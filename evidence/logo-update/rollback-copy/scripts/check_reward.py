"""Local organizer lookup; no public organizer credential or admin endpoint."""
import argparse
import json
import os
import re
import sqlite3
from pathlib import Path

parser = argparse.ArgumentParser(description='Tra mã hoàn thành để đối chiếu khi phát sticker.')
parser.add_argument('code')
parser.add_argument('--database', type=Path, default=Path(os.getenv('DATABASE_PATH', str(Path(__file__).resolve().parent.parent / 'backend/data/game.sqlite3'))))
args = parser.parse_args()
if not re.fullmatch(r'NF26-[A-F0-9]{12}', args.code):
    parser.error('Mã có định dạng NF26- và 12 ký tự hex viết hoa.')
with sqlite3.connect(args.database.resolve().as_uri() + '?mode=ro', uri=True) as con:
    con.row_factory = sqlite3.Row
    row = con.execute('''SELECT s.name,p.mode,p.finished,ROUND(p.finished-p.started) seconds,
        COUNT(v.stage) stages,SUM(v.points) points FROM progress p JOIN sessions s ON s.id=p.session
        JOIN solves v ON v.session=p.session AND v.mode=p.mode WHERE p.reward=? GROUP BY p.session,p.mode''', (args.code,)).fetchone()
    if row and row['stages'] == 5:
        print(json.dumps(dict(row), ensure_ascii=True))
    else:
        print('NOT_FOUND'); raise SystemExit(1)
