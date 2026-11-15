import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const [html, app] = await Promise.all([
  readFile(new URL('../index.html', import.meta.url), 'utf8'),
  readFile(new URL('../app.js', import.meta.url), 'utf8')
]);

const ids = [...html.matchAll(/id="([^"]+)"/g)].map(match => match[1]);
const duplicates = ids.filter((id, index) => ids.indexOf(id) !== index);
assert.deepEqual([...new Set(duplicates)], [], 'HTML must not contain duplicate IDs');

const selectors = [...app.matchAll(/\$\('([^']+)'\)/g)].map(match => match[1]);
const missingIds = [...new Set(selectors)].filter(id => !ids.includes(id));
assert.deepEqual(missingIds, [], 'Every JavaScript element ID must exist in index.html');

const tabs = [...html.matchAll(/data-tab="([^"]+)"/g)].map(match => match[1]);
for (const tab of tabs) {
  assert.ok(html.includes('id="view-' + tab + '"'), 'Missing view for tab: ' + tab);
  assert.ok(html.includes('aria-controls="view-' + tab + '"'), 'Tab must identify its panel: ' + tab);
  assert.ok(html.includes('aria-labelledby="tab-' + tab + '"'), 'Panel must be labelled by its tab: ' + tab);
}
assert.match(html, /role="tablist"/, 'Main navigation must expose tablist semantics');
assert.match(html, /class="skip-link" href="#mainContent"/, 'Keyboard users must have a skip link');
assert.match(html, /\.sr-only\{/, 'Accessible-only labels must be visually hidden, not omitted');
assert.match(app, /event\.key === 'ArrowRight'/, 'Tabs must support right-arrow navigation');
assert.match(app, /event\.key === 'Home'/, 'Tabs must support Home-key navigation');
assert.match(app, /event\.key==='Tab'/, 'Guided tour must keep keyboard focus inside its dialog');
assert.match(app, /last\.focus\(\)/, 'Guided tour must provide a keyboard focus wrap');
assert.match(app, /view\.hidden = !active/, 'Inactive panels must be removed from keyboard focus');
const controls = [...html.matchAll(/<(?:input|select)\b[^>]*>/g)].map(match => match[0]);
for (const control of controls) {
  const id = control.match(/\bid="([^"]+)"/)?.[1];
  if (!id) continue;
  const hasExplicitLabel = html.includes('for="' + id + '"') || /\baria-label=/.test(control);
  assert.ok(hasExplicitLabel, 'Form control must have its own accessible label: ' + id);
}
assert.match(html, /id="healthValue"[^>]*min="0"/, 'Health sample values must reject negatives');
assert.match(html, /prefers-reduced-motion:reduce/, 'Reduced-motion preferences must be respected');

assert.match(html, /DEMO MODE/, 'The public app must clearly identify itself as a demo');
assert.match(html, /Asha Rao/, 'The demo user must be visible');
assert.match(html, /fictional/i, 'The app must identify sample data as fictional');
assert.doesNotMatch(html, /id="(signIn|signUp|email|password)"/, 'The public demo must not show a login form');
assert.doesNotMatch(app, /supabase|createClient|signInWithPassword|auth\.getSession/i, 'The public demo must not call Supabase Auth');
assert.doesNotMatch(app, /fetch\s*\(/, 'The public demo must not call external APIs');
assert.ok(app.includes('localStorage'), 'Demo changes should persist locally in the browser');

for (const id of ['enableVoice','readHealth','voiceCommands','stopSpeech','stopAlarm','testMissedDose','missedDoseNotice']) {
  assert.ok(ids.includes(id), 'Missing voice companion control: ' + id);
}
for (const feature of ['enableVoiceCompanion','healthBriefing','evaluateVoiceReminders','startAlarm','getMissedDoses','startVoiceCommands','SpeechSynthesisUtterance','SpeechRecognition']) {
  assert.ok(app.includes(feature), 'Missing voice-first feature: ' + feature);
}
assert.ok(app.includes('window.setInterval(evaluateVoiceReminders,15000)'), 'Voice reminders should be checked while the demo page is open');
assert.ok(app.includes('30*60*1000'), 'Missed-dose alarm should use a defined grace period');
assert.ok(app.includes('reportDose'), 'Medication reporting must be interactive');
assert.ok(app.includes('renderTrends'), 'Health progress trends must be rendered');
assert.ok(app.includes('localStorage.setItem(\'vayoloop_voice_enabled\''), 'Voice preference should persist between visits');
assert.ok(app.includes("$('greeting').textContent='Hi Asha, welcome back.'"), 'Greeting must stay short and private');
assert.ok(app.includes("speak('Hi Asha, welcome back.')"), 'Welcome should be spoken automatically');
assert.ok(app.includes("window.addEventListener('pointerdown'"), 'First normal interaction should unlock browser audio');
assert.ok(html.includes('VayoLoop visual refresh'), 'The visual refresh should be present');

for (const id of ['simulateAlert','simulateSync']) assert.ok(ids.includes(id), 'Missing connected living demo control: ' + id);
assert.match(html, /not a medical device or emergency service/i, 'Medical and emergency limitations must remain visible');
assert.match(html, /does not connect to a real smartwatch/i, 'Device simulation must not be presented as a live connection');
assert.match(app, /not a real medication alert/i, 'Spoken content must identify demo-only medication reminders');
assert.match(html, /role="dialog"/, 'The guided tour must use dialog semantics');

console.log('VayoLoop demo, voice companion, interaction and safety smoke checks passed.');
