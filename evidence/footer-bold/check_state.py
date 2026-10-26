import json
import re
import sys
from pathlib import Path

root = Path(sys.argv[1] if len(sys.argv) > 1 else '.').resolve()
css = (root / 'app/globals.css').read_text(encoding='utf-8')
rules = re.findall(r'\.footer-bottom > span:first-child\s*\{([^}]+)\}', css)
weight = re.search(r'font-weight:([^;]+)', rules[-1])[1].strip()
if weight.startswith('var('):
    weight = re.search(r'--font-weight-footer:\s*(\d+)', css)[1]
print(json.dumps({'font':'Poppins', 'weight':int(weight)}, separators=(',', ':')))
