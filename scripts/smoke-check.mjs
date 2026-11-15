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
}

assert.match(html, /DEMO MODE/, 'The public app must clearly identify itself as a demo');
assert.match(html, /Asha Rao/, 'The demo user must be visible');
assert.match(html, /fictional/i, 'The app must identify sample data as fictional');
assert.doesNotMatch(html, /id="(signIn|signUp|email|password)"/, 'The public demo must not show a login form');
assert.doesNotMatch(app, /supabase|createClient|signInWithPassword|auth\.getSession/i, 'The public demo must not call Supabase Auth');
assert.doesNotMatch(app, /fetch\s*\(/, 'The public demo must not call external APIs');
assert.ok(app.includes('localStorage'), 'Demo changes should persist locally in the browser');
assert.ok(app.includes('simulateAlert'), 'The safety-alert demo control must be implemented');
assert.ok(app.includes('simulateSync'), 'The device-sync demo control must be implemented');
assert.ok(app.includes('reportDose'), 'Medication reporting must be interactive');
assert.ok(app.includes('renderTrends'), 'Health progress trends must be rendered');
assert.match(html, /not a medical device or emergency service/i, 'Medical and emergency limitations must remain visible');
assert.match(html, /does not connect to a real smartwatch/i, 'Device simulation must not be presented as a live connection');

console.log('VayoLoop demo smoke checks passed.');
