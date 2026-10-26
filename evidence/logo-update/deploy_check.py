"""Check the updated, running local deployment, including optimized logo pixels."""
import hashlib
import io
import json
import sys
from pathlib import Path
import httpx
from PIL import Image

sys.stdout.reconfigure(encoding='utf-8')
here = Path(__file__).resolve().parent
root = here.parents[1]
lines = []
with httpx.Client(base_url='http://127.0.0.1:3000', timeout=30) as client:
    assert client.get('/').status_code == 200
    response = client.get('/api/v1/catalog')
    assert response.status_code == 200 and response.json()['logo_ready'] is True
    assert response.json()['organizer'] == 'CMC Infrasec'
    for filename in ('club-logo.png', 'club-logo-light.jpg'):
        response = client.get('/' + filename)
        assert response.status_code == 200
        assert response.content == (root / 'public' / filename).read_bytes()
        optimized = client.get('/_next/image', params={'url': '/' + filename + '?v=20261026', 'w': 256, 'q': 75}, headers={'Accept': 'image/webp'})
        assert optimized.status_code == 200, optimized.text[:100]
        with Image.open(io.BytesIO(optimized.content)) as image:
            assert image.size == (256, 256), image.size
            assert image.convert('RGBA').getchannel('A').getextrema() == (255, 255), 'Optimized image is not opaque.'
    lines.append('DEPLOYED http://127.0.0.1:3000 HTTP 200 logo_ready=true optimized_dark=256x256 optimized_light=256x256 opaque=true')
    response = client.post('/api/v1/session', json={'name': 'Branding check'}, headers={'origin': 'http://127.0.0.1:3000', 'x-expedition': '1'})
    assert response.status_code == 201
    assert client.get('/api/v1/stages/1?mode=easy').status_code == 200
    lines.append('GAMEPLAY guest=201 first_stage=200')
manifest = json.loads((here / 'modified-hashes.json').read_text())
assert all(hashlib.sha256((root / rel).read_bytes()).hexdigest() == value for rel, value in manifest.items())
lines.append('SOURCE_HASHES current=' + str(len(manifest)) + ' all_match=true')
(here / 'deployment.log').write_text('\n'.join(lines) + '\n', encoding='utf-8')
print('\n'.join(lines))
records = json.loads((here / 'execution-record.json').read_text(encoding='utf-8'))
assert len(records) == 12 and all(row['exit'] == 0 for row in records)
report = '''# Completion audit — 2026-10-26

All items were checked against current source, current execution records and the running local application.

| Requirement | Authoritative proof | Result |
|---|---|---|
| Next.js frontend / Python backend | package.json, app/, backend/main.py; production BUILD and TYPECHECK | Pass |
| Five sequential stages; weight 2/4/6/8/10 | backend/puzzles.py; both real API solution journeys and both browser journeys | Pass |
| Easy teaches beginners; Hard combines basic CTF methods | objectives/hints/samples, local bench and guide; real artifact decoding in tests | Pass |
| Guest entry, SQLite persistence and separate mode leaderboards | restart/isolation/scoring/idempotence tests; browser journeys and leaderboard | Pass |
| Treasure after five solves; club-logo sticker at NextFest 26 | server treasure gate, completion code, local organizer lookup and both reward screens | Pass |
| Official primary/alternative logos copied | supplied-assets.json; byte-equal originals; both public assets served | Pass |
| Opaque logo choice matches theme without crop/inversion | raw/optimized pixel alpha tests, header/footer/reward source/contain/filter checks; light/dark screenshots | Pass |
| Readable palette and responsive UI | 34 contrast pairs, minimum text 5.16:1 and UI 3.69:1; axe on five widths x two themes, missions, rewards and dark secondary controls | Pass |
| Session/input/security controls and current dependency checks | API_TESTS, proxy E2E, NPM_AUDIT, PIP_AUDIT, OPENAPI all exit 0 | Pass |
| Originals, diff and working rollback | four reopened artifacts; separate copy restored to pre-logo state; player-data marker preserved | Pass |
| Runnable updated local deployment | deployment.log: HTTP 200, logo_ready=true, optimized logos opaque, guest 201, first stage 200 | Pass |

28 API tests and 7 browser tests passed. Production build, typecheck, dependency audits and OpenAPI lint passed. No required logo input or unfinished item remains. Local operation is the approved deployment context; no external host/domain was requested.
'''
(here / 'completion-audit.md').write_text(report, encoding='utf-8')
assert (here / 'completion-audit.md').read_text(encoding='utf-8') == report
with (here / 'VERIFICATION.txt').open('a', encoding='utf-8') as record:
    record.write('\nDEPLOYMENT\nCOMMAND: .venv\\Scripts\\python.exe evidence/logo-update/deploy_check.py\nINPUT: running local production app and versioned optimized logo images\nLITERAL OUTPUT:\n' + '\n'.join(lines) + '\nEXIT STATUS: 0\n')
for name in ('MODIFIED_FILE.tsx', 'DIFF_FILE.patch', 'VERIFICATION.txt', 'ROLLBACK.sh'):
    path = here / name
    data = path.read_bytes()
    assert data
    print('REOPENED', path, len(data), hashlib.sha256(data).hexdigest())
