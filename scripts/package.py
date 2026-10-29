"""Create a clean, reproducible source ZIP without local state or secrets."""
import hashlib
from pathlib import Path
import zipfile

root = Path(__file__).resolve().parent.parent
destination = root.parent / 'outputs' / 'ticari-kredi-on-inceleme-v1.zip'
destination.parent.mkdir(parents=True, exist_ok=True)
excluded = {'.venv', '.deps', '__pycache__', 'runtime', '.git', '_yedekler', '.pytest_cache', 'htmlcov', '.idea', '.vscode', 'outputs'}
with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(root.rglob('*')):
        rel = path.relative_to(root)
        private_file = (path.name == '.env' or
                        (path.name.startswith('.env.') and path.name != '.env.example') or
                        path.suffix in {'.db', '.sqlite', '.sqlite3', '.log', '.pyc'} or
                        '.sqlite3-' in path.name or '.db-' in path.name)
        if path.is_file() and not (set(rel.parts) & excluded) and not private_file:
            archive.write(path, Path(root.name) / rel)
with zipfile.ZipFile(destination) as archive:
    assert archive.testzip() is None
    count = len(archive.namelist())
print(f'{destination}\nFiles: {count}\nSHA256: {hashlib.sha256(destination.read_bytes()).hexdigest()}')
