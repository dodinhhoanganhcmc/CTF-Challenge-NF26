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
paths = set(original) | {p.relative_to(root).as_posix() for p in (root / 'public/fonts').iterdir() if p.is_file()}
modified = {rel: hashlib.sha256((root / rel).read_bytes()).hexdigest() for rel in paths}
(here / 'modified-hashes.json').write_text(json.dumps(modified, indent=2), encoding='utf-8')
shutil.copy2(root / 'components/game.tsx', here / 'MODIFIED_FILE.tsx')
diff = []
fixture = here / 'rollback-copy'
for rel in paths:
    dest = fixture / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(root / rel, dest)
    if original.get(rel) != modified[rel]:
        if rel.endswith('.woff2'):
            diff.append(f'Binary font added: {rel}; SHA256 {modified[rel]}\n')
            continue
        before = (here / 'baseline' / rel).read_text(encoding='utf-8-sig').splitlines(keepends=True) if rel in original else []
        after = (root / rel).read_text(encoding='utf-8-sig').splitlines(keepends=True)
        diff.extend(difflib.unified_diff(before, after, fromfile='baseline/' + rel, tofile='modified/' + rel))
(here / 'DIFF_FILE.patch').write_text(''.join(diff), encoding='utf-8')
records = []


def run(label, command, data):
    p = subprocess.run(command, shell=True, cwd=root, capture_output=True, text=True, encoding='utf-8', errors='replace')
    records.append({'label': label, 'command': command, 'input': data, 'stdout': p.stdout, 'stderr': p.stderr, 'exit': p.returncode})
    (here / (label.lower() + '.log')).write_text(p.stdout + p.stderr, encoding='utf-8')
    print(label, 'EXIT', p.returncode, p.stdout.strip()[-260:], flush=True)
    if p.returncode:
        print(p.stderr[-1500:]); raise SystemExit(p.returncode)


py = r'.venv\Scripts\python.exe'
check = py + ' evidence/footer-cleanup/check_state.py '
run('BASELINE', check + 'evidence/footer-cleanup/baseline', 'Original background colors, logo border, footer logo, Weight label and font.')
run('MODIFIED', check + '.', 'User-specified colors, borderless logo, copyright-only footer, removed Weight label and Poppins.')
run('PALETTE', py + ' scripts/check_palette.py', '34 actual text, button, border and focus color pairs.')
run('API_TESTS', py + ' -m pytest backend/tests -q', 'Existing real puzzle and opaque logo regressions.')
run('TYPECHECK', 'npm run typecheck', 'Current TypeScript.')
run('BUILD', 'npm run build', 'Current production frontend.')
run('E2E', 'npm run test:e2e', 'Both journeys; five widths/two themes; exact #FEFEFE/#020202 backgrounds, borderless logos, text-only footer, removed Weight label; Poppins loaded for all visible text and Vietnamese; replay still works.')
run('NPM_AUDIT', 'npm audit --json', 'Updated Poppins dependency and lockfile.')
run('ROLLBACK', r'"C:\Program Files\Git\bin\bash.exe" evidence/footer-cleanup/ROLLBACK.sh L:/ctf-chall/evidence/footer-cleanup/rollback-copy', 'Separate copy; source restored, npm ci and production build verify original fonts/dependencies. No player data touched.')
run('RESTORED', check + 'evidence/footer-cleanup/rollback-copy', 'Verify previous palette and heading are restored on the copy only.')
assert (root / 'components/game.tsx').read_bytes() == (here / 'MODIFIED_FILE.tsx').read_bytes()
assert all(hashlib.sha256((root / rel).read_bytes()).hexdigest() == value for rel, value in modified.items())
(here / 'execution-record.json').write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')
lines = ['VERIFICATION: borderless logos, copyright-only footer, final background tokens',
         "Changed fields: light surfaces -> #FEFEFE; dark surfaces -> #020202; logo border -> 0; footer -> (c) CMC Infrasec x NextFest '26; no footer logo/taglines or Weight ≤ 10 label. Replay moved beside guest summary. All UI fonts changed to Poppins. Logo assets unchanged.",
         'MODIFIED_FILE: ' + str(here / 'MODIFIED_FILE.tsx'), 'DIFF_FILE: ' + str(here / 'DIFF_FILE.patch'),
         'VERIFICATION: ' + str(here / 'VERIFICATION.txt'), 'ROLLBACK: ' + str(here / 'ROLLBACK.sh'),
         'Original game SHA256: ' + original['components/game.tsx'], 'Modified game SHA256: ' + modified['components/game.tsx'], '']
for r in records:
    lines += [r['label'], 'COMMAND: ' + r['command'], 'INPUT: ' + r['input'], 'LITERAL STDOUT:', r['stdout'], 'LITERAL STDERR:', r['stderr'], 'EXIT STATUS: ' + str(r['exit']), '']
lines += ['Restored behavior/status: previous colors, visible logo border, footer logo and Weight label on the separate copy; all 47 original hashes restored.',
          'Working project remains updated with the latest footer and precise background colors. Both supplied logo files remain unchanged.']
(here / 'VERIFICATION.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
for name in ('MODIFIED_FILE.tsx', 'DIFF_FILE.patch', 'VERIFICATION.txt', 'ROLLBACK.sh'):
    p = here / name
    assert p.read_bytes()
    print('REOPENED', p, p.stat().st_size, flush=True)
