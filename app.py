"""Run with python app.py --port 8765 [--mode agent]."""
import argparse
import os
import sys
from kredi.environment import load_environment, check_environment

if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    try:
        load_environment()
    except ImportError:
        raise SystemExit('Ortam bağımlılıkları eksik. Önce setup.ps1 dosyasını çalıştırın.')
    parser = argparse.ArgumentParser(description='Ticari kredi dosyası ön inceleme')
    parser.add_argument('--port', type=int)
    parser.add_argument('--mode', choices=['demo', 'agent'], default=os.getenv('KREDI_MODE', 'demo'))
    parser.add_argument('--data-dir', help='İzole demo verileri için dizin')
    parser.add_argument('--check', action='store_true', help='Ortamı kontrol et ve çık')
    parser.add_argument('--open-browser', action='store_true', help='HTTP yanıtı doğrulandıktan sonra tarayıcıyı aç')
    args = parser.parse_args()
    os.environ['KREDI_MODE'] = args.mode
    if args.port is not None:
        os.environ['KREDI_PORT'] = str(args.port)
    if args.data_dir:
        os.environ['KREDI_DATA_DIR'] = args.data_dir
    ok, checks = check_environment()
    for message in checks:
        print(message, flush=True)
    if not ok:
        raise SystemExit(1)
    if args.check:
        raise SystemExit(0)
    from kredi.web import serve
    try:
        serve(int(os.getenv('KREDI_PORT', '8765')), open_browser=args.open_browser)
    except OSError:
        raise SystemExit('Sunucu başlatılamadı veya HTTP yanıtı alınamadı. Portu kontrol edin. Farklı port: .\\start.ps1 -Port 8766') from None
