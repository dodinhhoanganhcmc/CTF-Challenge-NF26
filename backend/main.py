"""NextFest 26: authoritative guest sessions, progression and leaderboard."""
import hashlib
import hmac
import os
import secrets
import sqlite3
import time
import unicodedata
from contextlib import contextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from backend.puzzles import DEBRIEFS, STAGES, flag_for, image_artifact, puzzle
from backend import contracts
from backend.timing import LIMITS, score

Mode = Literal['easy', 'hard']
ROOT = Path(__file__).resolve().parent.parent
TTL = 30 * 24 * 3600


class Guest(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    name: str = Field(min_length=2, max_length=24)

    @field_validator('name')
    @classmethod
    def readable_name(cls, value):
        if any(unicodedata.category(c).startswith('C') for c in value):
            raise ValueError('Tên chứa ký tự điều khiển.')
        return value


class Answer(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    flag: str = Field(min_length=1, max_length=160)


def create_app(db_path=None, clock=None):
    now = clock or time.time
    app = FastAPI(title='Đảo Mật Mã · NextFest 26', version='1.0.0')
    path = Path(db_path or os.getenv('DATABASE_PATH', str(ROOT / 'backend/data/game.sqlite3')))
    path.parent.mkdir(parents=True, exist_ok=True)
    origins = set(os.getenv('APP_ORIGINS', 'http://127.0.0.1:3000,http://localhost:3000').split(','))

    @contextmanager
    def db():
        con = sqlite3.connect(path, timeout=15)
        con.row_factory = sqlite3.Row
        try:
            con.execute('PRAGMA foreign_keys=ON')
            con.execute('BEGIN IMMEDIATE')
            yield con
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()

    with db() as con:
        con.executescript('''
        CREATE TABLE IF NOT EXISTS sessions (
          id TEXT PRIMARY KEY, name TEXT NOT NULL, seed TEXT NOT NULL,
          csrf TEXT NOT NULL, expires REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS progress (
          session TEXT NOT NULL REFERENCES sessions(id), mode TEXT NOT NULL,
          started REAL NOT NULL, finished REAL, reward TEXT,
          PRIMARY KEY(session, mode));
        CREATE TABLE IF NOT EXISTS solves (
          session TEXT NOT NULL REFERENCES sessions(id), mode TEXT NOT NULL,
          stage INTEGER NOT NULL, points INTEGER NOT NULL, solved REAL NOT NULL,
          PRIMARY KEY(session, mode, stage));
        CREATE TABLE IF NOT EXISTS hints (
          session TEXT NOT NULL REFERENCES sessions(id), mode TEXT NOT NULL,
          stage INTEGER NOT NULL, count INTEGER NOT NULL,
          PRIMARY KEY(session, mode, stage));
        CREATE TABLE IF NOT EXISTS limits (
          key TEXT PRIMARY KEY, window INTEGER NOT NULL, count INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS stage_timers (
          session TEXT NOT NULL REFERENCES sessions(id), mode TEXT NOT NULL,
          stage INTEGER NOT NULL, started REAL NOT NULL, deadline REAL NOT NULL,
          attempt INTEGER NOT NULL, seed TEXT NOT NULL, finished REAL,
          PRIMARY KEY(session, mode, stage));
        ''')

    def fail(status, detail):
        raise HTTPException(status, detail)

    def rate(con, key, maximum, seconds=60):
        window = int(now() // seconds)
        row = con.execute('SELECT * FROM limits WHERE key=?', (key,)).fetchone()
        if row and row['window'] == window and row['count'] >= maximum:
            fail(429, 'Bạn thao tác hơi nhanh. Hãy thử lại sau một phút.')
        count = row['count'] + 1 if row and row['window'] == window else 1
        con.execute('INSERT OR REPLACE INTO limits VALUES (?,?,?)', (key, window, count))

    def session(con, request, write=False):
        raw = request.cookies.get('expedition', '')
        sid = hashlib.sha256(raw.encode()).hexdigest()
        row = con.execute('SELECT * FROM sessions WHERE id=? AND expires>?', (sid, now())).fetchone()
        if not row:
            fail(401, 'Nhập tên để bắt đầu một chuyến thám hiểm.')
        if write and not hmac.compare_digest(request.headers.get('x-csrf-token', ''), row['csrf']):
            fail(403, 'Phiên chưa đồng bộ. Hãy tải lại trang rồi thử lại.')
        return row

    def counts(con, sid, mode):
        return con.execute('SELECT COUNT(*) AS n FROM solves WHERE session=? AND mode=?', (sid, mode)).fetchone()['n']

    def unlock(con, guest, mode, stage):
        if stage not in range(1, 6):
            fail(404, 'Địa điểm không tồn tại.')
        if stage > counts(con, guest['id'], mode) + 1:
            fail(409, 'Hoàn thành địa điểm trước để mở lối đi này.')
        con.execute('INSERT OR IGNORE INTO progress(session,mode,started) VALUES (?,?,?)',
                    (guest['id'], mode, now()))

    def stage_timer(con, guest, mode, stage):
        unlock(con, guest, mode, stage)
        stamp = now()
        con.execute('''INSERT OR IGNORE INTO stage_timers
            (session,mode,stage,started,deadline,attempt,seed) VALUES (?,?,?,?,?,1,?)''',
                    (guest['id'], mode, stage, stamp, stamp + LIMITS[mode], guest['seed']))
        return con.execute('SELECT * FROM stage_timers WHERE session=? AND mode=? AND stage=?', (guest['id'], mode, stage)).fetchone()

    def timer_state(con, timer):
        stamp = now()
        solved = con.execute('SELECT points,solved FROM solves WHERE session=? AND mode=? AND stage=?',
                             (timer['session'], timer['mode'], timer['stage'])).fetchone()
        # Existing solved records predate timing; preserve their awarded score.
        end = timer['finished'] if timer['finished'] is not None else stamp
        elapsed = max(0, end - timer['started'])
        remaining = max(0, timer['deadline'] - end)
        legacy = bool(solved and solved['solved'] < timer['started'])
        hints = con.execute('SELECT count FROM hints WHERE session=? AND mode=? AND stage=?',
                            (timer['session'], timer['mode'], timer['stage'])).fetchone()
        return {'started_at': timer['started'], 'deadline': timer['deadline'], 'server_now': stamp,
                'limit_seconds': LIMITS[timer['mode']], 'elapsed_seconds': None if legacy else min(LIMITS[timer['mode']], elapsed),
                'remaining_seconds': 0 if legacy else remaining, 'expired': not solved and stamp >= timer['deadline'],
                'attempt': timer['attempt'], 'solved': bool(solved), 'awarded_points': solved['points'] if solved else None,
                'legacy_scoring': legacy,
                'points_available': solved['points'] if solved else score(STAGES[timer['stage']-1]['weight'], elapsed,
                    LIMITS[timer['mode']], hints['count'] if hints else 0, timer['attempt'])}

    def clue_data(con, guest, mode, stage, timer):
        data = puzzle(timer['seed'], mode, stage)
        saved = con.execute('SELECT count FROM hints WHERE session=? AND mode=? AND stage=?', (guest['id'], mode, stage)).fetchone()
        data['hints'] = data['hints'][:saved['count'] if saved else 0]
        data['debrief'] = DEBRIEFS[stage-1] if stage <= counts(con, guest['id'], mode) else None
        return {**STAGES[stage-1], **data, 'timing': timer_state(con, timer)}

    def require_time(timer, stamp=None):
        if (now() if stamp is None else stamp) >= timer['deadline']:
            fail(409, 'Hết giờ cho bài này. Chọn Chơi lại bài để nhận flag mới; mức điểm giảm còn 50%.')

    def state(con, guest):
        modes = {}
        for mode in ('easy', 'hard'):
            rows = con.execute('SELECT stage,points FROM solves WHERE session=? AND mode=? ORDER BY stage', (guest['id'], mode)).fetchall()
            hints = con.execute('SELECT stage,count FROM hints WHERE session=? AND mode=?', (guest['id'], mode)).fetchall()
            modes[mode] = {'solved': [r['stage'] for r in rows], 'points': sum(r['points'] for r in rows),
                           'hints': {str(r['stage']): r['count'] for r in hints}}
        return {'name': guest['name'], 'csrf': guest['csrf'], 'modes': modes}

    @app.exception_handler(HTTPException)
    async def problem(request, exc):
        return JSONResponse({'type': 'about:blank', 'title': 'Yêu cầu chưa hoàn tất',
                             'status': exc.status_code, 'detail': exc.detail},
                            status_code=exc.status_code, media_type='application/problem+json')

    @app.exception_handler(RequestValidationError)
    async def validation(request, exc):
        return await problem(request, HTTPException(422, 'Kiểm tra dữ liệu: tên 2–24 ký tự, flag tối đa 160 ký tự; mode easy hoặc hard.'))

    @app.middleware('http')
    async def controls(request, call_next):
        if request.method in ('POST', 'DELETE', 'PUT', 'PATCH'):
            if request.headers.get('origin') not in origins or request.headers.get('x-expedition') != '1':
                return await problem(request, HTTPException(403, 'Yêu cầu phải xuất phát từ trang trò chơi.'))
            chunks, size = [], 0
            async for chunk in request.stream():
                size += len(chunk)
                if size > 4096:
                    return await problem(request, HTTPException(413, 'Dữ liệu vượt quá 4 KB.'))
                chunks.append(chunk)
            request._body = b''.join(chunks)
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response

    @app.get('/health', response_model=contracts.Health)
    def health():
        return {'status': 'ok', 'stages': len(STAGES)}

    @app.get('/api/v1/catalog', response_model=contracts.Catalog)
    def catalog():
        return {'stages': STAGES, 'organizer': 'CMC Infrasec', 'event': 'NextFest 26',
                'reward': 'Sticker logo CLB', 'logo_ready': (ROOT / 'public/club-logo.png').is_file()}

    @app.post('/api/v1/session', status_code=201, response_model=contracts.Session)
    def enter(data: Guest, request: Request, response: Response):
        token = secrets.token_urlsafe(32)
        sid = hashlib.sha256(token.encode()).hexdigest()
        with db() as con:
            rate(con, 'new:' + (request.client.host if request.client else 'local'), 3000, 3600)
            con.execute('INSERT INTO sessions VALUES (?,?,?,?,?)',
                        (sid, data.name, secrets.token_hex(32), secrets.token_urlsafe(32), now() + TTL))
            result = state(con, con.execute('SELECT * FROM sessions WHERE id=?', (sid,)).fetchone())
        response.set_cookie('expedition', token, httponly=True, samesite='strict',
                            secure=os.getenv('COOKIE_SECURE', '0') == '1', max_age=TTL, path='/')
        return result

    @app.get('/api/v1/session', response_model=contracts.Session)
    def current(request: Request):
        with db() as con:
            return state(con, session(con, request))

    @app.get('/api/v1/stages/{stage}', response_model=contracts.Clue)
    def clue(stage: int, mode: Mode, request: Request):
        with db() as con:
            guest = session(con, request)
            timer = stage_timer(con, guest, mode, stage)
            return clue_data(con, guest, mode, stage, timer)

    @app.get('/api/v1/stages/{stage}/timing', response_model=contracts.Timing)
    def timing(stage: int, mode: Mode, request: Request):
        with db() as con:
            guest = session(con, request)
            return timer_state(con, stage_timer(con, guest, mode, stage))

    @app.post('/api/v1/stages/{stage}/retries', response_model=contracts.Clue)
    def retry_stage(stage: int, mode: Mode, request: Request):
        with db() as con:
            guest = session(con, request, True)
            timer = stage_timer(con, guest, mode, stage)
            if stage <= counts(con, guest['id'], mode) or now() < timer['deadline']:
                fail(409, 'Chỉ chơi lại bài chưa giải khi đã hết giờ.')
            rate(con, 'retry:' + guest['id'], 10)
            stamp = now()
            con.execute('''UPDATE stage_timers SET started=?,deadline=?,attempt=attempt+1,seed=?,finished=NULL
                WHERE session=? AND mode=? AND stage=?''',
                (stamp, stamp + LIMITS[mode], secrets.token_hex(32), guest['id'], mode, stage))
            timer = stage_timer(con, guest, mode, stage)
            return clue_data(con, guest, mode, stage, timer)

    @app.get('/api/v1/stages/{stage}/artifact')
    def artifact(stage: int, mode: Mode, request: Request):
        with db() as con:
            guest = session(con, request)
            timer = stage_timer(con, guest, mode, stage)
            if stage > counts(con, guest['id'], mode):
                require_time(timer)
            png = stage == 4 and mode == 'hard'
            body = image_artifact(timer['seed']) if png else puzzle(timer['seed'], mode, stage)['payload'].encode()
            return Response(body, media_type='image/png' if png else 'text/plain; charset=utf-8',
                            headers={'Content-Disposition': 'attachment; filename="' + ('lighthouse.png' if png else 'clue.txt') + '"'})

    @app.post('/api/v1/stages/{stage}/hints', response_model=contracts.Hints)
    def hint(stage: int, mode: Mode, request: Request):
        with db() as con:
            guest = session(con, request, True)
            timer = stage_timer(con, guest, mode, stage)
            if stage > counts(con, guest['id'], mode):
                require_time(timer)
            rate(con, 'hint:' + guest['id'], 30)
            old = con.execute('SELECT count FROM hints WHERE session=? AND mode=? AND stage=?', (guest['id'], mode, stage)).fetchone()
            count = min(3, (old['count'] if old else 0) + 1)
            con.execute('INSERT OR REPLACE INTO hints VALUES (?,?,?,?)', (guest['id'], mode, stage, count))
            return {'hints': puzzle(timer['seed'], mode, stage)['hints'][:count]}

    @app.post('/api/v1/stages/{stage}/answers', response_model=contracts.AnswerResult, response_model_exclude_none=True)
    def answer(stage: int, mode: Mode, data: Answer, request: Request):
        with db() as con:
            guest = session(con, request, True)
            timer = stage_timer(con, guest, mode, stage)
            rate(con, 'answer:' + guest['id'], 40)
            already_solved = stage <= counts(con, guest['id'], mode)
            stamp = now()
            if not already_solved:
                require_time(timer, stamp)
            if not hmac.compare_digest(data.flag.encode(), flag_for(timer['seed'], mode, stage).encode()):
                return {'correct': False, 'detail': 'Chưa đúng rồi. Kiểm tra đủ DAO{…}, chữ hoa và dấu ngoặc nhé.'}
            hints = con.execute('SELECT count FROM hints WHERE session=? AND mode=? AND stage=?', (guest['id'], mode, stage)).fetchone()
            points = score(STAGES[stage-1]['weight'], stamp - timer['started'], LIMITS[mode],
                           hints['count'] if hints else 0, timer['attempt'])
            con.execute('INSERT OR IGNORE INTO solves VALUES (?,?,?,?,?)', (guest['id'], mode, stage, points, stamp))
            if not already_solved:
                con.execute('UPDATE stage_timers SET finished=? WHERE session=? AND mode=? AND stage=?',
                            (stamp, guest['id'], mode, stage))
            if counts(con, guest['id'], mode) == 5:
                con.execute('UPDATE progress SET finished=COALESCE(finished,?),reward=COALESCE(reward,?) WHERE session=? AND mode=?',
                            (stamp, 'NF26-' + secrets.token_hex(6).upper(), guest['id'], mode))
            timer = stage_timer(con, guest, mode, stage)
            return {'correct': True, 'debrief': DEBRIEFS[stage-1], 'session': state(con, guest), 'timing': timer_state(con, timer)}

    @app.get('/api/v1/treasure', response_model=contracts.Treasure)
    def treasure(mode: Mode, request: Request):
        with db() as con:
            guest = session(con, request)
            if counts(con, guest['id'], mode) != 5:
                fail(409, 'Cần đủ 5 mảnh la bàn để mở kho báu.')
            row = con.execute('SELECT * FROM progress WHERE session=? AND mode=?', (guest['id'], mode)).fetchone()
            return {'name': guest['name'], 'reward': 'Sticker logo CMC Infrasec',
                    'event': 'NextFest 26', 'code': row['reward'], 'mode': mode,
                    'seconds': round(row['finished'] - row['started']),
                    'instruction': 'Đưa màn hình này cho ban tổ chức tại khu vực CLB để nhận sticker.',
                    'logo_ready': (ROOT / 'public/club-logo.png').is_file()}

    @app.get('/api/v1/leaderboard', response_model=contracts.Leaderboard)
    def leaderboard(mode: Mode, limit: int = 20, offset: int = 0):
        if not 1 <= limit <= 100 or offset < 0 or offset > 10000:
            fail(422, 'limit từ 1–100; offset từ 0–10000.')
        with db() as con:
            rows = con.execute('''SELECT s.name, COUNT(v.stage) AS solved, SUM(v.points) AS points,
                CASE WHEN p.finished IS NOT NULL THEN ROUND(p.finished-p.started) ELSE NULL END AS seconds
                FROM progress p JOIN sessions s ON s.id=p.session
                JOIN solves v ON v.session=p.session AND v.mode=p.mode
                WHERE p.mode=? GROUP BY p.session,p.mode
                ORDER BY solved DESC, points DESC, COALESCE(p.finished-p.started,1e15), p.started
                LIMIT ? OFFSET ?''', (mode, limit, offset)).fetchall()
            total = con.execute('SELECT COUNT(DISTINCT session) n FROM solves WHERE mode=?', (mode,)).fetchone()['n']
            return {'items': [dict(r) for r in rows], 'total': total, 'offset': offset, 'limit': limit}

    contracts.document_controls(app)
    return app


app = create_app()

