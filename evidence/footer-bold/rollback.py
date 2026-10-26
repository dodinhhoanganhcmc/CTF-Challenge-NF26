"""Restore the pre-logo source without touching input originals or player data."""
import hashlib
import json
import shutil
import sys
from pathlib import Path

here = Path(__file__).resolve().parent
project = here.parents[1]
target = Path(sys.argv[1]).resolve()
if target not in (project, here / 'rollback-copy'):
    raise SystemExit('Expected the project root or the dedicated rollback-copy fixture.')
original = json.loads((here / 'original-hashes.json').read_text())
modified = json.loads((here / 'modified-hashes.json').read_text())


def checked(base, relative):
    p = (base / relative).resolve()
    if not p.is_relative_to(base.resolve()) or p == base.resolve():
        raise SystemExit('Path escaped target root.')
    return p


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


for rel, expected in original.items():
    assert digest(checked(here / 'baseline', rel)) == expected, 'Baseline mismatch: ' + rel
for rel, expected in modified.items():
    path = checked(target, rel)
    if not path.is_file() or digest(path) != expected:
        raise SystemExit('Later edits retained; rollback stopped before writes: ' + rel)
for rel in original:
    path = checked(target, rel)
    path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(checked(here / 'baseline', rel), path)
for rel in modified.keys() - original.keys():
    checked(target, rel).unlink()
assert all(digest(checked(target, rel)) == expected for rel, expected in original.items())
print(f'ROLLBACK_OK restored={len(original)} removed={len(modified.keys()-original.keys())}')
