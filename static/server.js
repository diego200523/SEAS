/* Persistence adapter. Authentication, authorization, validation and final results live in Django. */
let pending=new Map(),revisions=new Map(),writeQueue=Promise.resolve(),saveTimer,lastFailure=null,configBusy=false;
const saveIndicator=(text,failed=false)=>{const el=$('#save-state');el.hidden=false;el.textContent=text;el.classList.toggle('failed',failed)};
async function api(path,method='GET',data){
  const csrf=document.cookie.split('; ').find(x=>x.startsWith('csrftoken='))?.split('=')[1]||'';
  const response=await fetch('/api/'+path,{method,credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRFToken':decodeURIComponent(csrf)},...(data===undefined?{}:{body:JSON.stringify(data)})});
  const payload=await response.json().catch(()=>({error:'El servidor no pudo procesar la solicitud.'}));
  if(!response.ok)throw new Error(payload.error||'No se pudo completar la operación.');
  return payload;
}
async function reloadState(){const state=await api('state');session=state.session;if(session){db=state;db.evaluations.forEach(e=>revisions.set(e.id,e.revision));}return state;}
function upsertEvaluation(e){const i=db.evaluations.findIndex(x=>x.id===e.id);if(i<0)db.evaluations.unshift(e);else db.evaluations[i]=e;}
function save(silent=true){
  if(!ev||ev.status==='Finalizada'||!evalAllowed(ev,true))return false;
  ev.step=step;ev.updated=new Date().toISOString();const data=clone(ev);upsertEvaluation(data);pending.set(data.id,data);
  saveIndicator('Cambios pendientes…');clearTimeout(saveTimer);
  saveTimer=setTimeout(()=>flush().catch(()=>{}),silent?450:0);return true;
}
function flush(){
  clearTimeout(saveTimer);
  const task=writeQueue.catch(()=>{}).then(async()=>{
    while(pending.size){
      const [id,data]=pending.entries().next().value;pending.delete(id);data.revision=revisions.get(id);
      saveIndicator('Guardando…');
      try{
        const saved=await api('evaluations/'+encodeURIComponent(id),'PUT',data);revisions.set(id,saved.revision);
        if(!pending.has(id)){upsertEvaluation(saved);if(ev?.id===id){ev.revision=saved.revision;ev.catalog=saved.catalog;ev.matrix=saved.matrix;ev.templates=saved.templates;}}
        lastFailure=null;
      }catch(err){if(!pending.has(id))pending.set(id,data);lastFailure=err;saveIndicator(err.message+' Use Guardar borrador para reintentar.',true);throw err;}
    }
    saveIndicator('Todos los cambios guardados');
  });writeQueue=task;return task;
}
function persist(){
  if(!allowed('admin'))return false;
  if(configBusy){toast('Espere a que termine el guardado de configuración.');return false;}
  configBusy=true;saveIndicator('Guardando configuración…');
  const data=clone(db);
  writeQueue=writeQueue.catch(()=>{}).then(async()=>{
    try{const state=await api('config','PUT',data);db=state;session=state.session;lastFailure=null;render();saveIndicator('Configuración guardada');toast('Cambios guardados en el servidor.');}
    catch(err){lastFailure=err;saveIndicator(err.message,true);toast(err.message);await reloadState();render();}
    finally{configBusy=false;}
  });return true;
}
async function loginForm(event){
  event.preventDefault();const btn=event.target.querySelector('[type=submit]');btn.disabled=true;
  try{await api('login','POST',{email:$('#email').value,password:$('#password').value});await reloadState();page='dashboard';render();}
  catch(err){error(err.message);btn.disabled=false;}
}
async function logout(){
  try{if(ev?.status!=='Finalizada')save();await flush();await api('logout','POST');session=null;ev=null;pending.clear();revisions.clear();db={users:[],catalog:[],dimensions:[],evaluations:[],matrix:clone(defaultMatrix),templates:{}};page='login';$('#save-state').hidden=true;render();}
  catch(err){toast('No se cerró la sesión: '+err.message);}
}
async function confirmFinal(){
  if(!ev||!evalAllowed(ev,true))return;
  const message=validate(ev,5);if(message){closeModal();error(message);return;}
  const id=ev.id;closeModal();save();
  try{await flush();const done=await api('evaluations/'+id+'/finalize','POST');ev=done;revisions.set(id,done.revision);upsertEvaluation(done);page='report';render();toast('Evaluación finalizada. Resultados conservados en el servidor.');}
  catch(err){error(err.message);}
}
async function duplicate(id){
  try{await flush();const copy=await api('evaluations/'+id+'/duplicate','POST');ev=copy;revisions.set(copy.id,copy.revision);upsertEvaluation(copy);step=0;page='register';render();toast('Copia creada con el catálogo actual. Califique nuevamente sus subfactores.');}
  catch(err){toast(err.message);}
}
function recover(){location.href='/accounts/password_reset/';}
function downloadPDF(){if(ev?.status==='Finalizada')location.href='/api/evaluations/'+encodeURIComponent(ev.id)+'/pdf';}
async function importCSV(file){
  if(!file||!allowed('admin'))return;
  try{const response=await api('experts','POST',{csv:await file.text()});await reloadState();render();$('#importresult').textContent=`${response.count} valoraciones guardadas; ${response.factors} factores actualizados.`;}
  catch(err){$('#importresult').textContent=err.message;}
}
function downloadCSV(){
  const f=db.catalog.find(f=>f.active);if(!f)return;
  const rows=['experto,factor_id,subfactor_id,nivel',...f.subs.filter(s=>s.active).map(s=>`Experto de ejemplo,${f.id},${s.id},3`)];
  const url=URL.createObjectURL(new Blob(['\ufeff'+rows.join('\r\n')],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='SEAS_valoraciones.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
function editUser(id){
  if(!allowed('admin'))return;
  const u=db.users.find(u=>u.id===id)||{id:uid(),name:'',email:'',role:'Decisor',active:true,organization:null};
  modal(id?'Editar usuario':'Crear usuario',`<form onsubmit="saveUser(event,'${u.id}',${!!id})"><label class="field">Nombre<input id="uname" value="${esc(u.name)}" required maxlength="150"></label><label class="field">Correo electrónico<input id="uemail" type="email" value="${esc(u.email)}" required></label><div class="formgrid"><label class="field">Rol<select id="urole">${['Administrador','Decisor','Dirección'].map(r=>`<option ${r===u.role?'selected':''}>${r}</option>`).join('')}</select></label><label class="field">Estado<select id="uactive"><option value="true" ${u.active?'selected':''}>Activo</option><option value="false" ${!u.active?'selected':''}>Inactivo</option></select></label></div><label class="field">Organización para acceso de Dirección<select id="uorg"><option value="">Sin asignar</option>${(db.organizations||[]).map(o=>`<option value="${o.id}" ${o.id===u.organization?'selected':''}>${esc(o.name)} · ${o.id}</option>`).join('')}</select><span class="help">Dirección consulta evaluaciones finalizadas. Si asigna una organización, se limita a ella.</span></label><label class="field">${id?'Nueva contraseña (opcional)':'Contraseña'}<input id="upass" type="password" minlength="10" autocomplete="new-password" ${id?'':'required'}><span class="help">Mínimo 10 caracteres. Se almacena como hash en el servidor.</span></label><div id="usererror" class="error" role="alert"></div><button class="btn" type="submit">Guardar usuario</button></form>`);
}
function saveUser(event,id,existing){
  event.preventDefault();if(!allowed('admin'))return;
  const u={id,name:$('#uname').value.trim(),email:$('#uemail').value.trim(),role:$('#urole').value,active:$('#uactive').value==='true',organization:$('#uorg').value?Number($('#uorg').value):null};
  if($('#upass').value)u.password=$('#upass').value;
  const i=db.users.findIndex(x=>x.id===id);if(i<0)db.users.push(u);else db.users[i]=u;persist();closeModal();
}
// Inform about outstanding requests instead of silently discarding edits.
window.addEventListener('beforeunload',event=>{if(pending.size||configBusy){event.preventDefault();event.returnValue='';}});
const originalExpertsHTML=expertsHTML;
expertsHTML=()=>originalExpertsHTML().replace('Para esta demostración, IE es la media de las valoraciones del factor redondeada al entero más cercano; la regla de agregación debe cotejarse con GUIOS antes de implementar el sistema. IS combina IE e IL mediante la matriz.','IE promedia primero expertos por subfactor y después subfactores del factor; redondea mitades hacia arriba. Cada subfactor activo debe tener valoraciones. IS combina IE e IL mediante la matriz.');
reloadState().then(()=>{page=session?'dashboard':'login';render();}).catch(err=>{$('#app').innerHTML='<main class="main"><h1>No se pudo cargar SEAS</h1><p>'+esc(err.message)+'</p><button class="btn" onclick="location.reload()">Reintentar</button></main>';});
