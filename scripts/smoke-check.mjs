import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const [html, app] = await Promise.all([
  readFile(new URL('../index.html', import.meta.url), 'utf8'),
  readFile(new URL('../app.js', import.meta.url), 'utf8')
]);

const ids = [...html.matchAll(/\\bid="([^"]+)"/g)].map(match => match[1]);
const duplicates = ids.filter((id, index) => ids.indexOf(id) !== index);
assert.deepEqual([...new Set(duplicates)], [], 'HTML must not contain duplicate IDs');

const selectors = [...app.matchAll(/\\$\\('([^']+)'\\)/g)].map(match => match[1]);
const dynamicIds = new Set(['copyInviteCode']);
const missingIds = [...new Set(selectors)].filter(id => !ids.includes(id) && !dynamicIds.has(id));
assert.deepEqual(missingIds, [], 'Every static JavaScript ID reference must exist in index.html');
assert.ok(app.includes('id="copyInviteCode"'), 'The copy button ID must be created by the invitation-code template');

const tabs = [...html.matchAll(/data-tab="([^"]+)"/g)].map(match => match[1]);
for (const tab of tabs) assert.ok(html.includes(`id="view-${tab}"`), `Missing view for tab: ${tab}`);

for (const feature of ['create_care_invitation','accept_care_invitation','revoke_care_invitation','remove_care_member']) {
  assert.ok(app.includes(feature), `Missing care-circle integration: ${feature}`);
}
assert.ok(app.includes('sb_publishable_'), 'Frontend should use a publishable Supabase key');
assert.doesNotMatch(app, /sb_secret_|service_role/i, 'Secret/service-role keys must never be shipped to the browser');
assert.ok(html.includes('not an emergency service'), 'Emergency-service limitation must remain visible');
assert.ok(html.includes('Device connections are not active yet'), 'Unimplemented integrations must not be presented as live');

console.log('VayoLoop smoke checks passed.');
