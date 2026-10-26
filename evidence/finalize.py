"""Reproducible baseline/modified/rollback checks and literal execution record."""
import difflib
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
root = Path(__file__).resolve().parent.parent
os.chdir(root)
os.environ['PYTHONIOENCODING'] = 'utf-8'
evidence = root / 'evidence'
original = json.loads((evidence / 'original-hashes.json').read_text(encoding='utf-8'))
ignored = {'.venv', 'node_modules', '.next', 'evidence', 'test-results', 'playwright-report', '__pycache__', '.pytest_cache'}
files = [p for p in root.rglob('*') if p.is_file() and not any(x in ignored for x in p.relative_to(root).parts)
         and p.suffix not in ('.pyc', '.sqlite3', '.tsbuildinfo') and not p.name.endswith(('.sqlite3-wal', '.sqlite3-shm'))]
modified = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
(evidence / 'modified-hashes.json').write_text(json.dumps(modified, indent=2), encoding='utf-8')
shutil.copy2(root / 'backend/main.py', evidence / 'MODIFIED_FILE.py')
diff = []
for rel in sorted(set(original) | set(modified)):
    before = (evidence / 'baseline' / rel).read_text(encoding='utf-8-sig').splitlines(keepends=True) if rel in original else []
    after = (root / rel).read_text(encoding='utf-8-sig').splitlines(keepends=True) if rel in modified else []
    diff.extend(difflib.unified_diff(before, after, fromfile='baseline/' + rel, tofile='modified/' + rel))
(evidence / 'DIFF_FILE.patch').write_text(''.join(diff), encoding='utf-8')
fixture = evidence / 'rollback-copy'
for rel in modified:
    target = fixture / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(root / rel, target)
marker = fixture / 'backend/data/keep-player-data.txt'
marker.parent.mkdir(parents=True, exist_ok=True)
marker.write_text('preserved', encoding='utf-8')
records = []


def run(label, command, input_description):
    result = subprocess.run(command, shell=True, cwd=root, capture_output=True, text=True, encoding='utf-8', errors='replace')
    (evidence / f'{label.lower()}.log').write_text(result.stdout + result.stderr, encoding='utf-8')
    records.append({'label': label, 'command': command, 'input': input_description, 'stdout': result.stdout, 'stderr': result.stderr, 'exit': result.returncode})
    print(label, 'EXIT', result.returncode, result.stdout.strip()[-250:], flush=True)
    if result.returncode:
        print(result.stderr[-1200:], flush=True)
        raise SystemExit(result.returncode)


py = r'.venv\Scripts\python.exe'
run('BASELINE', py + ' scripts/check_health.py evidence/baseline/backend/main.py', 'GET /health against preserved original backend')
run('MODIFIED', py + ' scripts/check_health.py evidence/MODIFIED_FILE.py', 'GET /health against reopened modified artifact')
run('API_TESTS', py + ' -m pytest backend/tests -q', 'real Easy/Hard puzzle artifacts; temporary isolated SQLite per test')
run('TYPECHECK', 'npm run typecheck', 'all TypeScript source')
run('BUILD', 'npm run build', 'Next.js production build')
run('E2E', 'npm run test:e2e', 'production browser; Easy/Hard complete journeys; 320/375/414/768/1440, light/dark, axe')
run('NPM_AUDIT', 'npm audit --json', 'package-lock.json including development dependencies')
run('PIP_AUDIT', py + ' -m pip_audit -r backend/requirements-lock.txt --format=json', 'resolved application and test dependencies')
run('OPENAPI', 'npx --yes @redocly/cli lint docs/openapi.json --format=summary', 'OpenAPI 3.1 with cookie, Origin and CSRF contracts')
run('ROLLBACK', r'"C:\Program Files\Git\bin\bash.exe" evidence/ROLLBACK.sh L:/ctf-chall/evidence/rollback-copy', 'separate source copy; original hashes checked before restore')
run('RESTORED', py + ' scripts/check_health.py evidence/rollback-copy/backend/main.py', 'GET /health after rollback on separate copy')
assert marker.read_text(encoding='utf-8') == 'preserved'
assert (evidence / 'MODIFIED_FILE.py').read_bytes() == (root / 'backend/main.py').read_bytes()
assert hashlib.sha256((root / 'codex-session-01a16c26-3b2f-7da2-8b2b-1f6ace9e78f4.md').read_bytes()).hexdigest() == original['codex-session-01a16c26-3b2f-7da2-8b2b-1f6ace9e78f4.md']
(evidence / 'execution-record.json').write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')
lines = ['VERIFICATION · CMC Infrasec × NextFest 26',
         'Changed branch/field: GET /health status baseline -> ok; stages 0 -> 5. Added full five-stage game, guest persistence, separate mode leaderboards and server-authorized sticker completion code.',
         'MODIFIED_FILE: ' + str(evidence / 'MODIFIED_FILE.py'),
         'DIFF_FILE: ' + str(evidence / 'DIFF_FILE.patch'),
         'VERIFICATION: ' + str(evidence / 'VERIFICATION.txt'),
         'ROLLBACK: ' + str(evidence / 'ROLLBACK.sh'),
         'Original backend SHA256: ' + original['backend/main.py'],
         'Modified backend SHA256: ' + modified['backend/main.py'],
         'Original transcript unchanged: ' + original['codex-session-01a16c26-3b2f-7da2-8b2b-1f6ace9e78f4.md'], '']
for r in records:
    lines.extend([r['label'], 'COMMAND: ' + r['command'], 'INPUT: ' + r['input'], 'LITERAL STDOUT:', r['stdout'], 'LITERAL STDERR:', r['stderr'], 'EXIT STATUS: ' + str(r['exit']), ''])
lines.extend(['Restored behavior/status: HTTP 200 {"status":"baseline","stages":0}; exit 0.',
              'Rollback tested on another copy; original hashes restored; untracked player-data marker preserved.',
              'Working backend/main.py and MODIFIED_FILE.py remain modified: HTTP 200 {"status":"ok","stages":5}.',
              'Only pending user input: official CMC Infrasec logo; installation target public/club-logo.png.'])
(evidence / 'VERIFICATION.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
for filename in ['MODIFIED_FILE.py', 'DIFF_FILE.patch', 'VERIFICATION.txt', 'ROLLBACK.sh']:
    path = evidence / filename
    data = path.read_bytes()
    assert data
    print('REOPENED', path, len(data), hashlib.sha256(data).hexdigest(), flush=True)
print('VERIFIED: gameplay ready; official logo pending.', flush=True)
