import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

const SUPABASE_URL = 'https://vhugnytmbjktbhlspgyx.supabase.co';
const SUPABASE_KEY = 'sb_publishable_2SxGxrtA5oPY1h6oDaBUMw_DLrVbRdU';
const db = createClient(SUPABASE_URL, SUPABASE_KEY);

let user = null;
let elder = null;
let meds = [];
let health = [];
let appointments = [];
let devices = [];
let memberships = [];
let invitations = [];
let myRole = null;

const $ = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({
  '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
}[c]));
const toast = message => {
  $('toast').textContent = message;
  $('toast').classList.remove('hidden');
  window.clearTimeout(toast.timer);
  toast.timer = window.setTimeout(() => $('toast').classList.add('hidden'), 3500);
};
const show = (id, visible = true) => $(id)?.classList.toggle('hidden', !visible);
const dateText = value => value
  ? new Date(value).toLocaleString([], { dateStyle:'medium', timeStyle:'short' })
  : 'Date not set';
const errorText = error => error?.message || 'Something went wrong. Please try again.';
const empty = message => '<div class="empty">' + esc(message) + '</div>';

function setTab(tab) {
  document.querySelectorAll('[data-tab]').forEach(button => {
    button.classList.toggle('active', button.dataset.tab === tab);
  });
  ['overview','medications','health','appointments','devices','care'].forEach(name => {
    show('view-' + name, name === tab);
  });
}

document.querySelectorAll('[data-tab]').forEach(button => {
  button.addEventListener('click', () => setTab(button.dataset.tab));
});
document.querySelectorAll('[data-go]').forEach(button => {
  button.addEventListener('click', () => setTab(button.dataset.go));
});

async function enter(session) {
  user = session?.user || null;
  show('auth', !user);
  show('app', !!user);
  if (!user) {
    elder = null;
    show('profileSetup', false);
    show('dashboard', false);
    return;
  }

  try {
    const { error: profileError } = await db.from('profiles').upsert({
      user_id: user.id,
      display_name: user.email?.split('@')[0] || 'Member'
    }, { onConflict:'user_id' });
    if (profileError) throw profileError;

    const { data, error } = await db.from('elder_profiles')
      .select('*').order('created_at', { ascending:true });
    if (error) throw error;

    const profiles = data || [];
    elder = profiles.find(profile => profile.created_by === user.id) || profiles[0] || null;
    show('profileSetup', !elder);
    show('dashboard', !!elder);

    if (elder) {
      $('greeting').textContent = 'Hello, ' + elder.display_name;
      $('profileStatus').textContent = 'Care profile · ' + String(elder.preferred_language || 'en').toUpperCase();
      await refresh();
      setTab('overview');
    }
  } catch (error) {
    toast(errorText(error));
  }
}

async function refresh() {
  if (!elder) return;

  const [medResult, healthResult, appointmentResult, deviceResult, membershipResult] =
    await Promise.all([
      db.from('medications').select('*').eq('elder_id', elder.id).order('created_at', { ascending:false }),
      db.from('health_observations').select('*').eq('elder_id', elder.id).order('observed_at', { ascending:false }).limit(50),
      db.from('appointments').select('*').eq('elder_id', elder.id).order('scheduled_at', { ascending:true }),
      db.from('connected_devices').select('*').eq('elder_id', elder.id).order('created_at', { ascending:false }),
      db.from('care_memberships').select('id,user_id,role,created_at').eq('elder_id', elder.id).order('created_at', { ascending:true })
    ]);

  for (const result of [medResult, healthResult, appointmentResult, deviceResult, membershipResult]) {
    if (result.error) throw result.error;
  }

  meds = medResult.data || [];
  health = healthResult.data || [];
  appointments = appointmentResult.data || [];
  devices = deviceResult.data || [];
  memberships = membershipResult.data || [];
  myRole = memberships.find(member => member.user_id === user.id)?.role || null;

  invitations = [];
  if (myRole === 'owner' || myRole === 'elder') {
    const { data, error } = await db.from('care_invitations')
      .select('id,invited_email,role,expires_at,accepted_at,revoked_at,created_at')
      .eq('elder_id', elder.id).order('created_at', { ascending:false });
    if (error) throw error;
    invitations = data || [];
  }

  render();
}

function render() {
  const canManageCare = ['owner','elder','caregiver'].includes(myRole);
  show('medForm', canManageCare);
  show('healthForm', canManageCare);
  show('apptForm', canManageCare);
  show('deviceForm', canManageCare);
  const activeMeds = meds.filter(item => item.status === 'active');
  const upcoming = appointments.filter(item =>
    item.status === 'scheduled' && new Date(item.scheduled_at) >= new Date()
  );

  $('medCount').textContent = activeMeds.length;
  $('apptCount').textContent = upcoming.length;

  $('todayMeds').innerHTML = activeMeds.map(item => `
    <div class="item">
      <div><strong>${esc(item.name)}</strong><small>${esc(item.strength || '')} · ${esc(item.instructions || 'No instructions added')}</small></div>
      ${canManageCare ? `<button class="btn light" data-taken="${esc(item.id)}">Log taken</button>` : ''}
    </div>`).join('') || empty('No active medication records yet.');

  $('medList').innerHTML = meds.map(item => `
    <div class="item">
      <div><strong>${esc(item.name)} <span class="pill">${esc(item.status)}</span></strong><small>${esc(item.strength || '')} · ${esc(item.instructions || '')}</small></div>
      <span class="muted">${esc((item.schedule?.times || []).join(', '))}</span>
    </div>`).join('') || empty('Add a medication record to begin.');

  const healthRows = health.map(item => `
    <div class="item">
      <div><strong>${esc(String(item.metric).replaceAll('_',' '))}</strong><small>${dateText(item.observed_at)} · ${esc(item.source)}</small></div>
      <strong>${esc(item.value)} ${esc(item.unit)}</strong>
    </div>`).join('');
  $('healthList').innerHTML = healthRows || empty('No health measurements recorded yet.');
  $('recentHealth').innerHTML = health.slice(0,3).map(item => `
    <div class="item">
      <div><strong>${esc(String(item.metric).replaceAll('_',' '))}</strong><small>${dateText(item.observed_at)}</small></div>
      <strong>${esc(item.value)} ${esc(item.unit)}</strong>
    </div>`).join('') || empty('No health entries yet.');

  $('apptList').innerHTML = appointments.map(item => `
    <div class="item">
      <div><strong>${esc(item.title)}</strong><small>${esc(item.clinician_name || 'Clinician not specified')} · ${dateText(item.scheduled_at)}</small></div>
      <span class="pill">${esc(item.status)}</span>
    </div>`).join('') || empty('No appointments added yet.');
  $('nextAppts').innerHTML = upcoming.slice(0,3).map(item => `
    <div class="item"><div><strong>${esc(item.title)}</strong><small>${dateText(item.scheduled_at)}</small></div></div>
  `).join('') || empty('No upcoming appointments.');

  $('deviceList').innerHTML = devices.map(item => `
    <div class="item">
      <div><strong>${esc(item.device_name)}</strong><small>${esc(item.provider)} · ${esc(item.device_kind.replaceAll('_',' '))}</small></div>
      <span class="pill">${esc(item.connection_status)}</span>
    </div>`).join('') || empty('No devices registered. Add one with the elder’s permission.');

  renderCareCircle();

  document.querySelectorAll('[data-taken]').forEach(button => {
    button.addEventListener('click', () => logTaken(button.dataset.taken));
  });
}

function renderCareCircle() {
  $('membersList').innerHTML = memberships.map(member => {
    const canRemove = member.role !== 'owner' &&
      (member.user_id === user.id ||
       ((myRole === 'owner' || myRole === 'elder') && member.role !== 'elder'));
    const actionLabel = member.user_id === user.id ? 'Leave circle' : 'Remove access';
    return `
      <div class="item">
        <div><strong>${member.user_id === user.id ? 'You' : 'Care-circle member'}</strong>
          <small>Member ID · ${esc(member.user_id.slice(0,8))}…</small>
        </div><div class="formrow"><span class="pill">${esc(member.role)}</span>
        ${canRemove ? `<button class="btn ghost" data-remove-member="${esc(member.id)}">${actionLabel}</button>` : ''}</div>
      </div>`;
  }).join('') || empty('No care-circle members found.');

  const canInvite = myRole === 'owner' || myRole === 'elder';
  show('inviteForm', canInvite);
  $('inviteList').innerHTML = canInvite
    ? invitations.map(invitation => {
        const state = invitation.accepted_at ? 'Accepted'
          : invitation.revoked_at ? 'Revoked'
          : new Date(invitation.expires_at) <= new Date() ? 'Expired'
          : 'Pending';
        const canRevoke = state === 'Pending';
        return `<div class="item">
          <div><strong>${esc(invitation.invited_email)}</strong>
            <small>${esc(invitation.role)} · Expires ${dateText(invitation.expires_at)}</small>
          </div>
          <div class="formrow"><span class="pill">${state}</span>
          ${canRevoke ? `<button class="btn ghost" data-revoke="${esc(invitation.id)}">Revoke</button>` : ''}</div>
        </div>`;
      }).join('') || empty('No invitations yet.')
    : empty('Only the elder or profile owner can create and view invitations.');

  document.querySelectorAll('[data-revoke]').forEach(button => {
    button.addEventListener('click', () => revokeInvitation(button.dataset.revoke));
  });
  document.querySelectorAll('[data-remove-member]').forEach(button => {
    button.addEventListener('click', () => removeCareMember(button.dataset.removeMember));
  });
}

async function run(query) {
  const { error } = await query;
  if (error) throw error;
  toast('Saved successfully.');
  await refresh();
}

async function handleAcceptInvitation(code) {
  const cleanCode = String(code || '').trim().toLowerCase();
  if (!/^[0-9a-f]{64}$/.test(cleanCode)) {
    toast('Enter the complete 64-character invitation code.');
    return;
  }
  try {
    const { data, error } = await db.rpc('accept_care_invitation', { p_invite_code:cleanCode });
    if (error) throw error;
    const accepted = data?.[0];
    if (!accepted?.elder_id) throw new Error('The invitation could not be accepted.');
    const { data: profile, error: profileError } = await db.from('elder_profiles')
      .select('*').eq('id', accepted.elder_id).single();
    if (profileError) throw profileError;
    elder = profile;
    show('profileSetup', false);
    show('dashboard', true);
    $('greeting').textContent = 'Hello, ' + elder.display_name;
    $('profileStatus').textContent = 'Care profile · ' + String(elder.preferred_language || 'en').toUpperCase();
    $('inviteCode').value = '';
    if ($('inviteCodeSetup')) $('inviteCodeSetup').value = '';
    await refresh();
    setTab('care');
    toast('Invitation accepted. You are now part of this care circle.');
  } catch (error) {
    toast(errorText(error));
  }
}

async function revokeInvitation(id) {
  try {
    const { data, error } = await db.rpc('revoke_care_invitation', { p_invitation_id:id });
    if (error) throw error;
    if (!data) throw new Error('This invitation could not be revoked.');
    toast('Invitation revoked.');
    await refresh();
  } catch (error) {
    toast(errorText(error));
  }
}

async function removeCareMember(id) {
  if (!window.confirm('Remove this person’s care-circle access?')) return;
  try {
    const { data, error } = await db.rpc('remove_care_member', { p_membership_id:id });
    if (error) throw error;
    if (!data) throw new Error('Access could not be removed.');
    toast('Care-circle access updated.');
    await refresh();
  } catch (error) {
    toast(errorText(error));
  }
}

$('signIn').onclick = async () => {
  const email = $('email').value.trim();
  const password = $('password').value;
  const { error } = await db.auth.signInWithPassword({ email, password });
  if (error) toast(errorText(error));
};

$('signUp').onclick = async () => {
  if ($('password').value.length < 8) {
    toast('Use a password with at least 8 characters.');
    return;
  }
  const { error } = await db.auth.signUp({
    email:$('email').value.trim(),
    password:$('password').value
  });
  if (error) toast(errorText(error));
  else toast('Account created. Check your email if confirmation is enabled.');
};

$('signOut').onclick = async () => {
  const { error } = await db.auth.signOut();
  if (error) toast(errorText(error));
};

$('profileForm').onsubmit = async event => {
  event.preventDefault();
  try {
    const { data, error } = await db.from('elder_profiles').insert({
      created_by:user.id,
      display_name:$('elderName').value.trim(),
      preferred_language:$('language').value
    }).select().single();
    if (error) throw error;
    elder = data;
    show('profileSetup', false);
    show('dashboard', true);
    $('greeting').textContent = 'Hello, ' + elder.display_name;
    await refresh();
    toast('Care profile created.');
  } catch (error) {
    toast(errorText(error));
  }
};

$('inviteForm').onsubmit = async event => {
  event.preventDefault();
  if (!(myRole === 'owner' || myRole === 'elder')) {
    toast('Only the elder or profile owner can invite members.');
    return;
  }
  try {
    const { data, error } = await db.rpc('create_care_invitation', {
      p_elder_id:elder.id,
      p_invited_email:$('inviteEmail').value.trim(),
      p_role:$('inviteRole').value,
      p_expires_in_hours:Number($('inviteExpiry').value)
    });
    if (error) throw error;
    const invitation = data?.[0];
    if (!invitation?.invite_code) throw new Error('Invitation created but no code was returned.');
    $('inviteResult').innerHTML = `
      <strong>Invitation code — shown only once</strong>
      <code id="newInviteCode">${esc(invitation.invite_code)}</code>
      <div class="formrow section"><button id="copyInviteCode" class="btn light" type="button">Copy code</button><span class="muted">Expires ${dateText(invitation.expires_at)}</span></div>`;
    show('inviteResult', true);
    $('copyInviteCode').onclick = async () => {
      try { await navigator.clipboard.writeText(invitation.invite_code); toast('Code copied. Share it privately.'); }
      catch { toast('Copy unavailable. Select and copy the code manually.'); }
    };
    event.target.reset();
    await refresh();
  } catch (error) {
    toast(errorText(error));
  }
};

$('acceptInviteForm').onsubmit = event => {
  event.preventDefault();
  handleAcceptInvitation($('inviteCode').value);
};

$('acceptInviteSetupForm').onsubmit = event => {
  event.preventDefault();
  handleAcceptInvitation($('inviteCodeSetup').value);
};

$('medForm').onsubmit = async event => {
  event.preventDefault();
  try {
    await run(db.from('medications').insert({
      elder_id:elder.id,
      name:$('medName').value.trim(),
      strength:$('medStrength').value.trim() || null,
      instructions:$('medInstructions').value.trim() || null,
      schedule:{ times:[$('medTime').value] },
      created_by:user.id
    }));
    event.target.reset();
    $('medTime').value = '09:00';
  } catch (error) {
    toast(errorText(error));
  }
};

async function logTaken(id) {
  const medication = meds.find(item => item.id === id);
  if (!medication) return;
  try {
    await run(db.from('dose_events').insert({
      elder_id:elder.id,
      medication_id:id,
      scheduled_for:new Date().toISOString(),
      status:'taken_reported',
      reported_by:user.id,
      note:'Self-reported by a care-circle member'
    }));
  } catch (error) {
    toast(errorText(error));
  }
}

$('healthForm').onsubmit = async event => {
  event.preventDefault();
  try {
    await run(db.from('health_observations').insert({
      elder_id:elder.id,
      metric:$('metric').value,
      value:Number($('healthValue').value),
      unit:$('healthUnit').value.trim(),
      observed_at:new Date().toISOString(),
      source:$('healthSource').value,
      recorded_by:user.id
    }));
    event.target.reset();
  } catch (error) {
    toast(errorText(error));
  }
};

$('apptForm').onsubmit = async event => {
  event.preventDefault();
  try {
    await run(db.from('appointments').insert({
      elder_id:elder.id,
      title:$('apptTitle').value.trim(),
      clinician_name:$('clinician').value.trim() || null,
      scheduled_at:new Date($('apptDate').value).toISOString(),
      created_by:user.id
    }));
    event.target.reset();
  } catch (error) {
    toast(errorText(error));
  }
};

$('deviceForm').onsubmit = async event => {
  event.preventDefault();
  if (!$('deviceConsent').checked) return toast('Consent is required before registering a device.');
  try {
    await run(db.from('connected_devices').insert({
      elder_id:elder.id,
      device_name:$('deviceName').value.trim(),
      device_kind:$('deviceKind').value,
      provider:$('provider').value.trim(),
      connection_status:'pending',
      consent_granted_by:user.id,
      capabilities:[]
    }));
    event.target.reset();
  } catch (error) {
    toast(errorText(error));
  }
};

db.auth.onAuthStateChange((_event, session) => {
  queueMicrotask(() => enter(session));
});
const { data:{ session } } = await db.auth.getSession();
await enter(session);
