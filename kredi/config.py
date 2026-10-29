import os
from pathlib import Path
from .environment import load_environment

load_environment()

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv('KREDI_DATA_DIR', str(ROOT / 'runtime'))).resolve()
DB_PATH = DATA_DIR / 'kredi.sqlite3'
AS_OF = '2026-10-17'  # Reproducible demo date, not the computer's clock.
MODE = os.getenv('KREDI_MODE', 'demo')
MODEL = os.getenv('OLLAMA_MODEL', 'qwen3:4b')
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://127.0.0.1:11434').rstrip('/')
DISCLAIMER = 'Dosya ön inceleme raporu • Nihai değerlendirme yetkili birim tarafından yapılır'
