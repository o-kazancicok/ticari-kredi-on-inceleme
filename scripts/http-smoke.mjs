// Run against a NEW isolated data directory (see README). Mutates synthetic 1002.
import assert from 'node:assert/strict';
const base = process.argv[2] || 'http://127.0.0.1:8767';
let count = 0;
async function request(path, body, expected = 200, headers = {}) {
 const response = await fetch(base + path, body === undefined ? {headers} : {
  method:'POST', headers:{'Content-Type':'application/json', ...headers}, body:JSON.stringify(body)});
 assert.equal(response.status,expected,path);
 count++;
 return response.headers.get('content-type').includes('json') ? response.json() : response.text();
}
const bootstrap = await request('/api/bootstrap');
assert.equal(bootstrap.mode,'demo'); assert.equal(bootstrap.applications.length,5);
assert.ok((await request('/')).includes('Başvuru ön inceleme'));
assert.ok((await request('/app.js')).includes('escapeHtml'));
assert.equal((await request('/api/applications/1002/review',{})).tasks.length,1);
await request('/api/applications/1002/attach-financial',{},201);
const resumed = await request('/api/chat',{session_id:'http-smoke-session',application_id:'1002',message:'Tekrar incele'});
assert.equal(resumed.report.tasks.length,0);assert.equal(resumed.report.changes[0].after,'uygun');
assert.ok((await request('/api/applications/1002/export')).includes('Nihai değerlendirme'));
assert.ok((await request('/api/applications/1002/history')).length>0);
assert.equal((await request('/api/applications/1005/review',{})).counts.kontrol_edilemedi,6);
await request('/api/applications/9999/report',undefined,404);
await request('/api/applications/1001/review',{},403,{'Origin':'https://example.invalid'});
await request('/api/applications/1001/upload',{name:'bad.exe',data:'eA==',kind:'mali_tablo',issued_on:'2026-10-01'},400);
const docs = await request('/api/applications/1002/documents');
const financial = docs.find(d=>d.kind==='mali_tablo');
assert.ok(financial);
await request('/api/applications/1001/remove-document',{document_id:financial.id},400);
await request('/api/applications/1002/remove-document',{document_id:financial.id},403,{'Origin':'https://example.invalid'});
await request('/api/applications/1002/remove-document',{document_id:financial.id});
await request('/api/applications/1002/remove-document',{document_id:financial.id},400);
assert.ok(!(await request('/api/applications/1002/documents')).some(d=>d.id===financial.id));
const stale = await request('/api/applications/1002/report');
assert.equal(stale.documents_changed,true);assert.equal(stale.tasks.length,0);
assert.ok((await request('/api/applications/1002/export')).includes('önceki belge kümesine'));
assert.equal((await request('/api/applications/1002/review',{})).tasks.length,1);
assert.equal((await request('/api/applications/1002/report')).documents_changed,false);
console.log(`HTTP smoke: ${count} requests passed; resume, exports, service outage, origin, invalid upload and document removal verified.`);
