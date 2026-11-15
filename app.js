import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

const SUPABASE_URL = 'https://vhugnytmbjktbhlspgyx.supabase.co';
const SUPABASE_KEY = 'sb_publishable_2SxGxrtA5oPY1h6oDaBUMw_DLrVbRdU';
const db = createClient(SUPABASE_URL, SUPABASE_KEY);
let user = null, elder = null, meds = [], health = [], appointments = [], devices = [];
const $ = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const toast = msg => { $('toast').textContent = msg; $('toast').classList.remove('hidden'); setTimeout(()=>$('toast').classList.add('hidden'),3200); };
const show = (id, yes=true) => $(id).classList.toggle('hidden',!yes);
const dateText = value => value ? new Date(value).toLocaleString([], {dateStyle:'medium',timeStyle:'short'}) : 'Date not set';
const errorText = e => e?.message || 'Something went wrong. Please try again.';
function setTab(tab){
 document.querySelectorAll('[data-tab]').forEach(b=>b.classList.toggle('active',b.dataset.tab===tab));
 ['overview','medications','health','appointments','devices'].forEach(t=>show('view-'+t,t===tab));
}
document.querySelectorAll('[data-tab]').forEach(b=>b.addEventListener('click',()=>setTab(b.dataset.tab)));
document.querySelectorAll('[data-go]').forEach(b=>b.addEventListener('click',()=>setTab(b.dataset.go)));

async function enter(session){
 user=session?.user||null;
 show('auth',!user); show('app',!!user);
 if(!user)return;
 $('greeting').textContent='Welcome back';
 try{
  await db.from('profiles').upsert({user_id:user.id,display_name:user.user_metadata?.display_name||user.email?.split('@')[0]||'Member'},{onConflict:'user_id'});
  const {data,error}=await db.from('elder_profiles').select('*').order('created_at',{ascending:true}).limit(1);
  if(error)throw error;
  elder=data?.[0]||null;
  show('profileSetup',!elder); show('dashboard',!!elder);
  if(elder){$('greeting').textContent='Hello, '+elder.display_name;$('profileStatus').textContent='Care profile · '+elder.preferred_language.toUpperCase();await refresh();}
 }catch(e){toast(errorText(e));}
}
async function refresh(){
 const [m,h,a,d]=await Promise.all([
  db.from('medications').select('*').eq('elder_id',elder.id).order('created_at',{ascending:false}),
  db.from('health_observations').select('*').eq('elder_id',elder.id).order('observed_at',{ascending:false}).limit(50),
  db.from('appointments').select('*').eq('elder_id',elder.id).order('scheduled_at',{ascending:true}),
  db.from('connected_devices').select('*').eq('elder_id',elder.id).order('created_at',{ascending:false})
 ]);
 for(const r of [m,h,a,d])if(r.error)throw r.error;
 meds=m.data||[];health=h.data||[];appointments=a.data||[];devices=d.data||[];
 render();
}
function empty(msg){return '<div class="empty">'+esc(msg)+'</div>'}
function render(){
 const active=meds.filter(x=>x.status==='active');
 $('medCount').textContent=active.length;$('apptCount').textContent=appointments.filter(x=>x.status==='scheduled'&&new Date(x.scheduled_at)>=new Date()).length;
 const medHtml=active.map(x=>'<div class="item"><div><strong>'+esc(x.name)+'</strong><small>'+esc(x.strength||'')+' · '+esc(x.instructions||'No instructions added')+'</small></div><button class="btn light" data-taken="'+x.id+'">Log taken</button></div>').join('');
 $('todayMeds').innerHTML=medHtml||empty('No active medication records yet.');
 $('medList').innerHTML=meds.map(x=>'<div class="item"><div><strong>'+esc(x.name)+' <span class="pill">'+esc(x.status)+'</span></strong><small>'+esc(x.strength||'')+' · '+esc(x.instructions||'')+'</small></div><span class="muted">'+esc((x.schedule?.times||[]).join(', '))+'</span></div>').join('')||empty('Add a medication record to begin.');
 const healthHtml=health.map(x=>'<div class="item"><div><strong>'+esc(x.metric.replaceAll('_',' '))+'</strong><small>'+dateText(x.observed_at)+' · '+esc(x.source)+'</small></div><strong>'+esc(x.value)+' '+esc(x.unit)+'</strong></div>').join('');
 $('healthList').innerHTML=healthHtml||empty('No health measurements recorded yet.');
 $('recentHealth').innerHTML=health.slice(0,3).map(x=>'<div class="item"><div><strong>'+esc(x.metric.replaceAll('_',' '))+'</strong><small>'+dateText(x.observed_at)+'</small></div><strong>'+esc(x.value)+' '+esc(x.unit)+'</strong></div>').join('')||empty('No health entries yet.');
 const upcoming=appointments.filter(x=>x.status==='scheduled'&&new Date(x.scheduled_at)>=new Date());
 $('apptList').innerHTML=appointments.map(x=>'<div class="item"><div><strong>'+esc(x.title)+'</strong><small>'+esc(x.clinician_name||'Clinician not specified')+' · '+dateText(x.scheduled_at)+'</small></div><span class="pill">'+esc(x.status)+'</span></div>').join('')||empty('No appointments added yet.');
 $('nextAppts').innerHTML=upcoming.slice(0,3).map(x=>'<div class="item"><div><strong>'+esc(x.title)+'</strong><small>'+dateText(x.scheduled_at)+'</small></div></div>').join('')||empty('No upcoming appointments.');
 $('deviceList').innerHTML=devices.map(x=>'<div class="item"><div><strong>'+esc(x.device_name)+'</strong><small>'+esc(x.provider)+' · '+esc(x.device_kind.replaceAll('_',' '))+'</small></div><span class="pill">'+esc(x.connection_status)+'</span></div>').join('')||empty('No devices registered. Add one with the elder’s permission.');
 document.querySelectorAll('[data-taken]').forEach(b=>b.addEventListener('click',()=>logTaken(b.dataset.taken)));
}
async function run(promise){const {error}=await promise;if(error)throw error;toast('Saved successfully.');await refresh();}
$('signIn').onclick=async()=>{const {error}=await db.auth.signInWithPassword({email:$('email').value.trim(),password:$('password').value});if(error)toast(errorText(error));};
$('signUp').onclick=async()=>{if($('password').value.length<8)return toast('Use a password with at least 8 characters.');const {error}=await db.auth.signUp({email:$('email').value.trim(),password:$('password').value});if(error)toast(errorText(error));else toast('Account created. Check your email if confirmation is enabled.');};
$('signOut').onclick=async()=>{await db.auth.signOut();};
$('profileForm').onsubmit=async e=>{e.preventDefault();try{const {data,error}=await db.from('elder_profiles').insert({created_by:user.id,display_name:$('elderName').value.trim(),preferred_language:$('language').value}).select().single();if(error)throw error;elder=data;show('profileSetup',false);show('dashboard',true);$('greeting').textContent='Hello, '+elder.display_name;await refresh();toast('Care profile created.');}catch(err){toast(errorText(err));}};
$('medForm').onsubmit=async e=>{e.preventDefault();try{await run(db.from('medications').insert({elder_id:elder.id,name:$('medName').value.trim(),strength:$('medStrength').value.trim()||null,instructions:$('medInstructions').value.trim()||null,schedule:{times:[$('medTime').value]},created_by:user.id}));e.target.reset();$('medTime').value='09:00';}catch(err){toast(errorText(err));}};
async function logTaken(id){try{const med=meds.find(x=>x.id===id);if(!med)return;await run(db.from('dose_events').insert({elder_id:elder.id,medication_id:id,scheduled_for:new Date().toISOString(),status:'taken_reported',reported_by:user.id,note:'Reported by user'}));}catch(e){toast(errorText(e));}}
$('healthForm').onsubmit=async e=>{e.preventDefault();try{await run(db.from('health_observations').insert({elder_id:elder.id,metric:$('metric').value,value:Number($('healthValue').value),unit:$('healthUnit').value.trim(),observed_at:new Date().toISOString(),source:$('healthSource').value,recorded_by:user.id}));e.target.reset();}catch(err){toast(errorText(err));}};
$('apptForm').onsubmit=async e=>{e.preventDefault();try{await run(db.from('appointments').insert({elder_id:elder.id,title:$('apptTitle').value.trim(),clinician_name:$('clinician').value.trim()||null,scheduled_at:new Date($('apptDate').value).toISOString(),created_by:user.id}));e.target.reset();}catch(err){toast(errorText(err));}};
$('deviceForm').onsubmit=async e=>{e.preventDefault();if(!$('deviceConsent').checked)return toast('Consent is required before registering a device.');try{await run(db.from('connected_devices').insert({elder_id:elder.id,device_name:$('deviceName').value.trim(),device_kind:$('deviceKind').value,provider:$('provider').value.trim(),connection_status:'pending',consent_granted_by:user.id,capabilities:[]}));e.target.reset();}catch(err){toast(errorText(err));}};
db.auth.onAuthStateChange((_event,session)=>{enter(session);});
const {data:{session}}=await db.auth.getSession();await enter(session);
