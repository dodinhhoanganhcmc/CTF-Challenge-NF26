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
modified = {rel: hashlib.sha256((root / rel).read_bytes()).hexdigest() for rel in original}
(here / 'modified-hashes.json').write_text(json.dumps(modified, indent=2), encoding='utf-8')
shutil.copy2(root / 'app/globals.css', here / 'MODIFIED_FILE.css')
diff = []
fixture = here / 'rollback-copy'
for rel in original:
    dest = fixture / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(root / rel, dest)
    if original[rel] != modified[rel]:
        before = (here / 'baseline' / rel).read_text(encoding='utf-8-sig').splitlines(keepends=True)
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
check = py + ' evidence/footer-bold/check_state.py '
run('BASELINE', check + 'evidence/footer-bold/baseline', 'Original footer family and font-weight.')
run('MODIFIED', check + '.', 'Footer uses explicit Poppins token and real bold 700, with synthesis disabled.')
run('TYPECHECK', 'npm run typecheck', 'Current TypeScript.')
run('BUILD', 'npm run build', 'Current production frontend.')
run('E2E', 'npm run test:e2e', 'Both journeys; five widths/two themes; unchanged footer copy, size and alignment; computed 700 and actual Poppins Bold platform font; axe checks.')
run('ROLLBACK', r'"C:\Program Files\Git\bin\bash.exe" evidence/footer-bold/ROLLBACK.sh L:/ctf-chall/evidence/footer-bold/rollback-copy', 'Separate copy; no runtime data touched.')
run('RESTORED', check + 'evidence/footer-bold/rollback-copy', 'Verify previous palette and heading are restored on the copy only.')
assert (root / 'app/globals.css').read_bytes() == (here / 'MODIFIED_FILE.css').read_bytes()
assert all(hashlib.sha256((root / rel).read_bytes()).hexdigest() == value for rel, value in modified.items())
(here / 'execution-record.json').write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')
lines = ['VERIFICATION: footer uses the same Poppins family in genuine Bold 700',
         'Changed field: footer font-weight 500 -> 700. Explicit font-family var(--font-sans), font-style normal and font-synthesis none. Copyright, sizes, left alignment, backgrounds, logos and gameplay unchanged.',
         'MODIFIED_FILE: ' + str(here / 'MODIFIED_FILE.css'), 'DIFF_FILE: ' + str(here / 'DIFF_FILE.patch'),
         'VERIFICATION: ' + str(here / 'VERIFICATION.txt'), 'ROLLBACK: ' + str(here / 'ROLLBACK.sh'),
         'Original stylesheet SHA256: ' + original['app/globals.css'], 'Modified stylesheet SHA256: ' + modified['app/globals.css'], '']
for r in records:
    lines += [r['label'], 'COMMAND: ' + r['command'], 'INPUT: ' + r['input'], 'LITERAL STDOUT:', r['stdout'], 'LITERAL STDERR:', r['stderr'], 'EXIT STATUS: ' + str(r['exit']), '']
lines += ['Restored behavior/status: Poppins weight 500 on the separate copy; both original file hashes restored.',
          'Actual project retains Poppins Bold 700, with existing copy, sizes and left alignment preserved.']
(here / 'VERIFICATION.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
for name in ('MODIFIED_FILE.css', 'DIFF_FILE.patch', 'VERIFICATION.txt', 'ROLLBACK.sh'):
    p = here / name
    assert p.read_bytes()
    print('REOPENED', p, p.stat().st_size, flush=True)
