'use strict';
const $ = s => document.querySelector(s);
const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const labels = {uygun:'Uygun',eksik:'Eksik',dogrulama_gerekli:'Doğrulama gerekli',kontrol_edilemedi:'Kontrol edilemedi',uygulanamaz:'Uygulanamaz'};
const kinds = {vergi_levhasi:'Vergi levhası',faaliyet_belgesi:'Faaliyet belgesi',mali_tablo:'Mali tablo'};
const fieldNames = {title:'Firma unvanı',tax_id:'Vergi numarası',legal_form:'Hukuki şekil',foundation_date:'Kuruluş tarihi',activity:'Faaliyet konusu',nace:'NACE kodu',address:'Adres',phone:'Telefon',email:'E-posta',zip_code:'Posta kodu',guarantor:'Kefil bilgileri',entity_type:'Kişi türü',first_name:'Ad',last_name:'Soyad',citizen_id:'Kimlik numarası',tax_office:'Vergi dairesi',issued_on:'Düzenleme tarihi',readable:'Okunabilirlik',as_of:'İnceleme tarihi',sectors:'Faaliyet bilgileri',value:'Faaliyet açıklaması',code:'NACE kodu',percent:'Faaliyet payı',service:'Servis durumu',kinds:'Yüklenen belgeler'};
function fieldName(path) {
 const key=String(path||'').replace(/\[\d+\]/g,'').split('.').pop();
 return fieldNames[key] || 'Kayıt bilgisi';
}
function sourceInfo(source, documents=[]) {
 const [ref,path='']=String(source||'').split('#'), type=ref.split(':')[0];
 if(type==='application')return {title:path==='guarantor'?'Kefil kaydı':'Başvuru bilgileri',field:fieldName(path)};
 if(type==='customer')return {title:'Müşteri kaydı',field:fieldName(path)};
 if(type==='review')return {title:'İnceleme bilgileri',field:'İnceleme tarihi'};
 if(type==='documents')return {title:'Başvuru belgeleri',field:fieldName(path)};
 if(type==='document') {
  const id=ref.slice('document:'.length), doc=documents.find(d=>d.id===id);
  const kind=doc?.kind || Object.keys(kinds).find(k=>id.includes(k));
  return {title:kinds[kind]||'Yüklenen belge',field:fieldName(path)};
 }
 return {title:'Kaynak kayıt',field:fieldName(path)};
}
function valueHtml(value, depth=0) {
 if(value===null||value===undefined||value==='')return '<span class="evidence-empty">Bilgi bulunmuyor</span>';
 if(typeof value==='boolean')return value?'Evet':'Hayır';
 if(Array.isArray(value))return value.length?`<ul class="evidence-list">${value.map(v=>`<li>${valueHtml(v,depth+1)}</li>`).join('')}</ul>`:'<span class="evidence-empty">Kayıt bulunmuyor</span>';
 if(typeof value==='object')return depth<4?`<dl class="evidence-fields">${Object.entries(value).map(([k,v])=>`<dt>${escapeHtml(fieldNames[k]||kinds[k]||'Ek bilgi')}</dt><dd>${valueHtml(v,depth+1)}</dd>`).join('')}</dl>`:'Ek kayıt mevcut';
 const translations={LIMITED:'Limited şirket',ANONIM:'Anonim şirket',individual:'Gerçek kişi',organization:'Tüzel kişi',unavailable:'Bilgi alınamadı',ok:'Erişilebilir',...kinds};
 if(Object.hasOwn(translations,value))return escapeHtml(translations[value]);
 if(/^\d{4}-\d{2}-\d{2}$/.test(String(value)))return escapeHtml(String(value).split('-').reverse().join('.'));
 return escapeHtml(value);
}
function customerUnavailable(f) {
 return f.status==='kontrol_edilemedi' && /müşteri.*(yanıt|alınamadı|eriş)/i.test(f.explanation||'');
}
function renderFinding(f, documents=[]) {
 const unavailable=customerUnavailable(f);
 const cards=f.evidence.map(e=>{
  const info=sourceInfo(e.source,documents);
  const value=String(e.source).endsWith('#readable')?(e.value?'Metin okunabilir':'Metin okunamadı'):valueHtml(e.value);
  return `<div class="evidence-card"><div class="evidence-source">${escapeHtml(info.title)}</div><div class="evidence-label">${escapeHtml(info.field)}</div><div class="evidence-value">${value}</div></div>`;
 });
 if(unavailable&&!f.evidence.some(e=>String(e.source).startsWith('customer:')))cards.push('<div class="evidence-card evidence-unavailable"><div class="evidence-source">Müşteri kaydı</div><div class="evidence-label">Karşılaştırma kaynağı</div><div class="evidence-value">Bilgi alınamadı</div></div>');
 const policy=String(f.policy_source||'').match(/@([^#]+)#(.*)$/);
 const policyText=policy?`Sürüm ${policy[1]} · Madde ${policy[2]}`:'Dayanak bilgisi bulunmuyor';
 return `<article class="finding"><div class="finding-head"><b>${escapeHtml(kinds[f.label]||f.label)}</b><span class="badge ${escapeHtml(f.status)}">${escapeHtml(labels[f.status]||'Değerlendirilemedi')}</span></div><p>${escapeHtml(f.explanation)}</p>${f.action?`<div class="finding-action"><span>Sonraki adım</span>${escapeHtml(f.action)}</div>`:''}<details><summary>Karşılaştırılan bilgiler ve dayanak</summary><div class="evidence">${cards.join('')}</div><div class="evidence-policy"><b>Ürün prosedürü</b><span>${escapeHtml(policyText)}</span></div></details></article>`;
}
let state = {id:sessionStorage.getItem('kredi-selected')||'1002',report:null,documents:[],tab:'findings',bootstrap:null,busy:false,logs:[],logError:''};
let logsLoading=false;
const logEvents={'review.run':'Başvuru incelemesi','customer.lookup':'Müşteri kaydı sorgusu','model.request':'Yerel model çağrısı','document.upload':'Belge yükleme','document.save':'Belge kaydı','document.remove':'Belge silme','report.save':'Rapor kaydı','report.export':'Rapor dışa aktarma','server.run':'Uygulama oturumu','server.diagnostic':'Sunucu bildirimi'};
function renderLogs() {
 const phases={started:'Başladı',completed:'Tamamlandı',failed:'Hata',warning:'Uyarı'};
 const rows=state.logs.slice(-100).reverse();
 return '<div class="log-heading"><div><b>Oturum günlüğü</b><p>Kritik işlemler canlı izlenir. Kayıtlar uygulama kapandığında silinir.</p></div><span>Canlı · 2 sn</span></div>'+(state.logError?'<p class="muted" role="status">Günlük bağlantısı kapandı. Ekrandaki kayıtlar temizlendi.</p>':rows.length?`<ol class="operation-logs">${rows.map(row=>`<li class="operation-log"><div class="log-row"><b>${escapeHtml(logEvents[row.event]||'İşlem')}</b><span class="badge ${row.level==='ERROR'?'kontrol_edilemedi':row.level==='WARNING'?'dogrulama_gerekli':row.phase==='started'?'uygulanamaz':'uygun'}">${escapeHtml(phases[row.phase]||row.phase)}</span></div><div class="log-meta"><time>${escapeHtml(new Date(row.time).toLocaleTimeString('tr-TR',{timeZone:'Europe/Istanbul'}))}</time>${row.application_id?`<span>Başvuru ${escapeHtml(row.application_id)}</span>`:''}${Number.isFinite(row.duration_ms)?`<span>${escapeHtml((row.duration_ms/1000).toFixed(2))} sn</span>`:''}${row.trace_id?`<span title="${escapeHtml(row.trace_id)}">Takip: ${escapeHtml(row.trace_id.slice(0,8))}</span>`:''}</div>${row.error_type?`<p class="log-error">Hata türü: ${escapeHtml(row.error_type)}</p>`:''}${row.outcome==='unavailable'?'<p class="log-error">Müşteri kaydı alınamadı.</p>':''}${row.message?`<p>${escapeHtml(row.message)}</p>`:''}</li>`).join('')}</ol><p class="muted">Son ${rows.length} kayıt gösteriliyor. Oturumda en fazla 2.000 kayıt bellekte tutulur.</p>`:'<p class="muted">Henüz kritik işlem kaydı yok.</p>');
}
async function refreshLogs() {
 if(state.tab!=='logs'||logsLoading)return;
 logsLoading=true;
 try{const result=await api('/api/logs');state.logs=result.records;state.logError='';}
 catch(e){state.logs=[];state.logError='disconnected';}
 finally{logsLoading=false;if(state.tab==='logs')renderContent();}
}
const sessionKey = 'kredi-session';
if(!sessionStorage.getItem(sessionKey)) sessionStorage.setItem(sessionKey,crypto.randomUUID());
async function api(url, body) {
 const response = await fetch(url, body === undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
 const result = await response.json();
 if(!response.ok) throw new Error(result.error || 'İşlem tamamlanamadı.');
 return result;
}
function error(message) { $('#error').textContent = message || ''; $('#error').classList.toggle('hidden',!message); }
function setBusy(value) { state.busy=value; document.querySelectorAll('button,input,select').forEach(e=>e.disabled=value&&e.dataset.tab!=='logs'); $('#review').textContent=value?'İnceleme sürüyor…':(state.report?'Yeniden incele ↻':'Ön incelemeyi başlat →'); }
async function guarded(work) { error('');setBusy(true);try{await work();}catch(e){error(e.message);}finally{setBusy(false);} }
function renderModelUsage(report) {
 if(!report)return '';
 const u=report.model_usage, number=v=>Number.isFinite(v)?v.toLocaleString('tr-TR',{maximumFractionDigits:0}):'Ölçülmedi';
 const seconds=v=>Number.isFinite(v)?(v/1000).toLocaleString('tr-TR',{maximumFractionDigits:2})+' sn':'Ölçülmedi';
 if(report.mode==='demo')return '<section class="model-usage"><b>Kurallı inceleme</b><p>Bu incelemede LLM çağrısı yapılmadı. Token kullanılmadı.</p><span>İnceleme süresi: '+escapeHtml(seconds(report.review_duration_ms))+'</span></section>';
 if(!u)return '<section class="model-usage"><b>Model kullanımı</b><p>Bu eski raporda model kullanım ölçümleri bulunmuyor. Yeni bir incelemede ölçümler gösterilir.</p></section>';
 const fields=[['Model',u.models?.join(', ')||'Ölçülmedi'],['Motor',u.engine||'Ölçülmedi'],['LLM çağrısı',number(u.call_count)],['Giriş token',number(u.input_tokens)],['Çıkış token',number(u.output_tokens)],['Toplam token',number(u.total_tokens)],['İnceleme süresi',seconds(report.review_duration_ms)],['Model süresi',seconds(u.model_duration_ms)],['Üretim hızı',Number.isFinite(u.output_tokens_per_second)?u.output_tokens_per_second.toLocaleString('tr-TR',{maximumFractionDigits:1})+' token/sn':'Ölçülmedi']];
 return '<section class="model-usage" aria-label="Model kullanımı"><b>Model kullanımı · Bu inceleme</b><dl>'+fields.map(([label,value])=>`<div><dt>${escapeHtml(label)}</dt><dd>${escapeHtml(value)}</dd></div>`).join('')+'</dl><p>Token değerleri bu incelemedeki tüm model çağrılarının toplamıdır; tekrar gönderilen bağlam her çağrıda sayılır. Üretim hızı çıkış token / üretim süresidir.</p></section>';
}
function render() {
 const app=state.bootstrap.applications.find(a=>a.id===state.id), r=state.report;
 $('#applications').innerHTML=state.bootstrap.applications.map(a=>`<button class="case ${a.id===state.id?'active':''}" data-id="${a.id}" ${state.busy?'disabled':''}><b>${a.id} <span aria-hidden="true">↗</span></b><small>${escapeHtml(a.scenario)}</small></button>`).join('');
 $('#app-number').textContent='BAŞVURU / '+state.id;$('#company').textContent=app.title;$('#scenario').textContent=app.scenario;
 $('#review').textContent=r?'Yeniden incele ↻':'Ön incelemeyi başlat →';
 $('#download').href=`/api/applications/${state.id}/export`;$('#download').classList.toggle('hidden',!r);
 $('#model-usage').innerHTML=renderModelUsage(r);
 const counts=r?.counts||{};
 $('#stats').innerHTML=[['Toplam kontrol',r?.findings.length??'—','', '◫'],['Uygun',counts.uygun??(r?0:'—'),'good','✓'],['Açık iş',r?.tasks.length??'—','warn','↗'],['Kontrol edilemedi',counts.kontrol_edilemedi??(r?0:'—'),'','○']].map(([label,count,cls,icon])=>`<div class="stat ${cls}"><span>${label}</span><strong>${count}</strong><small>${icon}</small></div>`).join('');
 $('#report-status').innerHTML=r?`<div class="status-line ${r.tasks.length?'':'ready'}">${r.tasks.length?'Tamamlanması gereken işler var.':'Tanımlı ön kontroller tamamlandı; dosya uzman incelemesine hazır.'} <span>· Rapor #${r.report_id}</span></div>`:'';
 if(r?.documents_changed)$('#report-status').innerHTML='<div class="status-line" role="status">Belgeler değişti. Görünen rapor önceki belge kümesine aittir; güncel sonuçlar için yeniden inceleyin.</div>'+$('#report-status').innerHTML;
 $('#changes').innerHTML=r?.changes.length?`<div class="change">${r.changes.map(c=>`${escapeHtml(kinds[c.label]||c.label)}: ${labels[c.before]} → ${labels[c.after]}`).join('<br>')}</div>`:'';
 $('#tasks').innerHTML=!r?'<p class="muted">İnceleme sonrası gerekli işler burada listelenir.</p>':r.tasks.length?r.tasks.map((t,i)=>`<div class="task"><span class="task-number">${i+1}</span><div><b>${escapeHtml(kinds[t.label]||t.label)}</b><p>${escapeHtml(t.action)}</p></div></div>`).join(''):'<p class="muted">Açık iş yok. Sonuç bir kredi onayı değildir.</p>';
 document.querySelectorAll('.tab').forEach(t=>t.classList.toggle('selected',t.dataset.tab===state.tab));
 renderContent();
}
function renderContent() {
 const r=state.report;
 if(state.tab==='findings') {
  const outage=r?.findings.some(customerUnavailable)?'<div class="service-alert" role="status"><b>Müşteri bilgilerine erişilemiyor</b><p>Başvuru ve belgeler incelendi. Müşteri kaydı gerektiren karşılaştırmalar, servis erişimi sağlandığında yeniden yapılmalıdır.</p></div>':'';
  $('#content').innerHTML=!r?'<div class="empty"><div class="empty-icon">▤</div><h3>Dosyanın bütününü gör.</h3><p>İncelemeyi başlattığında kaynaklı kontrol sonuçları<br>ve tamamlanacak işler burada görünür.</p></div>':outage+r.findings.map(f=>renderFinding(f,state.documents)).join('');
 } else if(state.tab==='logs') {
  $('#content').innerHTML=renderLogs();
 } else if(state.tab==='documents') {
  const hasFinancial=state.documents.some(d=>d.kind==='mali_tablo');
  $('#content').innerHTML=state.documents.map(d=>`<div class="doc"><div class="doc-heading"><b>${escapeHtml(kinds[d.kind])}</b><button type="button" class="delete-document" data-delete-document="${escapeHtml(d.id)}" aria-label="${escapeHtml(d.name)} belgesini sil" ${state.busy?'disabled':''}>Sil</button></div><small>${escapeHtml(d.name)} · ${escapeHtml(d.issued_on)} · ${d.readable?'Metin okunabilir':'Okunamadı'}</small><small>Kaynak: ${escapeHtml(d.id)}</small></div>`).join('')+
   (state.id==='1002'&&!hasFinancial?'<div class="upload"><b>Bekleyen belge</b><p class="muted">Mali tabloyu ekleyip dosya incelemesini güncelleyin.</p><button id="attach-financial" class="primary">Mali tabloyu ekle +</button></div>':'')+
   `<form id="upload-form" class="upload"><b>Belge ekle</b><p class="muted">TXT veya metin PDF · En fazla 2 MB / 10 sayfa. Taranmış PDF için OCR yoktur. Düzenleme tarihi kullanıcı beyanıdır. Firma alanları README’deki etiketli biçimde okunur.</p><label for="kind">Belge türü</label><select id="kind">${Object.entries(kinds).map(([k,v])=>`<option value="${k}">${v}</option>`).join('')}</select><label for="issued">Düzenleme tarihi</label><input id="issued" type="date" value="2026-10-01" required><label for="file">Dosya</label><input id="file" type="file" accept=".txt,.pdf" required><button class="primary" type="submit">Belgeyi ekle</button></form>`;
 } else if(state.tab==='trace') {
  $('#content').innerHTML='<p class="muted">'+(state.bootstrap.mode==='demo'?'Başvuru kapsamında tamamlanan veri sorguları ve kontroller.':'İnceleme asistanının gerçekleştirdiği veri sorguları ve kontroller.')+'</p>'+(r?r.trace.map(t=>`<div class="trace"><span class="step">${t.step}</span><div><b>${escapeHtml(t.tool)}</b><p>${escapeHtml(t.purpose)}</p><span class="badge ${t.status==='ok'?'uygun':'kontrol_edilemedi'}">${escapeHtml(t.status)}</span></div></div>`).join(''):'<div class="empty">Henüz bir inceleme çalıştırılmadı.</div>');
 } else {
  $('#content').innerHTML='<div class="notice"><p>Ürün koşulları ve kontrol dayanakları.</p></div>'+state.bootstrap.policy.clauses.map(c=>`<article class="policy"><b>${escapeHtml(c.id+' · '+c.title)}</b><p>${escapeHtml(c.text)}</p><code>policy:TIC-001@1.0#${c.id}</code></article>`).join('');
 }
}
async function load(id) {
 const [report,documents]=await Promise.all([api(`/api/applications/${id}/report`),api(`/api/applications/${id}/documents`)]);
 state.id=id;sessionStorage.setItem('kredi-selected',id);state.report=report;state.documents=documents;render();
}
document.addEventListener('click',event=>{
 const remove=event.target.closest('[data-delete-document]');
 if(remove&&!state.busy){
  const id=state.id, documentId=remove.dataset.deleteDocument;
  const doc=state.documents.find(d=>d.id===documentId);
  if(doc&&window.confirm(`“${doc.name}” belgesi silinsin mi? Önceki raporlar korunur. Güncel sonuçlar için yeniden inceleme gerekir.`)){
   guarded(async()=>{await api(`/api/applications/${id}/remove-document`,{document_id:documentId});await load(id);appendMessage('Belge silindi. Güncel sonuçlar için yeniden inceleme başlatabilirsin.');});
  }
  return;
 }
 const item=event.target.closest('[data-id]');if(item&&!state.busy)guarded(()=>load(item.dataset.id));
 const tab=event.target.closest('[data-tab]');if(tab&&(!state.busy||tab.dataset.tab==='logs')){state.tab=tab.dataset.tab;render();if(state.tab==='logs')refreshLogs();}
 if(event.target.closest('#attach-financial'))guarded(async()=>{await api(`/api/applications/${state.id}/attach-financial`,{});await load(state.id);appendMessage('Mali tablo eklendi. “Tekrar incele” yazarak dosyayı güncelleyebilirsin.');});
});
$('#review').addEventListener('click',()=>guarded(async()=>{const id=state.id;await api(`/api/applications/${id}/review`,{});if(state.tab!=='logs')state.tab='findings';await load(id);}));
function appendMessage(text,user=false){const div=document.createElement('div');div.className='message'+(user?' user':'');div.textContent=text;$('#messages').append(div);$('#messages').scrollTop=$('#messages').scrollHeight;}
$('#chat-form').addEventListener('submit',event=>{event.preventDefault();const message=$('#message').value.trim();if(!message)return;$('#message').value='';appendMessage(message,true);guarded(async()=>{const result=await api('/api/chat',{session_id:sessionStorage.getItem(sessionKey),application_id:state.id,message});appendMessage(result.message);if(result.report){state.tab='findings';await load(result.report.application_id);}});});
document.addEventListener('submit',event=>{if(event.target.id!=='upload-form')return;event.preventDefault();const file=$('#file').files[0],kind=$('#kind').value,issued=$('#issued').value;if(!file)return;guarded(async()=>{if(file.size>2*1024*1024)throw new Error('Dosya en fazla 2 MB olabilir.');const data=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result.split(',')[1]);reader.onerror=()=>reject(new Error('Dosya okunamadı.'));reader.readAsDataURL(file);});await api(`/api/applications/${state.id}/upload`,{name:file.name,data,kind,issued_on:issued});await load(state.id);appendMessage('Belge eklendi. Yeniden inceleme ile raporu güncelleyebilirsin.');});});
(async()=>{try{state.bootstrap=await api('/api/bootstrap');$('#mode').textContent=state.bootstrap.mode==='demo'?'● Ön kontrol etkin':'● İnceleme asistanı etkin';$('#chat-mode').textContent='korunuyor';$('#asof').textContent=new Date(state.bootstrap.as_of+'T12:00:00').toLocaleDateString('tr-TR');await load(state.id);}catch(e){error(e.message);$('#review').disabled=true;}})();
setInterval(()=>{if(!document.hidden)refreshLogs();},2000);
