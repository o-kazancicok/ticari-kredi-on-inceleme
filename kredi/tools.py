"""Application-scoped tools shared by demo, LangGraph and MCP adapters."""
from . import storage, checks
from .config import AS_OF
from .policy import POLICY, search_policy
from .operations import operation

TOOL_INFO = {
    'get_application': 'Başvuru beyanı ve kefil kaydını getirir. Önce bunu çağır.',
    'get_customer': 'Müşteri servisini sorgular; hata olursa unavailable döner, veri uydurulmaz.',
    'get_documents': 'Başvuru belgelerini ve kaynak kimliklerini getirir.',
    'get_policy': 'Bu ürünün tam ve sürümlü eğitim prosedürünü getirir.',
    'check_identity': 'Firma kimliği ve yaşını kontrol eder. Dört get aracı önceden çağrılmalıdır.',
    'check_activity': 'Faaliyet/NACE kontrolü. Dört get aracı önceden çağrılmalıdır.',
    'check_contact': 'İletişim kontrolü. Dört get aracı önceden çağrılmalıdır.',
    'check_guarantor': 'Kefil kontrolü. Dört get aracı önceden çağrılmalıdır.',
    'check_documents': 'Belge varlığı ve tarihi kontrolü. Dört get aracı önceden çağrılmalıdır.',
    'search_policy': 'Belirsiz bulgu için ürün prosedüründe anahtar kelime araması yapar. query gerekir.',
    'read_document': 'Seçili başvurudaki bir belgenin metnini ve alanlarını okur. document_id gerekir.',
}


class ReviewTools:
    def __init__(self, application_id, as_of=AS_OF):
        self.application_id = application_id
        self.as_of = as_of
        self.facts = {}
        self.results = {}
        self.trace = []

    def call(self, name, arguments=None):
        arguments = arguments or {}
        if name not in TOOL_INFO or not isinstance(arguments, dict):
            raise ValueError('İzin verilmeyen araç veya parametre. Başvuru kapsamı değiştirilemez.')
        if name == 'search_policy':
            if set(arguments) != {'query'} or not isinstance(arguments['query'], str) or not 1 <= len(arguments['query']) <= 500:
                raise ValueError('query 1–500 karakter olmalıdır.')
            result = search_policy(arguments['query'])
        elif name == 'read_document':
            if set(arguments) != {'document_id'}:
                raise ValueError('Yalnızca document_id kabul edilir.')
            result = next((d for d in storage.documents(self.application_id) if d['id'] == arguments['document_id']), None)
            if result is None:
                raise ValueError('Belge seçili başvuru kapsamında bulunamadı.')
            result = result | {'text': result.get('text', '')[:8000],
                               'text_truncated': len(result.get('text', '')) > 8000}
        elif arguments:
            raise ValueError('Bu araç parametre kabul etmez; başvuru kapsamı sabittir.')
        elif name == 'get_application':
            app = storage.get_application(self.application_id)
            self.facts['application'] = app
            result = {k: v for k, v in app.items() if k not in ('customer', 'customer_service_error')}
        elif name == 'get_customer':
            with operation('customer.lookup', self.application_id) as summary:
                app = storage.get_application(self.application_id)
                customer = None if app['customer_service_error'] else app['customer']
                self.facts['customer'] = customer
                result = {'status': 'unavailable' if customer is None else 'ok', 'data': customer}
                summary['outcome'] = 'unavailable' if customer is None else 'available'
        elif name == 'get_documents':
            docs = storage.documents(self.application_id)
            self.facts['documents'] = docs
            result = [d | {'text': d.get('text', '')[:2000],
                            'text_truncated': len(d.get('text', '')) > 2000} for d in docs]
        elif name == 'get_policy':
            result = POLICY
            self.facts['policy'] = result
        else:
            if not all(key in self.facts for key in ('application', 'customer', 'documents', 'policy')):
                raise ValueError('Önce başvuru, müşteri, belge ve prosedür araçlarını çağırın.')
            group = name.removeprefix('check_')
            result = checks.CHECKERS[group](self.facts['application'], self.facts['customer'],
                                             self.facts['documents'], self.as_of)
            self.results[group] = result
        self.trace.append({'step': len(self.trace) + 1, 'tool': name,
                           'purpose': TOOL_INFO[name], 'arguments': arguments, 'status': 'ok' if not (
                               name == 'get_customer' and result['status'] == 'unavailable') else 'unavailable'})
        return result

    def complete(self):
        return set(self.results) == set(checks.GROUPS)

    def findings(self):
        return [item for group in checks.GROUPS for item in self.results.get(group, [])]


def schemas():
    result = []
    for name, description in TOOL_INFO.items():
        parameter = 'query' if name == 'search_policy' else 'document_id' if name == 'read_document' else None
        properties = {parameter: {'type': 'string'}} if parameter else {}
        result.append({'type': 'function', 'function': {'name': name, 'description': description,
                       'parameters': {'type': 'object', 'properties': properties,
                                      'required': [parameter] if parameter else [], 'additionalProperties': False}}})
    return result
