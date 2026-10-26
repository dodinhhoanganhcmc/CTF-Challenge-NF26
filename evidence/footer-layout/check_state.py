import json
import re
import sys
from pathlib import Path

root = Path(sys.argv[1] if len(sys.argv) > 1 else '.').resolve()
css = (root / 'app/globals.css').read_text(encoding='utf-8')
game = (root / 'components/game.tsx').read_text(encoding='utf-8')
rule = re.search(r'(?m)^\.footer-bottom\s*\{([^}]+)\}', css)[1]
get = lambda key: re.search(re.escape(key) + r':([^;]+)', rule)[1].strip()
print(json.dumps({'footer_size': get('font-size'), 'footer_alignment': get('justify-content'),
                  'learning_strip': 'className="below-map"' in game}, separators=(',', ':')))
