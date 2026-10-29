"""Optional PDF intake tests; core tests do not need PDF authoring packages."""
import base64
import io
import unittest
from importlib.util import find_spec
import test_review
from kredi.documents import ingest


@unittest.skipUnless(find_spec('reportlab') and find_spec('pypdf'), 'PDF test extras not installed')
class PdfIntakeTests(unittest.TestCase):
    setUp = test_review.ReviewTests.setUp
    tearDown = test_review.ReviewTests.tearDown

    def test_text_pdf_fields_are_read_without_llm(self):
        from reportlab.pdfgen import canvas
        stream = io.BytesIO()
        pdf = canvas.Canvas(stream)
        pdf.drawString(50, 750, 'SYNTHETIC DOCUMENT FOR TESTING ONLY')
        pdf.drawString(50, 720, 'Unvan: DEMO Ornek Tarim Limited Sirketi')
        pdf.drawString(50, 700, 'Vergi Numarasi: 0000000001')
        pdf.save()
        result = ingest('1002', 'synthetic.pdf', base64.b64encode(stream.getvalue()).decode(),
                        'mali_tablo', '2026-10-01')
        self.assertTrue(result['readable'])
        self.assertEqual(result['fields']['tax_id'], '0000000001')

    def test_image_only_pdf_is_not_marked_readable(self):
        from reportlab.pdfgen import canvas
        stream = io.BytesIO()
        pdf = canvas.Canvas(stream)
        pdf.rect(20, 20, 200, 200, fill=1)
        pdf.showPage()
        pdf.save()
        result = ingest('1002', 'empty.pdf', base64.b64encode(stream.getvalue()).decode(),
                        'mali_tablo', '2026-10-01')
        self.assertFalse(result['readable'])
