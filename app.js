(() => {
  'use strict';

  const STORAGE_KEY = 'vayoloop_demo_workspace_v1';
  const $ = id => document.getElementById(id);
  const now = () => new Date();
  const iso = date => new Date(date).toISOString();
  const esc = value => String(value ?? '').replace(/[&<>"']/g, ch => ({
    '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'
  }[ch]));
  const dateLabel = (value, withTime = true) => {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return 'Date not set';
    return date.toLocaleString([], withTime
      ? {weekday:'short', month:'short', day:'numeric', hour:'numeric', minute:'2-digit'}
      : {weekday:'short', month:'short', day:'numeric'});
  };
  const clockLabel = value => new Date(value).toLocaleTimeString([], {hour:'numeric', minute:'2-digit'});
  const startOfDay = date => {
    const d = new Date(date); d.setHours(0,0,0,0); return d;
  };
  const dateOffset = (days, hour = 9, minute = 0) => {
    const d = new Date(); d.setDate(d.getDate() + days); d.setHours(hour, minute, 0, 0); return d;
  };
  const makeId = prefix => prefix + '-' + Math.random().toString(36).slice(2,10);
  const empty = text => '<div class="empty">' + esc(text) + '</div>';

  function seedState() {
    const today = startOfDay(now());
    const steps = [2850, 3220, 3610, 3980, 4240, 4610, 4920];
    const sleeps = [7.2, 7.0, 6.9, 7.1, 6.8, 6.7, 6.5];
    const health = [];
    for (let i = 6; i >= 0; i--) {
      const day = new Date(today); day.setDate(day.getDate() - i); day.setHours(8, 0, 0, 0);
      const index = 6 - i;
      health.push({id:makeId('h'), metric:'steps', value:steps[index], unit:'steps', observedAt:iso(day), source:'Demo watch'});
      const sleepAt = new Date(day); sleepAt.setHours(8, 15);
      health.push({id:makeId('h'), metric:'sleep_hours', value:sleeps[index], unit:'hours', observedAt:iso(sleepAt), source:'Demo watch'});
    }
    health.push({id:makeId('h'),metric:'resting_heart_rate',value:72,unit:'bpm',observedAt:iso(dateOffset(-1,8,30)),source:'Demo watch'});
    health.push({id:makeId('h'),metric:'resting_heart_rate',value:74,unit:'bpm',observedAt:iso(dateOffset(0,8,30)),source:'Demo watch'});

    const meds = [
      {id:'med-a',name:'Medicine A',strength:'Sample dose A',time:'08:00',instructions:'Example note: after breakfast',active:true,lastReportedAt:null},
      {id:'med-b',name:'Medicine B',strength:'Sample dose B',time:'13:00',instructions:'Example note: lunchtime routine',active:true,lastReportedAt:null},
      {id:'med-c',name:'Medicine C',strength:'Sample dose C',time:'20:00',instructions:'Example note: evening routine',active:true,lastReportedAt:null}
    ];
    const appointments = [
      {id:'apt-a',title:'Routine wellness visit',clinician:'Dr. Example',scheduledAt:iso(dateOffset(1,11,30)),status:'scheduled',note:'Fictional sample appointment'},
      {id:'apt-b',title:'Follow-up consultation',clinician:'Community Clinic Demo',scheduledAt:iso(dateOffset(5,15,0)),status:'scheduled',note:'Bring the sample care summary'},
      {id:'apt-c',title:'Previous check-in',clinician:'Dr. Example',scheduledAt:iso(dateOffset(-4,10,0)),status:'completed',note:'Demo history'}
    ];
    const devices = [
      {id:'dev-a',name:'Asha demo watch',kind:'Smart watch',provider:'Demo wearable',status:'Simulated',lastSync:iso(dateOffset(0,8,30)),consent:true,reading:'Steps and sleep sample'},
      {id:'dev-b',name:'Hall motion sensor',kind:'Motion sensor',provider:'Demo home hub',status:'Simulated',lastSync:iso(dateOffset(0,7,50)),consent:true,reading:'Motion event sample'},
      {id:'dev-c',name:'Living room light',kind:'Smart light',provider:'Demo smart home',status:'Simulated',lastSync:null,consent:true,reading:'No live appliance control'}
    ];
    const members = [
      {id:'mem-a',name:'Asha Rao',role:'Elder',initials:'AR',scope:'Owns this demo care profile'},
      {id:'mem-b',name:'Meera Rao',role:'Family',initials:'MR',scope:'Read-only example access'},
      {id:'mem-c',name:'Arjun Patel',role:'Caregiver',initials:'AP',scope:'Example care coordination access'}
    ];
    const doseReports = [
      {id:makeId('dose'),medicationId:'med-a',at:iso(dateOffset(-5,8,5))},
      {id:makeId('dose'),medicationId:'med-b',at:iso(dateOffset(-5,13,5))},
      {id:makeId('dose'),medicationId:'med-c',at:iso(dateOffset(-4,20,5))},
      {id:makeId('dose'),medicationId:'med-a',at:iso(dateOffset(-3,8,5))},
      {id:makeId('dose'),medicationId:'med-b',at:iso(dateOffset(-2,13,5))},
      {id:makeId('dose'),medicationId:'med-a',at:iso(dateOffset(-1,8,5))}
    ];
    const events = [
      {id:makeId('ev'),title:'Morning routine reported',detail:'Medicine A · user-reported in demo',at:iso(dateOffset(0,8,5)),kind:'medication'},
      {id:makeId('ev'),title:'Demo watch sample synced',detail:'Steps and sleep sample readings',at:iso(dateOffset(0,8,30)),kind:'device'},
      {id:makeId('ev'),title:'Care circle checked in',detail:'Example shared-care activity',at:iso(dateOffset(-1,17,0)),kind:'care'}
    ];
    return {version:1,meds,health,appointments,devices,members,doseReports,events,invites:[],safetyEvents:[]};
  }

  let state;
  let memoryOnly = false;
  let previewRole = "elder";
  let tourIndex = 0;
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    state = saved ? JSON.parse(saved) : seedState();
    if (!state || state.version !== 1) state = seedState();
  } catch {
    state = seedState();
    memoryOnly = true;
  }

  function save() {
    if (memoryOnly) return;
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); }
    catch { memoryOnly = true; toast('Browser storage is unavailable. Changes will last only until this tab closes.'); }
  }

  function toast(message) {
    $('toast').textContent = message;
    $('toast').classList.remove('hidden');
    clearTimeout(toast.timer);
    toast.timer = setTimeout(() => $('toast').classList.add('hidden'), 3200);
  }

  function switchView(name) {
    document.querySelectorAll('[data-tab]').forEach(button => {
      button.classList.toggle('active', button.dataset.tab === name);
    });
    document.querySelectorAll('.view').forEach(view => {
      view.classList.toggle('active', view.id === 'view-' + name);
    });
  }

  document.querySelectorAll('[data-tab]').forEach(button => {
    button.addEventListener('click', () => switchView(button.dataset.tab));
  });
  document.querySelectorAll('[data-go]').forEach(button => {
    button.addEventListener('click', () => switchView(button.dataset.go));
  });

  function todayReports() {
    const start = startOfDay(now()).getTime();
    return state.doseReports.filter(report => new Date(report.at).getTime() >= start);
  }

  const roleTabs = {
    elder:['overview','medications','health','appointments','devices','care'],
    caregiver:['overview','medications','health','appointments','devices','care'],
    family:['overview','medications','health','appointments','care'],
    viewer:['overview']
  };
  const canEditDemo = () => previewRole === 'elder' || previewRole === 'caregiver';
  const canAdminDemo = () => previewRole === 'elder';

  function applyRoleView() {
    const allowed = roleTabs[previewRole] || roleTabs.elder;
    document.querySelectorAll('[data-tab]').forEach(button => {
      button.classList.toggle('hidden', !allowed.includes(button.dataset.tab));
    });
    const active = document.querySelector('[data-tab].active')?.dataset.tab;
    if (active && !allowed.includes(active)) switchView('overview');
    ['medForm','healthForm','apptForm','deviceForm'].forEach(id => {
      $(id).classList.toggle('hidden', !canEditDemo());
    });
    $('inviteForm').classList.toggle('hidden', !canAdminDemo());
    $('simulateSync').classList.toggle('hidden', !canEditDemo());
    $('simulateAlert').classList.toggle('hidden', !canEditDemo());
    $('rolePreview').value = previewRole;
  }

  function renderMedicationJourney() {
    const active = state.meds.filter(m => m.active);
    const recentReports = state.doseReports.filter(report => new Date(report.at) >= new Date(Date.now()-7*24*60*60*1000));
    const scheduled = active.filter(m => /^\d{2}:\d{2}$/.test(m.time)).length;
    const nextReview = state.appointments.some(item => item.status === 'scheduled' && new Date(item.scheduledAt) >= now());
    const stages = [
      {title:'Care plan recorded',count:active.length+' items',detail:'Sample medication records are stored.',done:active.length>0},
      {title:'Daily routine mapped',count:scheduled+' time slots',detail:'Each active record has a routine time.',done:scheduled>0},
      {title:'Dose reports captured',count:recentReports.length+' reports',detail:'Reports are self-entered and traceable.',done:recentReports.length>0},
      {title:'Care review planned',count:nextReview?'On calendar':'Not scheduled',detail:'A follow-up appointment gives the circle a review point.',done:nextReview}
    ];
    $('medJourney').innerHTML = stages.map((stage,index) =>
      '<div class="journey-step '+(stage.done?'':'pending')+'"><small>STEP 0'+(index+1)+'</small><strong>'+esc(stage.title)+'</strong><span class="step-count">'+esc(stage.count)+'</span><small>'+esc(stage.detail)+'</small></div>'
    ).join('');
  }

  function renderStats() {
    const weekStart = startOfDay(now());
    weekStart.setDate(weekStart.getDate() - 6);
    const reports = state.doseReports.filter(report => new Date(report.at) >= weekStart);
    const scheduled = 7;
    const rate = Math.min(100, Math.round((reports.length / scheduled) * 100));
    $('doseRate').textContent = rate + '%';
    $('medCount').textContent = state.meds.filter(m => m.active).length;
    $('memberCount').textContent = state.members.length;
    const next = state.appointments
      .filter(a => a.status === 'scheduled' && new Date(a.scheduledAt) >= now())
      .sort((a,b) => new Date(a.scheduledAt) - new Date(b.scheduledAt))[0];
    if (next) {
      $('apptCount').textContent = clockLabel(next.scheduledAt);
      $('apptNote').textContent = dateLabel(next.scheduledAt, false) + ' · sample';
    } else {
      $('apptCount').textContent = '—';
      $('apptNote').textContent = 'No upcoming demo appointments';
    }
    $('todayLabel').textContent = now().toLocaleDateString([], {weekday:'long',month:'long',day:'numeric'});
  }

  function renderMeds() {
    const active = state.meds.filter(m => m.active).sort((a,b) => a.time.localeCompare(b.time));
    const today = todayReports();
    const row = med => {
      const reportedToday = today.some(r => r.medicationId === med.id);
      return '<div class="item"><div><strong>' + esc(med.name) + ' <span class="pill neutral">' + esc(med.time) + '</span></strong>' +
        '<small>' + esc(med.strength || 'Sample label') + ' · ' + esc(med.instructions || 'No demo note') + '</small></div>' +
        '<div class="item-actions">' + (reportedToday
          ? '<span class="pill">Reported</span>'
          : '<button class="btn light small" data-dose="' + esc(med.id) + '">Mark reported</button>') +
        '</div></div>';
    };
    $('todayMeds').innerHTML = active.length ? active.map(row).join('') : empty('No active demo medication records.');
    $('medList').innerHTML = state.meds.length ? state.meds.map(med => {
      const todayReported = today.some(r => r.medicationId === med.id);
      return '<div class="item"><div><strong>' + esc(med.name) + ' <span class="pill ' + (med.active?'':'neutral') + '">' + (med.active?'Active demo record':'Archived') + '</span></strong>' +
        '<small>' + esc(med.strength || 'Sample label') + ' · ' + esc(med.time) + ' · ' + esc(med.instructions || 'No note') + '</small></div>' +
        '<div class="item-actions">' + (med.active
          ? (todayReported ? '<span class="pill">Reported today</span>' : '<button class="btn light small" data-dose="' + esc(med.id) + '">Report dose</button>') +
            '<button class="btn ghost small" data-archive="' + esc(med.id) + '">Archive</button>'
          : '<button class="btn ghost small" data-restore="' + esc(med.id) + '">Restore</button>') + '</div></div>';
    }).join('') : empty('Add a fictional medicine record to explore this screen.');
    document.querySelectorAll('[data-dose]').forEach(button => button.addEventListener('click', () => reportDose(button.dataset.dose)));
    document.querySelectorAll('[data-archive]').forEach(button => button.addEventListener('click', () => setMedicationActive(button.dataset.archive,false)));
    document.querySelectorAll('[data-restore]').forEach(button => button.addEventListener('click', () => setMedicationActive(button.dataset.restore,true)));
  }

  function reportDose(id) {
    if (todayReports().some(report => report.medicationId === id)) return toast('This demo dose was already reported today.');
    const med = state.meds.find(item => item.id === id);
    if (!med || !med.active) return;
    const at = iso(now());
    state.doseReports.push({id:makeId('dose'),medicationId:id,at});
    med.lastReportedAt = at;
    state.events.unshift({id:makeId('ev'),title:'Dose reported in demo',detail:med.name + ' · self-reported, not independently verified',at,kind:'medication'});
    save(); render(); toast('Demo dose report saved.');
  }

  function setMedicationActive(id, active) {
    const med = state.meds.find(item => item.id === id);
    if (!med) return;
    med.active = active;
    save(); render(); toast(active ? 'Demo medicine restored.' : 'Demo medicine archived.');
  }

  function renderHealth() {
    const sorted = [...state.health].sort((a,b) => new Date(b.observedAt)-new Date(a.observedAt));
    $('healthList').innerHTML = sorted.map(item =>
      '<div class="item"><div><strong>' + esc(metricName(item.metric)) + '</strong><small>' +
      dateLabel(item.observedAt) + ' · ' + esc(item.source || 'Manual demo entry') +
      '</small></div><strong>' + esc(item.value) + ' ' + esc(item.unit) + '</strong></div>'
    ).join('') || empty('No fictional health observations yet.');
    renderTrends();
  }

  function metricName(metric) {
    return ({
      steps:'Daily steps',sleep_hours:'Sleep duration',resting_heart_rate:'Resting heart rate',
      blood_pressure_systolic:'Blood pressure · systolic',blood_glucose:'Blood glucose'
    })[metric] || String(metric).replaceAll('_',' ');
  }

  function unitFor(metric) {
    return ({steps:'steps',sleep_hours:'hours',resting_heart_rate:'bpm',blood_pressure_systolic:'mmHg',blood_glucose:'sample units'})[metric] || 'units';
  }

  function latestTwo(metric) {
    return state.health.filter(item => item.metric === metric)
      .sort((a,b) => new Date(a.observedAt)-new Date(b.observedAt)).slice(-2);
  }

  function trendLabel(metric) {
    const values = latestTwo(metric);
    if (values.length < 2) return {text:'Need more entries',cls:'review',detail:'Add another dated reading to compare direction.'};
    const first = Number(values[0].value), last = Number(values[1].value);
    if (!Number.isFinite(first) || !Number.isFinite(last) || first === 0) return {text:'No comparison',cls:'review',detail:'A comparison is not available.'};
    const diff = ((last-first)/Math.abs(first))*100;
    const direction = diff > 1 ? 'Higher' : diff < -1 ? 'Lower' : 'Similar';
    return {text:direction + ' · ' + (diff > 0 ? '+' : '') + diff.toFixed(0) + '%',cls:Math.abs(diff)>12?'review':'',detail:values[0].value+' → '+values[1].value+' '+unitFor(metric)};
  }

  function renderTrends() {
    const metrics = ['steps','sleep_hours','resting_heart_rate'];
    $('trendSummary').innerHTML = metrics.map(metric => {
      const trend = trendLabel(metric);
      const latest = latestTwo(metric).at(-1);
      return '<div class="trend"><div><strong>' + (latest ? esc(latest.value)+' '+esc(latest.unit) : '—') +
        '</strong><small>' + esc(metricName(metric)) + ' · ' + esc(trend.detail) + '</small></div><span class="trend-tag ' + trend.cls + '">' + esc(trend.text) + '</span></div>';
    }).join('');
    $('trendDetail').innerHTML = metrics.map(metric => {
      const trend = trendLabel(metric);
      const latest = latestTwo(metric).at(-1);
      return '<div class="trend"><div><strong>' + (latest ? esc(latest.value)+' '+esc(latest.unit) : '—') +
        '</strong><small>' + esc(metricName(metric)) + ' · ' + esc(trend.detail) +
        '</small></div><span class="trend-tag ' + trend.cls + '">' + esc(trend.text) + '</span></div>';
    }).join('');
    const week = state.health.filter(item => item.metric === 'steps')
      .sort((a,b) => new Date(a.observedAt)-new Date(b.observedAt)).slice(-7);
    const max = Math.max(1,...week.map(item=>Number(item.value)||0));
    $('activityBars').innerHTML = week.map(item => {
      const width = Math.max(2,Math.round((Number(item.value)/max)*100));
      return '<div class="barrow"><span>' + new Date(item.observedAt).toLocaleDateString([], {weekday:'short'}) +
        '</span><div class="bartrack"><div class="barfill" style="width:' + width + '%"></div></div><strong>' +
        esc(item.value.toLocaleString ? Number(item.value).toLocaleString() : item.value) + '</strong></div>';
    }).join('') || empty('Add daily step observations to see a sample activity pattern.');
  }

  function renderAppointments() {
    const sorted = [...state.appointments].sort((a,b) => new Date(a.scheduledAt)-new Date(b.scheduledAt));
    $('apptList').innerHTML = sorted.map(item => {
      const past = new Date(item.scheduledAt) < now();
      return '<div class="item"><div><strong>' + esc(item.title) + '</strong><small>' +
        esc(item.clinician || 'Clinician not specified') + ' · ' + dateLabel(item.scheduledAt) +
        (item.note ? ' · ' + esc(item.note) : '') + '</small></div><div class="item-actions"><span class="pill ' +
        (item.status==='completed'?'neutral':past?'amber':'') + '">' + esc(item.status) + '</span>' +
        (item.status==='scheduled' ? '<button class="btn ghost small" data-complete-appt="' + esc(item.id) + '">Complete</button>' : '') +
        '</div></div>';
    }).join('') || empty('No demo appointments. Add one to see the workflow.');
    const upcoming = sorted.filter(item => item.status==='scheduled' && new Date(item.scheduledAt)>=now()).slice(0,3);
    $('nextAppts').innerHTML = upcoming.map(item =>
      '<div class="item"><div><strong>' + esc(item.title) + '</strong><small>' + dateLabel(item.scheduledAt) + '</small></div><span class="pill neutral">Planned</span></div>'
    ).join('') || empty('No upcoming sample appointments.');
    document.querySelectorAll('[data-complete-appt]').forEach(button => button.addEventListener('click', () => {
      const appointment = state.appointments.find(item=>item.id===button.dataset.completeAppt);
      if (appointment) { appointment.status='completed'; addEvent('Appointment marked complete in demo',appointment.title,'care'); save(); render(); }
    }));
  }

  function renderDevices() {
    $('deviceList').innerHTML = state.devices.map(device =>
      '<div class="item"><div><strong>' + esc(device.name) + ' <span class="pill blue">Simulated</span></strong><small>' +
      esc(device.kind) + ' · ' + esc(device.provider) + ' · ' +
      (device.lastSync ? 'Last demo sync: '+dateLabel(device.lastSync) : 'Not synced in demo') +
      '<br>' + esc(device.reading || 'No demo reading') + '</small></div>' +
      '<button class="btn ghost small" data-device-sync="' + esc(device.id) + '">Sync demo</button></div>'
    ).join('') || empty('No demo devices registered yet.');
    $('safetyLog').innerHTML = state.safetyEvents.length ? state.safetyEvents.map(event =>
      '<div class="item"><div><strong>' + esc(event.title) + '</strong><small>' + esc(event.detail) + ' · ' + dateLabel(event.at) + '</small></div><span class="pill amber">Simulated</span></div>'
    ).join('') : empty('No simulated safety events yet. Try “Run safety alert demo”.');
    document.querySelectorAll('[data-device-sync]').forEach(button => button.addEventListener('click',()=>syncDevice(button.dataset.deviceSync)));
  }

  function syncDevice(id) {
    const device = state.devices.find(item=>item.id===id);
    if (!device) return;
    device.lastSync = iso(now());
    device.reading = device.kind.toLowerCase().includes('watch')
      ? 'Steps: 5,120 · sleep: 6.5 h (sample)'
      : device.kind.toLowerCase().includes('light')
        ? 'Light state: on (simulated)'
        : 'Motion event: sample activity recorded';
    if (device.kind.toLowerCase().includes('watch')) {
      state.health.push({id:makeId('h'),metric:'steps',value:5120,unit:'steps',observedAt:device.lastSync,source:'Simulated watch sync'});
    }
    addEvent('Demo device synced',device.name+' · simulated values only','device');
    save(); render(); toast('Sample device sync complete. No real device was contacted.');
  }

  function renderCare() {
    $('membersList').innerHTML = state.members.map(member =>
      '<div class="member"><span class="member-avatar">' + esc(member.initials || member.name.slice(0,2).toUpperCase()) +
      '</span><div class="member-info"><strong>' + esc(member.name) + '</strong><small>' + esc(member.scope) +
      '</small></div><span class="pill ' + (member.role==='Elder'?'':'neutral') + '">' + esc(member.role) + '</span></div>'
    ).join('') || empty('No sample care-circle members.');
    $('inviteList').innerHTML = state.invites.length ? state.invites.map(invite =>
      '<div class="item"><div><strong>' + esc(invite.email) + '</strong><small>' + esc(invite.role) +
      ' · Expires ' + dateLabel(invite.expiresAt) + '</small></div><div class="item-actions"><span class="pill amber">Demo pending</span>' +
      '<button class="btn ghost small" data-copy-invite="' + esc(invite.id) + '">Copy code</button></div></div>'
    ).join('') : empty('No demo invitations created yet.');
    document.querySelectorAll('[data-copy-invite]').forEach(button => button.addEventListener('click', () => {
      const invite = state.invites.find(item=>item.id===button.dataset.copyInvite);
      if (!invite) return;
      copyText(invite.code);
    }));
  }

  async function copyText(value) {
    try {
      await navigator.clipboard.writeText(value);
      toast('Demo code copied. It is not a real login credential.');
    } catch {
      $('inviteResult').innerHTML = '<strong>Demo code</strong><div class="codebox">'+esc(value)+'</div><small>Select and copy this example code manually. It does not grant real access.</small>';
      $('inviteResult').classList.remove('hidden');
    }
  }

  function addEvent(title, detail, kind) {
    state.events.unshift({id:makeId('ev'),title,detail,at:iso(now()),kind});
    state.events = state.events.slice(0,30);
  }

  function renderTimeline() {
    $('timeline').innerHTML = state.events.slice(0,5).map(event =>
      '<div class="timeline-item"><span class="timeline-dot"></span><div><strong>' + esc(event.title) +
      '</strong><small>' + esc(event.detail) + ' · ' + dateLabel(event.at) + '</small></div></div>'
    ).join('') || empty('No recent demo events.');
  }

  function render() {
    renderStats();
    renderMeds();
    renderHealth();
    renderAppointments();
    renderDevices();
    renderCare();
    renderTimeline();
  }

  $('medForm').addEventListener('submit', event => {
    event.preventDefault();
    const name = $('medName').value.trim();
    const time = $('medTime').value;
    if (!name || !time) return toast('Enter a medicine label and sample time.');
    state.meds.push({
      id:makeId('med'),name,strength:$('medStrength').value.trim()||'Sample label',
      time,instructions:$('medInstructions').value.trim()||'Demo entry only',
      active:true,lastReportedAt:null
    });
    addEvent('Demo medication record added',name,'medication');
    event.target.reset(); $('medTime').value='09:00';
    save(); render(); toast('Sample medication added.');
  });

  $('healthForm').addEventListener('submit', event => {
    event.preventDefault();
    const metric = $('metric').value;
    const value = Number($('healthValue').value);
    const unit = $('healthUnit').value.trim();
    if (!Number.isFinite(value) || !unit) return toast('Enter a sample value and unit.');
    const at = iso(now());
    state.health.push({id:makeId('h'),metric,value,unit,observedAt:at,source:'Manual demo entry'});
    addEvent('Health journal sample added',metricName(metric)+' · '+value+' '+unit,'health');
    event.target.reset(); $('healthUnit').value=unitFor($('metric').value);
    save(); render(); toast('Sample observation saved.');
  });
  $('metric').addEventListener('change',()=>{$('healthUnit').value=unitFor($('metric').value);});
  $('healthUnit').value=unitFor($('metric').value);

  $('apptForm').addEventListener('submit', event => {
    event.preventDefault();
    const title = $('apptTitle').value.trim();
    const clinician = $('clinician').value.trim();
    const when = $('apptDate').value;
    if (!title || !when || new Date(when) < now()) return toast('Choose an appointment time in the future.');
    state.appointments.push({id:makeId('apt'),title,clinician,scheduledAt:iso(new Date(when)),status:'scheduled',note:'Created in demo workspace'});
    addEvent('Demo appointment added',title,'care');
    event.target.reset(); save(); render(); toast('Sample appointment added.');
  });

  $('deviceForm').addEventListener('submit', event => {
    event.preventDefault();
    if (!$('deviceConsent').checked) return toast('Confirm permission for this demo profile first.');
    const name=$('deviceName').value.trim(), kind=$('deviceKind').value, provider=$('provider').value.trim();
    if (!name || !provider) return toast('Enter a demo device name and provider.');
    state.devices.push({id:makeId('dev'),name,kind,provider,status:'Simulated',lastSync:null,consent:true,reading:'Registered in demo only'});
    addEvent('Demo device registered',name+' · simulated, not connected','device');
    event.target.reset(); save(); render(); toast('Demo device added. No real device was connected.');
  });

  $('inviteForm').addEventListener('submit', event => {
    event.preventDefault();
    const email=$('inviteEmail').value.trim().toLowerCase();
    if (!email || !email.includes('@')) return toast('Enter an example email address.');
    const bytes = new Uint8Array(8);
    if (window.crypto?.getRandomValues) crypto.getRandomValues(bytes);
    else for (let i=0;i<bytes.length;i++) bytes[i]=Math.floor(Math.random()*256);
    const code = Array.from(bytes,b=>b.toString(16).padStart(2,'0')).join('').toUpperCase();
    const hours=Number($('inviteExpiry').value);
    const invite={id:makeId('inv'),email,role:$('inviteRole').value,code,expiresAt:iso(Date.now()+hours*60*60*1000)};
    state.invites.unshift(invite);
    $('inviteResult').innerHTML='<strong>Demo invitation code · not a real access credential</strong><div class="codebox section">'+esc(code)+'</div><small>This code is only a visual example and cannot grant anyone access.</small>';
    $('inviteResult').classList.remove('hidden');
    addEvent('Demo invitation generated',email+' · '+invite.role,'care');
    event.target.reset(); save(); render(); $('inviteResult').classList.remove('hidden');
    toast('Example invitation generated.');
  });

  $('simulateSync').addEventListener('click', () => {
    const watch = state.devices.find(d=>d.kind.toLowerCase().includes('watch'));
    if (watch) syncDevice(watch.id);
    else {
      state.devices.push({id:makeId('dev'),name:'Temporary demo watch',kind:'Smart watch',provider:'VayoLoop simulator',status:'Simulated',lastSync:iso(now()),consent:true,reading:'Steps: 5,120 · sleep: 6.5 h (sample)'});
      state.health.push({id:makeId('h'),metric:'steps',value:5120,unit:'steps',observedAt:iso(now()),source:'Simulated watch sync'});
      addEvent('Demo watch sync complete','Steps and sleep example values received','device');
      save(); render(); toast('Sample watch data added. No real device was contacted.');
    }
  });

  $('simulateAlert').addEventListener('click', () => {
    const at=iso(now());
    const event={id:makeId('safety'),title:'Possible fall alert · simulated',detail:'Demo flow: verify with the elder → notify designated care-circle members → coordinate support. No real alert or call was sent.',at};
    state.safetyEvents.unshift(event);
    addEvent(event.title,'Simulation only · no emergency service contacted','safety');
    save(); render(); toast('Safety scenario simulated. No real contacts were notified.');
  });

  $('resetDemo').addEventListener('click', () => {
    if (!window.confirm('Reset all demo changes in this browser and restore the original fictional sample profile?')) return;
    state=seedState(); save(); render(); switchView('overview'); toast('Demo workspace reset.');
  });

  $('largeText').addEventListener('click', () => {
    document.body.classList.toggle('large-text');
    const enabled=document.body.classList.contains('large-text');
    $('largeText').textContent=enabled?'A− Text':'A+ Text';
    toast(enabled?'Larger text enabled.':'Standard text size restored.');
  });

  const greetHour=now().getHours();
  $('greeting').textContent=(greetHour<12?'Good morning':greetHour<17?'Good afternoon':'Good evening')+', Asha';
  if (!memoryOnly) { try { if (!localStorage.getItem(STORAGE_KEY)) save(); } catch { memoryOnly = true; } }
  render();
})();