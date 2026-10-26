"""Restore only the recorded project source files, never a recursive deletion."""
import hashlib
import json
import shutil
import sys
from pathlib import Path

here = Path(__file__).resolve().parent
project = here.parent
target = Path(sys.argv[1]).resolve()
fixture = (here / 'rollback-copy').resolve()
if target not in (project, fixture):
    raise SystemExit('Target must be the project root or its evidence/rollback-copy fixture.')
original = json.loads((here / 'original-hashes.json').read_text(encoding='utf-8'))
modified = json.loads((here / 'modified-hashes.json').read_text(encoding='utf-8'))


def checked(base, relative):
    path = (base / relative).resolve()
    if not path.is_relative_to(base.resolve()) or path == base.resolve():
        raise SystemExit('Path escaped target root.')
    return path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


# Verify ALL paths and file contents before making the first change.
for rel, expected in original.items():
    if digest(checked(here / 'baseline', rel)) != expected:
        raise SystemExit('Baseline hash mismatch: ' + rel)
for rel, expected in modified.items():
    dest = checked(target, rel)
    if not dest.is_file() or digest(dest) != expected:
        raise SystemExit('Source changed since verification; retained without changes: ' + rel)
for rel in original:
    dest = checked(target, rel)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(checked(here / 'baseline', rel), dest)
removed = 0
for rel in modified.keys() - original.keys():
    checked(target, rel).unlink()
    removed += 1
assert all(digest(checked(target, rel)) == expected for rel, expected in original.items())
print(f'ROLLBACK_OK restored={len(original)} removed={removed}')
