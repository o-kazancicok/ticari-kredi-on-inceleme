"""Load local settings and check runtime prerequisites without exposing secrets."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
from urllib.parse import urlsplit
from urllib.request import build_opener, ProxyHandler

ROOT = Path(__file__).resolve().parent.parent


def load_environment(path=None):
    from dotenv import load_dotenv
    # Terminal/CI variables take precedence over the local file.
    load_dotenv(path or ROOT / '.env', override=False, interpolate=False)


def validate_settings():
    mode = os.getenv('KREDI_MODE', 'demo')
    engine = os.getenv('KREDI_ENGINE', 'native')
    if mode not in ('demo', 'agent'):
        raise ValueError('KREDI_MODE demo veya agent olmalıdır.')
    if engine not in ('native', 'langgraph'):
        raise ValueError('KREDI_ENGINE native veya langgraph olmalıdır.')
    try:
        port = int(os.getenv('KREDI_PORT', '8765'))
        if not 1 <= port <= 65535:
            raise ValueError()
    except ValueError:
        raise ValueError('KREDI_PORT 1–65535 arasında bir tam sayı olmalıdır.') from None
    if mode == 'agent':
        url = urlsplit(os.getenv('OLLAMA_URL', 'http://127.0.0.1:11434'))
        try:
            valid_port = url.port is None or 1 <= url.port <= 65535
        except ValueError:
            valid_port = False
        if (url.scheme != 'http' or url.hostname not in ('127.0.0.1', 'localhost', '::1')
                or url.username or url.password or url.path not in ('', '/')
                or url.query or url.fragment or not valid_port):
            raise ValueError('OLLAMA_URL yerel bir HTTP adresi olmalıdır (örn. http://127.0.0.1:11434).')
        if not os.getenv('OLLAMA_MODEL', 'qwen3:4b').strip():
            raise ValueError('OLLAMA_MODEL boş bırakılamaz.')


def check_environment():
    """Return (success, human readable checks); never generate application records."""
    checks = []
    if sys.version_info < (3, 11):
        return False, ['HATA: Python 3.11 veya üstü gerekiyor.']
    checks.append('OK: Python sürümü uygun.')
    try:
        validate_settings()
    except ValueError as exc:
        return False, checks + [f'HATA: {exc}']
    checks.append('OK: Ortam ayarları geçerli.')
    mode = os.getenv('KREDI_MODE', 'demo')
    packages = ['pypdf']
    if mode == 'agent' and os.getenv('KREDI_ENGINE', 'native') == 'langgraph':
        packages.append('langgraph')
    for name in packages:
        if importlib.util.find_spec(name) is None:
            return False, checks + [f'HATA: {name} eksik. İlgili requirements dosyasını kurun.']
    checks.append('OK: Seçilen modun Python bağımlılıkları mevcut.')
    data = Path(os.getenv('KREDI_DATA_DIR', str(ROOT / 'runtime'))).expanduser().resolve()
    try:
        data.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryFile(dir=data):
            pass
    except OSError:
        return False, checks + ['HATA: Veri dizinine yazılamıyor. KREDI_DATA_DIR ayarını kontrol edin.']
    checks.append('OK: Veri dizini yazılabilir.')
    if mode == 'agent':
        url = os.getenv('OLLAMA_URL', 'http://127.0.0.1:11434').rstrip('/')
        model = os.getenv('OLLAMA_MODEL', 'qwen3:4b')
        try:
            # Local requests should not be routed through a machine's HTTP proxy.
            with build_opener(ProxyHandler({})).open(url + '/api/tags', timeout=5) as response:
                payload = json.load(response)
            names = {item['name'] for item in payload['models']}
        except (OSError, ValueError, KeyError, TypeError):
            return False, checks + ['HATA: Ollama model listesine erişilemiyor. Yerel servisi ve adresi kontrol edin.']
        if model not in names and model + ':latest' not in names:
            return False, checks + ['HATA: Seçilen model Ollama içinde kurulu değil. OLLAMA_MODEL modelini indirin.']
        checks.append('OK: Ollama erişilebilir ve seçilen model kurulu.')
        checks.append('BİLGİ: Modelin araç çağırma başarısı ayrıca uçtan uca doğrulanmalıdır.')
    return True, checks
