"""Current logo/theme integration transaction, regressions and tested rollback."""
import difflib
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
here = Path(__file__).resolve().parent
root = here.parents[1]
os.chdir(root)
os.environ['PYTHONIOENCODING'] = 'utf-8'
original = json.loads((here / 'original-hashes.json').read_text())
paths = set(original) | {'components/club-logo.tsx', 'scripts/check_palette.py', 'public/club-logo.png', 'public/club-logo-light.jpg'}
modified = {rel: hashlib.sha256((root / rel).read_bytes()).hexdigest() for rel in sorted(paths)}
(here / 'modified-hashes.json').write_text(json.dumps(modified, indent=2), encoding='utf-8')
shutil.copy2(root / 'components/game.tsx', here / 'MODIFIED_FILE.tsx')
diff = []
for rel in sorted(paths):
    if original.get(rel) == modified[rel]:
        continue
    if rel.endswith(('.png', '.jpg')):
        diff.append(f'Binary file added: {rel}; SHA256 {modified[rel]}\n')
    else:
        before = (here / 'baseline' / rel).read_text(encoding='utf-8-sig').splitlines(keepends=True) if rel in original else []
        after = (root / rel).read_text(encoding='utf-8-sig').splitlines(keepends=True)
        diff.extend(difflib.unified_diff(before, after, fromfile='baseline/' + rel, tofile='modified/' + rel))
(here / 'DIFF_FILE.patch').write_text(''.join(diff), encoding='utf-8')
fixture = here / 'rollback-copy'
for rel in paths:
    dest = fixture / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(root / rel, dest)
marker = fixture / 'backend/data/preserve-player-data.txt'
marker.parent.mkdir(parents=True, exist_ok=True)
marker.write_text('preserved', encoding='utf-8')
records = []


def run(label, command, data):
    p = subprocess.run(command, shell=True, cwd=root, capture_output=True, text=True, encoding='utf-8', errors='replace')
    records.append({'label': label, 'command': command, 'input': data, 'stdout': p.stdout, 'stderr': p.stderr, 'exit': p.returncode})
    (here / (label.lower() + '.log')).write_text(p.stdout + p.stderr, encoding='utf-8')
    print(label, 'EXIT', p.returncode, p.stdout.strip()[-240:], flush=True)
    if p.returncode:
        print(p.stderr[-1500:]); raise SystemExit(p.returncode)


py = r'.venv\Scripts\python.exe'
check = py + ' evidence/logo-update/check_branding.py '
run('BASELINE', check + 'evidence/logo-update/baseline', 'Preserved pre-logo source; GET /api/v1/catalog and both asset paths.')
run('MODIFIED', check + '.', 'Current source; GET /api/v1/catalog and both decoded official asset files.')
run('PALETTE', py + ' scripts/check_palette.py', 'Actual CSS tokens; 34 WCAG text/UI pairs.')
run('API_TESTS', py + ' -m pytest backend/tests -q', 'Both real puzzle journeys, progression, persistence, reward and input controls.')
run('TYPECHECK', 'npm run typecheck', 'All TypeScript including ClubLogo and gameplay.')
run('BUILD', 'npm run build', 'Production application with supplied opaque logo pair.')
run('E2E', 'npm run test:e2e', 'Production browser; both full journeys; 5 widths × 2 themes; header/footer/reward logos; axe including dark secondary controls.')
run('NPM_AUDIT', 'npm audit --json', 'Current package-lock.json')
run('PIP_AUDIT', py + ' -m pip_audit -r backend/requirements-lock.txt --format=json', 'Current Python dependency lock')
run('OPENAPI', 'npx --yes @redocly/cli lint docs/openapi.json --format=summary', 'Current OpenAPI contract')
run('ROLLBACK', r'"C:\Program Files\Git\bin\bash.exe" evidence/logo-update/ROLLBACK.sh L:/ctf-chall/evidence/logo-update/rollback-copy', 'Dedicated copy only; original source hashes verified before restoring.')
run('RESTORED', check + 'evidence/logo-update/rollback-copy', 'Restored copy; pre-logo behavior while the real working copy stays branded.')
assert marker.read_text(encoding='utf-8') == 'preserved'
assert (root / 'components/game.tsx').read_bytes() == (here / 'MODIFIED_FILE.tsx').read_bytes()
assets = json.loads((here / 'supplied-assets.json').read_text())
for entry in assets.values():
    for key in ('source', 'copy'):
        assert hashlib.sha256(Path(entry[key]).read_bytes()).hexdigest() == entry['sha256']
(here / 'execution-record.json').write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')
lines = ['VERIFICATION · official logo integration / 2026-10-26',
         'Changed branch/field: catalog/reward logo_ready false -> true. Header/footer/reward ClubLogo selects opaque white alternative for light and opaque black primary for dark. No crop, recolor, inversion or background removal.',
         'Palette: forest/stone light and near-black forest dark; text >=4.5:1 and UI >=3:1 across 34 token pairs, plus rendered axe checks.',
         'MODIFIED_FILE: ' + str(here / 'MODIFIED_FILE.tsx'),
         'DIFF_FILE: ' + str(here / 'DIFF_FILE.patch'),
         'VERIFICATION: ' + str(here / 'VERIFICATION.txt'),
         'ROLLBACK: ' + str(here / 'ROLLBACK.sh'),
         'Original game SHA256: ' + original['components/game.tsx'],
         'Modified game SHA256: ' + modified['components/game.tsx'],
         'Original supplied artwork hashes: ' + json.dumps(assets), '']
for entry in records:
    lines += [entry['label'], 'COMMAND: ' + entry['command'], 'INPUT: ' + entry['input'],
              'LITERAL STDOUT:', entry['stdout'], 'LITERAL STDERR:', entry['stderr'], 'EXIT STATUS: ' + str(entry['exit']), '']
lines += ['Restored status: logo_ready=false; primary=missing; alternative=missing on the separate rollback copy. Player-data marker preserved.',
          'Actual project remains modified: logo_ready=true, both supplied logo variants installed, original input files unchanged.',
          'No pending logo input remains. Local application launch is recorded separately in deployment.log.']
(here / 'VERIFICATION.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
for name in ('MODIFIED_FILE.tsx', 'DIFF_FILE.patch', 'VERIFICATION.txt', 'ROLLBACK.sh'):
    file = here / name
    data = file.read_bytes()
    assert data
    print('REOPENED', file, len(data), hashlib.sha256(data).hexdigest(), flush=True)
print('VERIFIED official logos, palette, gameplay and rollback.', flush=True)
