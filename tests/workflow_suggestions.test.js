const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

const root = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'workflow.html'), 'utf8');
const dataMatch = html.match(/<script id="workflow-data" type="application\/json">([\s\S]*?)<\/script>/);
const appMatch = html.match(/<script>\s*('use strict';[\s\S]*?)<\/script>\s*<\/body>/);
assert.ok(dataMatch, 'workflow data script is present');
assert.ok(appMatch, 'workflow application script is present');

const documentStub = {
  getElementById(id) {
    if (id === 'workflow-data') return { textContent: dataMatch[1] };
    return null;
  },
  querySelector() { return null; },
  querySelectorAll() { return []; },
};
const storage = new Map();
const context = {
  console,
  document: documentStub,
  localStorage: {
    getItem(key) { return storage.has(key) ? storage.get(key) : null; },
    setItem(key, value) { storage.set(key, value); },
    removeItem(key) { storage.delete(key); },
  },
  structuredClone,
  CSS: { escape: value => String(value) },
  Blob: class {},
  URL: { createObjectURL() { return 'blob:test'; }, revokeObjectURL() {} },
  setTimeout() { return 1; },
  clearTimeout() {},
};
vm.createContext(context);
const applicationScript = appMatch[1].replace(/\ninit\(\);\s*$/, '\n');
vm.runInContext(`${applicationScript}\n
globalThis.__testApi = {
  reset(answers = {}) { state = {...structuredClone(DEFAULT_STATE), answers: normalizeAnswers(answers)}; applyDefaults(); },
  suggest(stepIndex) { return buildLuckySuggestions(STEPS[stepIndex]); },
  apply(stepIndex) { const patch = buildLuckySuggestions(STEPS[stepIndex]); state.answers = {...state.answers, ...patch}; return patch; },
  issueCount() { return allIssues().length; },
  validatePatch(stepIndex, patch) {
    const previous = state.answers;
    state.answers = {...previous, ...patch};
    const valid = STEPS[stepIndex].fields
      .filter(field => Object.prototype.hasOwnProperty.call(patch, field.id))
      .every(field => fieldValueValid(field, patch[field.id]));
    state.answers = previous;
    return valid;
  },
};`, context);
const api = context.__testApi;

assert.match(html, /id="luckyBtn"/, 'the current step exposes an I’m Feeling Lucky button');
assert.match(html, /@media\(max-width:780px\)[\s\S]*?\.top-actions\{order:2;width:100%;margin-left:0/, 'mobile top actions wrap into a full-width row');
assert.match(html, /I(?:’|')m Feeling Lucky/, 'the action has an explicit accessible label');

api.reset();
const starter = api.suggest(0);
for (const id of ['repoMode', 'repoTarget', 'baselineEvidence', 'title', 'pitch', 'genre', 'audience', 'platforms', 'sessionLength', 'deliveryScope', 'nonGoals']) {
  assert.ok(Object.prototype.hasOwnProperty.call(starter, id), `greenfield starter suggests ${id}`);
}
assert.equal(api.validatePatch(0, starter), true, 'greenfield starter values satisfy the workflow schema');

api.reset({repoMode: 'Implement in an existing repository', repoTarget: 'C:\\games\\existing-project', title: 'Existing Game'});
const existingRepo = api.suggest(0);
assert.equal(Object.prototype.hasOwnProperty.call(existingRepo, 'repoMode'), false, 'existing workspace choice is preserved');
assert.equal(Object.prototype.hasOwnProperty.call(existingRepo, 'repoTarget'), false, 'existing repository target is preserved');
assert.match(existingRepo.baselineEvidence, /inspect/i, 'existing-repository suggestion requests baseline inspection');
assert.doesNotMatch(existingRepo.baselineEvidence, /greenfield/i, 'existing repository is never described as greenfield');

api.reset({
  title: 'Sky Salvage',
  genre: 'arcade flight combat',
  pitch: 'Pilot a salvage skiff through dangerous cloud ruins.',
  platforms: ['Desktop web'],
  sessionLength: '5–15 minutes',
});
const vision = api.suggest(0);
assert.equal(Object.prototype.hasOwnProperty.call(vision, 'title'), false, 'existing title is never overwritten');
assert.equal(Object.prototype.hasOwnProperty.call(vision, 'genre'), false, 'existing genre is never overwritten');
const bar = api.suggest(1);
assert.match(bar.barSentence, /Sky Salvage/, 'later suggestions use the working title from a previous screen');
assert.equal(api.validatePatch(1, bar), true, 'quality-bar suggestions satisfy the workflow schema');

const desktopExperience = api.suggest(2);
assert.equal(Object.prototype.hasOwnProperty.call(desktopExperience, 'touchControls'), false, 'touch controls are not suggested for desktop-only games');
assert.equal(api.validatePatch(2, desktopExperience), true, 'desktop experience suggestions satisfy the workflow schema');

api.reset({
  title: 'Pocket Salvage',
  genre: 'arcade action',
  pitch: 'Recover relics during compact action runs.',
  platforms: ['Mobile web'],
  sessionLength: '2–5 minutes',
});
const mobileExperience = api.suggest(2);
assert.equal(typeof mobileExperience.touchControls, 'string', 'touch controls are suggested when mobile is targeted');
assert.ok(mobileExperience.touchControls.length > 20, 'touch suggestion is implementation-useful');
assert.equal(api.validatePatch(2, mobileExperience), true, 'mobile experience suggestions satisfy the workflow schema');

api.reset({
  title: 'Sky Salvage',
  genre: 'arcade flight combat',
  pitch: 'Pilot a salvage skiff through dangerous cloud ruins.',
  platforms: ['Desktop web'],
  sessionLength: '5–15 minutes',
});
const systems = api.suggest(5);
assert.ok(systems.systems.includes('Combat'), 'action context produces a relevant combat-system suggestion');
assert.equal(typeof systems.combatContract, 'string', 'conditional combat contract is suggested with combat');
assert.equal(api.validatePatch(5, systems), true, 'systems suggestions satisfy the workflow schema');

api.reset({
  title: 'Quiet Circuit',
  genre: 'spatial puzzle',
  pitch: 'Solve signal puzzles between tactical encounters.',
  systems: ['Combat'],
});
const canonicalCombat = api.suggest(5);
assert.equal(Object.prototype.hasOwnProperty.call(canonicalCombat, 'systems'), false, 'an existing systems selection is never replaced');
assert.equal(typeof canonicalCombat.combatContract, 'string', 'contracts follow an existing canonical combat selection even for a puzzle genre');
assert.equal(api.validatePatch(5, canonicalCombat), true, 'canonical combat contract satisfies the workflow schema');

api.reset({
  title: 'Talkative Ruins',
  genre: 'action adventure',
  pitch: 'Resolve a dangerous expedition through conversation.',
  systems: ['Dialogue'],
});
const canonicalDialogue = api.suggest(5);
assert.equal(Object.prototype.hasOwnProperty.call(canonicalDialogue, 'combatContract'), false, 'genre inference cannot add a contract for an unselected combat system');
assert.equal(Object.prototype.hasOwnProperty.call(canonicalDialogue, 'aiContract'), false, 'genre inference cannot add a contract for unselected enemy AI');

api.reset({
  title: 'Relay Crew',
  genre: 'cooperative puzzle',
  pitch: 'Coordinate signal routing with a remote partner.',
  systems: ['Online multiplayer'],
});
const canonicalOnline = api.suggest(5);
const onlineTechnical = api.suggest(7);
assert.equal(typeof canonicalOnline.multiplayerContract, 'string', 'canonical online selection receives its required multiplayer contract');
assert.equal(onlineTechnical.networking, 'Authoritative online multiplayer', 'technical suggestions honor canonical online-system selection');
assert.equal(api.validatePatch(5, canonicalOnline), true, 'canonical online contract satisfies the workflow schema');
assert.equal(api.validatePatch(7, onlineTechnical), true, 'online technical suggestion satisfies the workflow schema');

api.reset();
for (let stepIndex = 0; stepIndex < 12; stepIndex += 1) {
  const patch = api.apply(stepIndex);
  assert.equal(api.validatePatch(stepIndex, patch), true, `stage ${stepIndex + 1} suggestions satisfy the workflow schema`);
}
assert.equal(api.issueCount(), 0, 'applying suggestions across all stages produces an export-ready canonical state');

console.log('workflow contextual suggestions: PASS');
