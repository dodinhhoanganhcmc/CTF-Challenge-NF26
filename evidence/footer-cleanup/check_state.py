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
footer = re.search(r'<footer>(.*?)</footer>', game, re.S)[1]
logo = re.search(r'(?m)^\.club-logo \{([^}]+)\}', css)[1]
border = re.search(r'border:([^;]+)', logo)[1]
print(json.dumps({'light': colors[0], 'dark': colors[1], 'logo_border': border,
                  'footer_logo': '<ClubLogo' in footer,
                  'copyright': "(c) CMC Infrasec x NextFest '26" in footer,
                  'weight_label': 'Weight ≤ 10' in game,
                  'poppins': "--font-sans: 'Poppins'" in css}, ensure_ascii=False, separators=(',', ':')))
