"""WCAG sRGB contrast checks for the actual CSS theme tokens."""
import json
import re
from pathlib import Path


def luminance(color):
    values = [int(color[i:i+2], 16) / 255 for i in (1, 3, 5)]
    linear = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in values]
    return sum(a*b for a, b in zip(linear, (.2126, .7152, .0722)))


def contrast(a, b):
    x, y = sorted((luminance(a), luminance(b)))
    return (y + .05) / (x + .05)


root = Path(__file__).resolve().parent.parent
css = (root / 'app/globals.css').read_text(encoding='utf-8-sig')
results = []
for theme, selector in [('light', ':root'), ('dark', ":root[data-theme='dark']")]:
    block = re.search(re.escape(selector) + r'\s*\{([^}]+)\}', css)[1]
    colors = dict(re.findall(r'--([\w-]+):\s*(#[0-9a-fA-F]{6})(?=[;\s])', block))
    for fg in ('ink', 'muted', 'coral'):
        for bg in ('paper', 'panel', 'ocean', 'soft'):
            results.append({'theme': theme, 'foreground': fg, 'background': bg,
                            'ratio': round(contrast(colors[fg], colors[bg]), 3), 'threshold': 4.5})
    for fg in ('success', 'error'):
        results.append({'theme': theme, 'foreground': fg, 'background': 'panel',
                        'ratio': round(contrast(colors[fg], colors['panel']), 3), 'threshold': 4.5})
    button_text = colors['panel'] if theme == 'light' else '#171717'
    results.append({'theme': theme, 'foreground': 'button-label', 'background': 'coral',
                    'ratio': round(contrast(button_text, colors['coral']), 3), 'threshold': 4.5})
    for fg in ('control-border', 'focus'):
        results.append({'theme': theme, 'foreground': fg, 'background': 'panel',
                        'ratio': round(contrast(colors[fg], colors['panel']), 3), 'threshold': 3.0})
failed = [row for row in results if row['ratio'] < row['threshold']]
output = root / 'evidence/white-black-title/palette-contrast.json'
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(results, indent=2), encoding='utf-8')
if failed:
    print(json.dumps(failed)); raise SystemExit(1)
print(f"PALETTE_OK pairs={len(results)} min_text={min(r['ratio'] for r in results if r['threshold']==4.5):.2f} min_ui={min(r['ratio'] for r in results if r['threshold']==3):.2f}")
