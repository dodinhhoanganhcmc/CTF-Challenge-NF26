import importlib.util
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fastapi.testclient import TestClient

path = Path(sys.argv[1]).resolve()
spec = importlib.util.spec_from_file_location('health_target', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
with TestClient(module.app) as client:
    response = client.get('/health')
    print(f'HTTP {response.status_code} ' + json.dumps(response.json(), separators=(',', ':')))
    raise SystemExit(0 if response.status_code == 200 else 1)
