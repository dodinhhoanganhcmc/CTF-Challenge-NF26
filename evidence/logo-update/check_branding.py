import json
import sys
from pathlib import Path
from PIL import Image

root = Path(sys.argv[1] if len(sys.argv) > 1 else '.').resolve()
sys.path.insert(0, str(root))
from backend.main import create_app
from fastapi.testclient import TestClient
import tempfile

sizes = []
for name in ('club-logo.png', 'club-logo-light.jpg'):
    path = root / 'public' / name
    if path.is_file():
        with Image.open(path) as im:
            im.verify()
        with Image.open(path) as im:
            assert im.convert('RGBA').getchannel('A').getextrema() == (255, 255), 'Web logo must remain fully opaque.'
            sizes.append(f'{im.width}x{im.height}')
    else:
        sizes.append('missing')
with tempfile.TemporaryDirectory() as folder:
    with TestClient(create_app(Path(folder) / 'check.sqlite3')) as client:
        ready = client.get('/api/v1/catalog').json()['logo_ready']
print(f'BRANDING logo_ready={str(ready).lower()} primary={sizes[0]} alternative={sizes[1]}')
