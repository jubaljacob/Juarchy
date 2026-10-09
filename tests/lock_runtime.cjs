const fs = require('fs');
const vm = require('vm');
const assert = require('assert');

// Run the lock's actual handlers against a fake PAM service; never authenticate.
const source = fs.readFileSync('shell/modules/lock/Pam.qml', 'utf8');
const handler = source.match(/function handleKey\(event: KeyEvent\): void \{([\s\S]*?)\n    \}/)[1];
const completion = source.match(/onCompleted: res => \{([\s\S]*?)\n        \}/)[1];
const cooldown = source.match(/id: pwdStateReset[\s\S]*?onTriggered: \{([\s\S]*?)\n        \}/)[1];
const activation = source.match(/onActiveChanged: \{([\s\S]*?)\n        \}/)[1];
const Pam = {None: 0, Error: 1, MaxTries: 2, Failed: 3};
const PamResult = {Success: 0, Error: 1, MaxTries: 2, Failed: 3};
let starts = 0, unlocks = 0, resets = 0;
const root = {
    state: Pam.None, buffer: '', lockMessage: '',
    lock: {unlock: () => unlocks++},
    clearTransientState() {}, flashMsg() {}
};
const ctx = vm.createContext({
    root, Pam, PamResult,
    passwd: {active: false, start: () => starts++},
    howdy: {canAttempt: false, active: false},
    pwdStateReset: {restart: () => resets++},
    Qt: {Key_Enter: 1, Key_Return: 2, Key_Backspace: 3, ControlModifier: 4}
});
vm.runInContext(`function handleKey(event) { with (root) {${handler}} }
function complete(res) {${completion}}
function cooldown() {${cooldown}}
function activate(active) {${activation}}`, ctx);

// All unsuccessful outcomes leave the session locked. The UI cooldown also
// recovers from MaxTries, so a later keyboard retry reaches PAM again.
for (const result of [PamResult.Failed, PamResult.Error, PamResult.MaxTries]) {
    ctx.complete(result);
    assert.notEqual(root.state, Pam.None);
    assert.equal(unlocks, 0);
    ctx.cooldown();
    assert.equal(root.state, Pam.None);
    root.buffer = '';
    ctx.handleKey({key: 99, text: 'x', modifiers: 0});
    assert.equal(root.buffer, 'x');
    const previousStarts = starts;
    ctx.handleKey({key: 2, text: '', modifiers: 0});
    assert.equal(starts, previousStarts + 1);
    assert.equal(unlocks, 0);
}
assert.equal(resets, 3);

// Input remains blocked during authentication and during the message cooldown.
root.state = Pam.MaxTries;
root.buffer = '';
ctx.handleKey({key: 99, text: 'x', modifiers: 0});
assert.equal(root.buffer, '');
ctx.cooldown();
ctx.passwd.active = true;
const previousStarts = starts;
ctx.handleKey({key: 2, text: '', modifiers: 0});
assert.equal(starts, previousStarts);
root.lockMessage = 'Previous lockout';
ctx.activate(true);
assert.equal(root.lockMessage, '');
ctx.complete(PamResult.Success);
assert.equal(unlocks, 1);
console.log('Lock retry recovery and PAM-only unlock checks passed.');
