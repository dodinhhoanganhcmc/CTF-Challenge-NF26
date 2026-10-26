import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
root = Path(sys.argv[1] if len(sys.argv) > 1 else '.').resolve()
css = (root / 'app/globals.css').read_text(encoding='utf-8-sig')
game = (root / 'components/game.tsx').read_text(encoding='utf-8-sig')
colors = []
for selector in (':root', ":root[data-theme='dark']"):
    block = re.search(re.escape(selector) + r'\s*\{([^}]+)\}', css)[1]
    colors.append(re.search(r'--paper:\s*(#[a-fA-F0-9]{6})', block)[1].lower())
heading = re.search(r'<h1 id="title">(.*?)</h1>', game, re.S)[1].replace('<br />', ' ')
heading = re.sub('<[^>]+>', '', heading)
print(json.dumps({'light': colors[0], 'dark': colors[1], 'title': heading}, ensure_ascii=False, separators=(',', ':')))
