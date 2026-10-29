"""Run the HTTP suite against an isolated short-lived server and data directory."""
import os
import json
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from urllib.request import build_opener, ProxyHandler

ROOT = Path(__file__).resolve().parent.parent


def main():
    node = shutil.which('node')
    if not node:
        raise SystemExit('HTTP testleri için Node.js 22+ gerekiyor.')
    with tempfile.TemporaryDirectory(prefix='kredi-http-') as data:
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        base = f'http://127.0.0.1:{port}'
        env = dict(os.environ, KREDI_MODE='demo', KREDI_ENGINE='native',
                   KREDI_DATA_DIR=data, NO_PROXY='127.0.0.1,localhost')
        with tempfile.TemporaryFile() as log:
            process = subprocess.Popen(
                [sys.executable, 'app.py', '--port', str(port), '--mode', 'demo'],
                cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
            try:
                opener = build_opener(ProxyHandler({}))
                deadline = time.monotonic() + 20
                while time.monotonic() < deadline:
                    if process.poll() is not None:
                        raise RuntimeError('Test sunucusu başlatılamadı.')
                    try:
                        with opener.open(base + '/api/bootstrap', timeout=1):
                            break
                    except OSError:
                        time.sleep(0.1)
                else:
                    raise RuntimeError('Test sunucusu zamanında hazır olmadı.')
                subprocess.run([node, 'scripts/http-smoke.mjs', base],
                               cwd=ROOT, env=env, check=True, timeout=60)
                with opener.open(f'http://localhost:{port}/api/bootstrap', timeout=5) as response:
                    assert json.load(response)['mode'] == 'demo'
                print('Localhost address: verified.')
                with opener.open(base + '/api/logs', timeout=3) as response:
                    logged = json.load(response)
                with opener.open(base + '/api/logs', timeout=3) as response:
                    self_read = json.load(response)
                assert logged == self_read, 'Reading logs must not create new records'
                events = {row['event'] for row in logged['records']}
                assert {'review.run', 'customer.lookup', 'report.save', 'report.export',
                        'document.save', 'document.upload'} <= events
                assert any(row['event'] == 'document.upload' and row['phase'] == 'failed'
                           for row in logged['records'])
                assert 'bad.exe' not in json.dumps(logged)
                assert 'http-smoke-session' not in json.dumps(logged)
                assert not list(Path(data).rglob('*.log*')), 'Application logs must stay in memory'
                print('Session logs: critical events, error records, no self-logging and no log files verified.')
            except Exception:
                log.seek(0)
                print(log.read().decode('utf-8', errors='replace'), file=sys.stderr)
                raise
            finally:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)


if __name__ == '__main__':
    main()
