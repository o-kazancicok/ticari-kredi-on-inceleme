"""Export synthetic input records and one report using an isolated database."""
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
from kredi import storage
from kredi.seed import seed
from kredi.service import review, markdown

scratch = root / 'runtime' / 'example-build'
scratch.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(dir=scratch) as directory, patch.object(storage, 'DB_PATH', Path(directory) / 'examples.db'):
    seed()
    (root / 'examples' / 'basvurular.json').write_text(
        json.dumps(storage.list_applications(), ensure_ascii=False, indent=2), encoding='utf-8')
    (root / 'docs' / 'ORNEK_RAPOR.md').write_text(markdown(review('1003')), encoding='utf-8')
print('Synthetic examples and sample report built.')
