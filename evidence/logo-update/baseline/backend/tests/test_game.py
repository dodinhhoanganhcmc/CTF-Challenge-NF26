import base64
import io
import re
import sqlite3
import subprocess
import sys
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from backend.main import create_app

HEADERS = {'origin': 'http://127.0.0.1:3000', 'x-expedition': '1'}


@pytest.fixture
def game(tmp_path):
    path = tmp_path / 'test.sqlite3'
    app = create_app(path)
    with TestClient(app) as c:
        c.headers.update(HEADERS)
        data = c.post('/api/v1/session', json={'name': 'Thuyền trưởng Mèo'}).json()
        c.headers['x-csrf-token'] = data['csrf']
        yield c, path


def solution(c, mode, stage):
    r = c.get(f'/api/v1/stages/{stage}?mode={mode}')
    assert r.status_code == 200
    payload = r.json()['payload']
    if stage == 1:
        decoded = base64.b64decode(payload).decode()
        return decoded if mode == 'easy' else bytes.fromhex(decoded).decode()
    if stage == 2:
        shift = 3 if mode == 'easy' else 7
        def rotate(m):
            s = m.group(); b = 65 if s.isupper() else 97
            return chr((ord(s)-b-shift)%26+b)
        return re.sub('[a-zA-Z]', rotate, payload)
    if stage == 3:
        return re.search(r'DAO\{[^}]+\}', payload).group() if mode == 'easy' else base64.b64decode(re.search(r'data-cargo="([^"]+)"', payload)[1]).decode()
    if stage == 4:
        if mode == 'easy':
            return ''.join(m[1] for m in sorted(re.findall(r'FRAGMENT seq=(\d+) text=([^\n]+)', payload)))
        r = c.get('/api/v1/stages/4/artifact?mode=hard')
        image = Image.open(io.BytesIO(r.content))
        chunks = sorted(x.split(':') for x in image.info['Comment'].split('|'))
        return bytes.fromhex(''.join(x[1] for x in chunks)).decode()
    blob = bytes.fromhex(payload) if mode == 'easy' else base64.b64decode(payload)
    key = b'SAO' if mode == 'easy' else b'LA_BAN'
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(blob)).decode()


def solve(c, mode, stage):
    flag = solution(c, mode, stage)
    r = c.post(f'/api/v1/stages/{stage}/answers?mode={mode}', json={'flag': flag})
    assert r.status_code == 200, r.text
    assert r.json()['correct']
    return flag


@pytest.mark.parametrize('mode', ['easy', 'hard'])
def test_complete_real_puzzle_journey(game, mode):
    c, _ = game
    assert c.get(f'/api/v1/treasure?mode={mode}').status_code == 409
    for stage in range(1, 6):
        if stage < 5:
            assert c.get(f'/api/v1/stages/{stage+1}?mode={mode}').status_code == 409
            assert c.get(f'/api/v1/stages/{stage+1}/artifact?mode={mode}').status_code == 409
        flag = solve(c, mode, stage)
        assert c.post(f'/api/v1/stages/{stage}/answers?mode={mode}', json={'flag': flag}).json()['correct']
    state = c.get('/api/v1/session').json()
    assert state['modes'][mode]['solved'] == [1, 2, 3, 4, 5]
    assert state['modes'][mode]['points'] == 3000
    assert state['modes']['hard' if mode == 'easy' else 'easy']['solved'] == []
    reward = c.get(f'/api/v1/treasure?mode={mode}').json()
    assert reward['reward'] == 'Sticker logo CMC Infrasec'
    assert re.fullmatch('NF26-[0-9A-F]{12}', reward['code'])
    assert c.get(f'/api/v1/treasure?mode={mode}').json()['code'] == reward['code']
    board = c.get(f'/api/v1/leaderboard?mode={mode}').json()
    assert board['items'][0]['points'] == 3000
    assert board['items'][0]['solved'] == 5


def test_hints_scoring_and_idempotence(game):
    c, _ = game
    for n in range(1, 6):
        r = c.post('/api/v1/stages/1/hints?mode=easy', json={})
        assert len(r.json()['hints']) == min(3, n)
    flag = solve(c, 'easy', 1)
    assert c.get('/api/v1/session').json()['modes']['easy']['points'] == 125
    c.post('/api/v1/stages/1/hints?mode=easy', json={})
    c.post('/api/v1/stages/1/answers?mode=easy', json={'flag': flag})
    assert c.get('/api/v1/session').json()['modes']['easy']['points'] == 125
    assert len(c.get('/api/v1/stages/1?mode=easy').json()['hints']) == 3


def test_wrong_case_whitespace_cross_session(game, tmp_path):
    c, _ = game
    flag = solution(c, 'easy', 1)
    assert not c.post('/api/v1/stages/1/answers?mode=easy', json={'flag': flag.lower()}).json()['correct']
    other = TestClient(create_app(tmp_path / 'other.db'), headers=HEADERS)
    data = other.post('/api/v1/session', json={'name': 'Other'}).json()
    other.headers['x-csrf-token'] = data['csrf']
    assert not other.post('/api/v1/stages/1/answers?mode=easy', json={'flag': flag}).json()['correct']
    assert c.post('/api/v1/stages/1/answers?mode=easy', json={'flag': '  ' + flag + '\n'}).json()['correct']


@pytest.mark.parametrize('headers', [{}, {'origin': 'https://evil.example', 'x-expedition': '1'}, {'origin': 'http://127.0.0.1:3000'}])
def test_session_origin_required(game, headers):
    c, _ = game
    c.headers.clear()
    assert c.post('/api/v1/session', json={'name': 'Guest'}, headers=headers).status_code == 403


@pytest.mark.parametrize('token', ['', 'wrong'])
def test_csrf(game, token):
    c, _ = game
    r = c.post('/api/v1/stages/1/hints?mode=easy', json={}, headers={'x-csrf-token': token})
    assert r.status_code == 403
    assert r.headers['content-type'].startswith('application/problem+json')


@pytest.mark.parametrize('data', [{'name': 'a'}, {'name': 'x'*25}, {'name': 'Mèo\x00'}, {'name': 123}, {'name': 'Okay', 'admin': True}, {}])
def test_guest_validation(game, data):
    c, _ = game
    assert c.post('/api/v1/session', json=data).status_code == 422


@pytest.mark.parametrize('path', ['/api/v1/stages/6?mode=easy', '/api/v1/stages/0?mode=easy', '/api/v1/stages/3?mode=hard', '/api/v1/leaderboard?mode=easy&limit=101', '/api/v1/stages/1?mode=expert'])
def test_bad_paths(game, path):
    c, _ = game
    assert c.get(path).status_code in (404, 409, 422)


def test_anonymous_and_expired(game):
    c, path = game
    token = c.cookies.get('expedition')
    assert 'httponly' in c.post('/api/v1/session', json={'name': 'Second'}).headers['set-cookie'].lower()
    with sqlite3.connect(path) as db:
        db.execute('UPDATE sessions SET expires=0')
    assert c.get('/api/v1/session').status_code == 401
    c.cookies.clear()
    assert c.get('/api/v1/stages/1?mode=easy').status_code == 401
    assert token


def test_body_json_flags_and_rate_limit(game):
    c, _ = game
    assert c.post('/api/v1/session', content=b'x'*4097).status_code == 413
    assert c.post('/api/v1/session', content='{bad', headers={'content-type': 'application/json'}).status_code == 422
    assert c.post('/api/v1/stages/1/answers?mode=easy', json={'flag': 'x'*161}).status_code == 422
    for _ in range(40):
        assert c.post('/api/v1/stages/1/answers?mode=easy', json={'flag': 'bad'}).status_code == 200
    assert c.post('/api/v1/stages/1/answers?mode=easy', json={'flag': 'bad'}).status_code == 429
    assert c.get('/api/v1/session').json()['modes']['easy']['points'] == 0


def test_restart_persistence_and_parallel_solves(game):
    c, path = game
    flag = solution(c, 'easy', 1)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: c.post('/api/v1/stages/1/answers?mode=easy', json={'flag': flag}), range(4)))
    assert all(r.json()['correct'] for r in results)
    restarted = TestClient(create_app(path), headers=HEADERS)
    restarted.cookies.update(c.cookies)
    assert restarted.get('/api/v1/session').json()['modes']['easy']['points'] == 200
    assert restarted.get('/api/v1/leaderboard?mode=easy').json()['total'] == 1


def test_public_catalog_and_parameterized_name(game):
    c, path = game
    catalog = c.get('/api/v1/catalog').json()
    assert catalog['organizer'] == 'CMC Infrasec'
    assert len(catalog['stages']) == 5
    assert 'DAO{' not in str(catalog)
    name = "x');DROP TABLE solves;--"
    r = c.post('/api/v1/session', json={'name': name})
    assert r.status_code == 201
    c.headers['x-csrf-token'] = r.json()['csrf']
    solve(c, 'easy', 1)
    assert c.get('/api/v1/leaderboard?mode=easy').json()['items'][0]['name'] == name


def test_organizer_reward_lookup(game):
    c, path = game
    for stage in range(1, 6):
        solve(c, 'easy', stage)
    code = c.get('/api/v1/treasure?mode=easy').json()['code']
    result = subprocess.run([sys.executable, 'scripts/check_reward.py', code, '--database', str(path)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['stages'] == 5
    result = subprocess.run([sys.executable, 'scripts/check_reward.py', 'NF26-000000000000', '--database', str(path)], capture_output=True, text=True)
    assert result.returncode == 1 and result.stdout.strip() == 'NOT_FOUND'


def test_logo_install_and_dynamic_detection(tmp_path, monkeypatch):
    import backend.main as main
    from scripts.install_logo import install
    source = tmp_path / 'source.png'
    Image.new('RGBA', (64, 64), (20, 40, 60, 255)).save(source)
    before = source.read_bytes()
    target = tmp_path / 'public/club-logo.png'
    monkeypatch.setattr(main, 'ROOT', tmp_path)
    c = TestClient(main.create_app(tmp_path / 'logo-test.db'))
    assert not c.get('/api/v1/catalog').json()['logo_ready']
    install(source, target)
    assert c.get('/api/v1/catalog').json()['logo_ready']
    assert before == source.read_bytes()
    with Image.open(target) as image:
        assert image.format == 'PNG' and image.size == (64, 64)
    with pytest.raises(ValueError):
        install(source, source)


def test_creation_rate_cap_and_empty_pagination(game):
    c, path = game
    assert c.get('/api/v1/leaderboard?mode=easy&offset=20').json()['items'] == []
    with sqlite3.connect(path) as db:
        db.execute("UPDATE limits SET count=3000 WHERE key LIKE 'new:%'")
    assert c.post('/api/v1/session', json={'name': 'Over limit'}).status_code == 429
