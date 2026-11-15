import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const [html, app, streamlit, architecture, readme, sampleCsv] = await Promise.all([
  readFile(new URL('../index.html', import.meta.url), 'utf8'),
  readFile(new URL('../app.js', import.meta.url), 'utf8'),
  readFile(new URL('../app.py', import.meta.url), 'utf8'),
  readFile(new URL('../ARCHITECTURE.md', import.meta.url), 'utf8'),
  readFile(new URL('../README.md', import.meta.url), 'utf8'),
  readFile(new URL('../examples/vayoloop_wearable_demo.csv', import.meta.url), 'utf8')
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
assert.match(html, /Content-Security-Policy/, 'Static preview must declare a restrictive content security policy');
assert.match(html, /strict-origin-when-cross-origin/, 'External navigation must use a conservative referrer policy');
assert.doesNotMatch(html, /<script[^>]+src="https?:\/\//i, 'No third-party script source should be loaded');

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

function relativeLuminance(hex) {
  const value = hex.replace('#', '');
  const channels = [0, 2, 4].map((offset) => parseInt(value.slice(offset, offset + 2), 16) / 255);
  const linear = channels.map((channel) => (
    channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4
  ));
  return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2];
}
function contrastRatio(foreground, background) {
  const values = [relativeLuminance(foreground), relativeLuminance(background)].sort((a, b) => b - a);
  return (values[0] + 0.05) / (values[1] + 0.05);
}
assert.match(html, /--muted:#5f6d64/, 'Static preview body copy must use the accessible muted token');
assert.match(html, /--amber:#79531e/, 'Static preview warning text must use the accessible amber token');
assert.match(html, /color:#65756b/, 'Static preview placeholders must remain legible');
assert.match(streamlit, /--vl-muted:#5f6d64/, 'Streamlit copy must use the accessible muted token');
assert.ok(streamlit.includes('[data-testid="stMetricLabel"] { color:#5f6d64;'), 'Streamlit metric labels must use accessible contrast');
assert.ok(streamlit.includes('.vl-small { color:#5f6d64;'), 'Streamlit small text must use accessible contrast');
assert.ok(contrastRatio('#5f6d64', '#fffefa') >= 4.5, 'Muted text on white cards must meet WCAG AA normal-text contrast');
assert.ok(contrastRatio('#5f6d64', '#f5f2e9') >= 4.5, 'Muted text on paper background must meet WCAG AA normal-text contrast');
assert.ok(contrastRatio('#65756b', '#fbfcfb') >= 4.5, 'Input placeholders must meet WCAG AA normal-text contrast');
assert.ok(contrastRatio('#79531e', '#f8f0df') >= 4.5, 'Warning labels must meet WCAG AA normal-text contrast');
assert.match(streamlit, /id="voiceStatus" role="status" aria-live="polite"/, 'Voice status updates must be announced to assistive technology');
console.log('VayoLoop demo, voice companion, interaction, safety and accessibility smoke checks passed.');


assert.match(streamlit, /Import a wearable \/ health-app export/, 'The Health Journal must expose the wearable CSV import');
assert.match(streamlit, /parse_health_observations_csv/, 'The Streamlit UI must call the validated wearable CSV parser');
assert.match(streamlit, /save_health_observations/, 'Wearable readings must be persisted with the validated batch-save function');

assert.match(architecture, /## Architecture and trust boundaries/, 'Architecture must explain component and trust boundaries');
assert.match(architecture, /### Component and responsibility map/, 'Architecture must show module responsibilities');
assert.match(architecture, /### Wearable \/ health-app CSV import data flow/, 'Architecture must describe the wearable CSV pipeline');
assert.match(architecture, /### Data ownership and persistence boundary/, 'Architecture must distinguish persistent and session data');
assert.match(architecture, /### Security and failure boundaries/, 'Architecture must document validation and failure boundaries');
assert.match(architecture, /Public-demo consequence/, 'Architecture must disclose shared public demo data visibility');
assert.match(architecture, /not a Bluetooth\/vendor-cloud integration/, 'Architecture must distinguish CSV file import from live device integration');
const currentSamplePath = 'examples/vayoloop_wearable_demo.csv';
const retiredSamplePath = 'examples/wearable_export_sample.csv';
assert.ok(architecture.includes(currentSamplePath), 'Architecture must identify the current reproducible sample input');
assert.ok(readme.includes(currentSamplePath), 'README must identify the current reproducible sample input');
assert.ok(!architecture.includes(retiredSamplePath) && !readme.includes(retiredSamplePath), 'Documentation must not link to the retired sample input');
assert.ok(sampleCsv.startsWith('metric,value,unit,observed_at,source'), 'The committed sample must use the parser header contract');
assert.equal(sampleCsv.trimEnd().split(String.fromCharCode(10)).length, 8, 'The committed sample must contain seven data rows plus its header');
