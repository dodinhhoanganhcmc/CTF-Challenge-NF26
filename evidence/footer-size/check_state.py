import json
import re
import sys
from pathlib import Path

root = Path(sys.argv[1] if len(sys.argv) > 1 else '.').resolve()
css = (root / 'app/globals.css').read_text(encoding='utf-8')
sizes = re.findall(r'--text-footer:\s*(\d+)px', css)
if sizes:
    desktop, mobile = int(sizes[0]), int(sizes[-1])
else:
    desktop = int(re.search(r'(?m)^\.footer-bottom\s*\{[^}]*font-size:(\d+)px', css)[1])
    mobile = int(re.search(r'\.footer-bottom\s*\{[^}]*flex-wrap:wrap;[^}]*font-size:(\d+)px', css)[1])
weight = int(re.search(r'--font-weight-footer:\s*(\d+)', css)[1])
print(json.dumps({'desktop_px': desktop, 'mobile_px': mobile, 'weight': weight}, separators=(',', ':')))
