import base64
import hashlib
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from backend.main import create_app
from backend.timing import LIMITS, score

HEADERS = {'origin': 'http://127.0.0.1:3000', 'x-expedition': '1'}


@pytest.fixture
def timed(tmp_path):
    stamp = [2_000_000_000.0]
    path = tmp_path / 'timed.sqlite3'
    app = create_app(path, clock=lambda: stamp[0])
    with TestClient(app, headers=HEADERS) as client:
        guest = client.post('/api/v1/session', json={'name': 'Timer Captain'}).json()
        client.headers['x-csrf-token'] = guest['csrf']
        yield client, stamp, path


def flag_from_clue(data, mode):
    raw = base64.b64decode(data['payload']).decode()
    return raw if mode == 'easy' else bytes.fromhex(raw).decode()


@pytest.mark.parametrize('mode,limit', [('easy', 180), ('hard', 420)])
def test_exact_limits_reload_restart_and_server_scoring(timed, mode, limit):
    c, stamp, path = timed
    data = c.get(f'/api/v1/stages/1?mode={mode}').json()
    flag = flag_from_clue(data, mode)
    assert data['timing']['remaining_seconds'] == limit
    assert data['timing']['deadline'] == stamp[0] + limit
    stamp[0] += limit / 2
    reload = c.get(f'/api/v1/stages/1?mode={mode}').json()
    assert reload['payload'] == data['payload']
    assert reload['timing']['remaining_seconds'] == limit / 2
    restarted = TestClient(create_app(path, clock=lambda: stamp[0]), headers=dict(c.headers))
    restarted.cookies.update(c.cookies)
    assert restarted.get(f'/api/v1/stages/1/timing?mode={mode}').json()['remaining_seconds'] == limit / 2
    r = restarted.post(f'/api/v1/stages/1/answers?mode={mode}', json={'flag': flag})
    assert r.status_code == 200 and r.json()['correct']
    assert r.json()['session']['modes'][mode]['points'] == 150
    assert r.json()['timing']['elapsed_seconds'] == limit / 2
    stamp[0] += limit * 2
    duplicate = restarted.post(f'/api/v1/stages/1/answers?mode={mode}', json={'flag': flag}).json()
    assert duplicate['session']['modes'][mode]['points'] == 150
    assert duplicate['timing']['elapsed_seconds'] == limit / 2
    assert restarted.get(f'/api/v1/stages/1?mode={mode}').json()['timing']['solved']
    assert restarted.get(f'/api/v1/stages/1/artifact?mode={mode}').status_code == 200


@pytest.mark.parametrize('mode', ['easy', 'hard'])
def test_deadline_boundary_expired_flag_hints_artifact_retry(timed, mode):
    c, stamp, path = timed
    data = c.get(f'/api/v1/stages/1?mode={mode}').json()
    old_flag = flag_from_clue(data, mode)
    assert c.post(f'/api/v1/stages/1/retries?mode={mode}', json={}).status_code == 409
    c.post(f'/api/v1/stages/1/hints?mode={mode}', json={})
    stamp[0] += LIMITS[mode]
    timing = c.get(f'/api/v1/stages/1/timing?mode={mode}').json()
    assert timing['expired'] and timing['remaining_seconds'] == 0
    for suffix, method, payload in [('answers', 'post', {'flag': old_flag}), ('hints', 'post', {}), ('artifact', 'get', None)]:
        r = c.request(method, f'/api/v1/stages/1/{suffix}?mode={mode}', json=payload)
        assert r.status_code == 409, r.text
    assert c.get('/api/v1/session').json()['modes'][mode]['solved'] == []
    assert c.get(f'/api/v1/stages/2?mode={mode}').status_code == 409
    assert c.get(f'/api/v1/treasure?mode={mode}').status_code == 409
    r = c.post(f'/api/v1/stages/1/retries?mode={mode}', json={})
    assert r.status_code == 200
    new = r.json()
    assert new['timing']['attempt'] == 2 and new['timing']['remaining_seconds'] == LIMITS[mode]
    assert len(new['hints']) == 1
    assert new['payload'] != data['payload']
    assert new['timing']['points_available'] == 87  # (200-25)//2
    assert not c.post(f'/api/v1/stages/1/answers?mode={mode}', json={'flag': old_flag}).json()['correct']
    solved = c.post(f'/api/v1/stages/1/answers?mode={mode}', json={'flag': flag_from_clue(new, mode)}).json()
    assert solved['correct'] and solved['session']['modes'][mode]['points'] == 87
    assert c.post(f'/api/v1/stages/1/retries?mode={mode}', json={}).status_code == 409


def test_near_deadline_and_exact_boundary(timed):
    c, stamp, _ = timed
    data = c.get('/api/v1/stages/1?mode=easy').json()
    stamp[0] += 179.999
    r = c.post('/api/v1/stages/1/answers?mode=easy', json={'flag': flag_from_clue(data, 'easy')})
    assert r.json()['correct'] and r.json()['timing']['awarded_points'] == 100


def test_independent_stage_mode_session_and_no_client_timing(timed):
    c, stamp, path = timed
    first = c.get('/api/v1/stages/1?mode=easy').json()
    stamp[0] += 70
    hard = c.get('/api/v1/stages/1?mode=hard').json()
    assert hard['timing']['remaining_seconds'] == 420
    assert c.get('/api/v1/stages/1/timing?mode=easy').json()['remaining_seconds'] == 110
    flag = flag_from_clue(first, 'easy')
    assert c.post('/api/v1/stages/1/answers?mode=easy', json={'flag': flag, 'elapsed_seconds': 0}).status_code == 422
    r = c.post('/api/v1/stages/1/answers?mode=easy', json={'flag': flag}).json()
    assert r['timing']['awarded_points'] == 161
    stamp[0] += 20
    second = c.get('/api/v1/stages/2?mode=easy').json()
    assert second['timing']['remaining_seconds'] == 180
    assert c.get('/api/v1/stages/1/timing?mode=easy').json()['elapsed_seconds'] == 70
    other = TestClient(create_app(path, clock=lambda: stamp[0]), headers=HEADERS)
    other.post('/api/v1/session', json={'name': 'Other Timer'})
    assert other.get('/api/v1/stages/1?mode=easy').json()['timing']['remaining_seconds'] == 180
    # Invalid CSRF and locked routes never restart an existing clock.
    assert other.post('/api/v1/stages/1/retries?mode=easy', json={}).status_code == 403
    assert c.get('/api/v1/stages/3/timing?mode=easy').status_code == 409


def test_parallel_solves_and_retry_are_single_awards(timed):
    c, stamp, _ = timed
    data = c.get('/api/v1/stages/1?mode=easy').json()
    stamp[0] += 180
    with ThreadPoolExecutor(max_workers=3) as pool:
        result = list(pool.map(lambda _: c.post('/api/v1/stages/1/retries?mode=easy', json={}), range(3)))
    assert sorted(r.status_code for r in result) == [200, 409, 409]
    new = next(r.json() for r in result if r.status_code == 200)
    flag = flag_from_clue(new, 'easy')
    stamp[0] += 90
    with ThreadPoolExecutor(max_workers=3) as pool:
        result = list(pool.map(lambda _: c.post('/api/v1/stages/1/answers?mode=easy', json={'flag': flag}), range(3)))
    assert all(r.json()['correct'] for r in result)
    assert c.get('/api/v1/session').json()['modes']['easy']['points'] == 75
    assert c.get('/api/v1/leaderboard?mode=easy').json()['items'][0]['points'] == 75


def test_leaderboard_rewards_faster_solver(timed):
    slow, stamp, path = timed
    data = slow.get('/api/v1/stages/1?mode=easy').json()
    fast = TestClient(create_app(path, clock=lambda: stamp[0]), headers=HEADERS)
    guest = fast.post('/api/v1/session', json={'name': 'Fast Captain'}).json()
    fast.headers['x-csrf-token'] = guest['csrf']
    quick = fast.get('/api/v1/stages/1?mode=easy').json()
    assert fast.post('/api/v1/stages/1/answers?mode=easy', json={'flag': flag_from_clue(quick, 'easy')}).json()['timing']['awarded_points'] == 200
    stamp[0] += 90
    assert slow.post('/api/v1/stages/1/answers?mode=easy', json={'flag': flag_from_clue(data, 'easy')}).json()['timing']['awarded_points'] == 150
    board = slow.get('/api/v1/leaderboard?mode=easy').json()['items']
    assert [(r['name'], r['points']) for r in board] == [('Fast Captain', 200), ('Timer Captain', 150)]


def test_hard_png_retry_regenerates_artifact_and_prior_solves_survive(timed):
    from backend.tests.test_game import solve, solution
    c, stamp, _ = timed
    for stage in range(1, 4):
        solve(c, 'hard', stage)
    original_flag = solution(c, 'hard', 4)
    original_image = c.get('/api/v1/stages/4/artifact?mode=hard').content
    stamp[0] += 420
    assert c.get('/api/v1/stages/4/artifact?mode=hard').status_code == 409
    c.post('/api/v1/stages/4/retries?mode=hard', json={})
    assert solution(c, 'hard', 4) != original_flag
    assert c.get('/api/v1/stages/4/artifact?mode=hard').content != original_image
    assert c.get('/api/v1/session').json()['modes']['hard']['solved'] == [1, 2, 3]
    solve(c, 'hard', 4)
    assert c.get('/api/v1/session').json()['modes']['hard']['points'] == 1600


def test_migration_preserves_existing_solves_and_scores(timed):
    c, stamp, path = timed
    sid = hashlib.sha256(c.cookies.get('expedition').encode()).hexdigest()
    with sqlite3.connect(path) as db:
        db.execute('DROP TABLE stage_timers')
        db.execute('INSERT INTO progress(session,mode,started) VALUES (?,?,?)', (sid, 'easy', stamp[0]-100))
        db.execute('INSERT INTO solves VALUES (?,?,?,?,?)', (sid, 'easy', 1, 200, stamp[0]-50))
    updated = TestClient(create_app(path, clock=lambda: stamp[0]), headers=dict(c.headers))
    updated.cookies.update(c.cookies)
    data = updated.get('/api/v1/stages/1?mode=easy').json()
    assert data['timing']['legacy_scoring']
    assert data['timing']['elapsed_seconds'] is None
    assert data['timing']['awarded_points'] == 200
    assert updated.get('/api/v1/stages/2?mode=easy').json()['timing']['remaining_seconds'] == 180
    assert updated.get('/api/v1/session').json()['modes']['easy']['points'] == 200


@pytest.mark.parametrize('mode', ['easy', 'hard'])
def test_score_decreases_over_time_and_stays_bounded(mode):
    limit = LIMITS[mode]
    for weight in (2, 4, 6, 8, 10):
        for hints in range(4):
            values = [score(weight, elapsed, limit, hints) for elapsed in range(limit + 1)]
            assert values == sorted(values, reverse=True)
            assert max(values) == weight*100 - hints*25
            assert min(values) == 0
            assert score(weight, 0, limit, hints, 2) <= weight*50
            assert score(weight, 0, limit, hints, 3) == score(weight, 0, limit, hints, 2)
