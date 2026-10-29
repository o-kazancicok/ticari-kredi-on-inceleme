"""Start the installed local Ollama runtime; download a model only with --pull."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from urllib.parse import urlsplit
from urllib.request import build_opener, ProxyHandler, Request

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from kredi.environment import load_environment


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser()
    parser.add_argument('--pull', action='store_true')
    args = parser.parse_args()
    load_environment()
    url = os.getenv('OLLAMA_URL', 'http://127.0.0.1:11434').rstrip('/')
    address = urlsplit(url)
    if (address.scheme != 'http' or address.hostname not in ('127.0.0.1', 'localhost', '::1')
            or address.username or address.password or address.path or address.query or address.fragment):
        raise SystemExit('Ollama için yalnızca yerel HTTP adresi kullanılabilir.')
    opener = build_opener(ProxyHandler({}))

    def tags():
        with opener.open(url + '/api/tags', timeout=3) as response:
            return json.load(response)['models']

    try:
        models = tags()
    except (OSError, ValueError, KeyError):
        manifest_path = ROOT / 'runtime' / 'ollama-install.json'
        executable = None
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
            candidate = Path(manifest['executable']).resolve()
            if candidate.is_relative_to((ROOT / 'runtime').resolve()) and candidate.is_file():
                executable = str(candidate)
        executable = executable or shutil.which('ollama')
        if not executable:
            candidate = Path(os.getenv('LOCALAPPDATA', '')) / 'Programs' / 'Ollama' / 'ollama.exe'
            if candidate.is_file():
                executable = str(candidate)
        if not executable:
            raise SystemExit('Ollama bulunamadı. Önce .\\setup-ollama.ps1 çalıştırın.')
        data = Path(os.getenv('KREDI_DATA_DIR', str(ROOT / 'runtime'))).resolve()
        data.mkdir(parents=True, exist_ok=True)
        env = dict(os.environ, OLLAMA_HOST=address.netloc, OLLAMA_NO_CLOUD='1')
        with (data / 'ollama-server.log').open('ab') as log:
            process = subprocess.Popen([executable, 'serve'], env=env,
                                       stdout=log, stderr=subprocess.STDOUT,
                                       creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        deadline = time.monotonic() + 30
        while True:
            try:
                models = tags()
                break
            except (OSError, ValueError, KeyError):
                if process.poll() is not None or time.monotonic() >= deadline:
                    raise SystemExit('Ollama başlatılamadı. runtime/ollama-server.log kaydını kontrol edin.')
                time.sleep(0.5)
    print('Ollama yerel servisi hazır.', flush=True)
    model = os.getenv('OLLAMA_MODEL', 'qwen3:4b')
    if not any(item['name'] in (model, model + ':latest') for item in models):
        if not args.pull:
            raise SystemExit('Model kurulu değil. İndirmek için .\\setup-ollama.ps1 çalıştırın.')
        print(f'Model indiriliyor: {model}', flush=True)
        request = Request(url + '/api/pull', json.dumps({'model': model, 'stream': True}).encode(),
                          {'Content-Type': 'application/json'})
        last = 0
        with opener.open(request, timeout=900) as response:
            for line in response:
                item = json.loads(line)
                if item.get('error'):
                    raise SystemExit('Model indirilemedi: ' + item['error'])
                if item.get('total') and time.monotonic() - last > 10:
                    print(f'Model indirme: {item.get("completed", 0) / item["total"]:.0%}', flush=True)
                    last = time.monotonic()
        models = tags()
        if not any(item['name'] in (model, model + ':latest') for item in models):
            raise SystemExit('Model indirme sonrası doğrulanamadı.')
    print(f'Model hazır: {model}', flush=True)


if __name__ == '__main__':
    main()
