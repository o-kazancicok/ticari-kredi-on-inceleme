"""Restricted text/PDF intake; deterministic labelled fields, no invented extraction."""
import base64
import binascii
import io
import re
import uuid
from datetime import date
from pathlib import Path
from . import storage
from .policy import POLICY, normalize
from .operations import critical

MAX_BYTES = 2 * 1024 * 1024
LABELS = {'unvan': 'title', 'vergi numarasi': 'tax_id', 'hukuki sekil': 'legal_form',
          'kurulus tarihi': 'foundation_date', 'faaliyet konusu': 'activity', 'nace': 'nace'}


@critical('document.upload', 'application_id', fields=('kind',))
def ingest(application_id, name, encoded, kind, issued_on):
    if kind not in POLICY['required_documents']:
        raise ValueError('Desteklenmeyen belge türü.')
    try:
        parsed_date = date.fromisoformat(issued_on)
    except (TypeError, ValueError):
        raise ValueError('Düzenleme tarihi YYYY-AA-GG biçiminde olmalıdır.') from None
    if not isinstance(name, str) or len(name) > 150:
        raise ValueError('Geçersiz dosya adı.')
    suffix = Path(name).suffix.lower()
    if suffix not in ('.txt', '.pdf'):
        raise ValueError('Yalnızca .txt veya metin içeren .pdf kabul edilir.')
    if not isinstance(encoded, str) or len(encoded) > 4 * MAX_BYTES // 3 + 8:
        raise ValueError('Dosya en fazla 2 MB olabilir.')
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error):
        raise ValueError('Dosya kodlaması geçersiz.') from None
    if len(raw) > MAX_BYTES or not raw:
        raise ValueError('Dosya boş veya 2 MB sınırını aşıyor.')
    try:
        if suffix == '.pdf':
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(raw))
            if reader.is_encrypted or len(reader.pages) > 10:
                raise ValueError('Şifreli veya 10 sayfadan uzun PDF desteklenmiyor.')
            text = '\n'.join(page.extract_text() or '' for page in reader.pages)
        else:
            text = raw.decode('utf-8-sig')
    except ImportError:
        raise ValueError('PDF okumak için requirements.txt paketlerini kurun.') from None
    except Exception:
        raise ValueError('Dosya metni okunamadı; UTF-8 TXT veya geçerli metin PDF kullanın.') from None
    if len(text) > 100_000:
        raise ValueError('Belge metni çok uzun.')
    fields = {}
    for line in text.splitlines():
        if ':' in line:
            label, value = line.split(':', 1)
            key = LABELS.get(normalize(label))
            if key:
                if len(value.strip()) > 1000:
                    raise ValueError('Belge alanı en fazla 1000 karakter olabilir: ' + label)
                if key in fields and fields[key] != value.strip():
                    raise ValueError('Aynı alan için çelişkili değerler var: ' + label)
                fields[key] = value.strip()
    doc = {'id': 'U-' + uuid.uuid4().hex, 'name': re.split(r'[/\\]', name)[-1], 'kind': kind,
           'issued_on': parsed_date.isoformat(), 'readable': bool(text.strip()),
           'fields': fields, 'text': text, 'synthetic': True, 'intake': 'labelled_text',
           'date_source': 'user_declared'}
    storage.add_document(application_id, doc)
    return doc
