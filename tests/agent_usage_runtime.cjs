const fs = require('fs');
const vm = require('vm');
const assert = require('assert');

// Load the real functions out of the QML service and run them with mocked globals.
function functions(path, names) {
    const source = fs.readFileSync(path, 'utf8');
    return names.map(name => {
        const match = source.match(new RegExp('    function ' + name + '\\(([^)]*)\\)(?::[^\\{]+)? \\{([\\s\\S]*?)\\n    \\}'));
        assert(match, `Missing ${name} in ${path}`);
        return `function ${name}(${match[1].replace(/:\s*\w+/g, '')}) {${match[2]}\n}`;
    }).join('\n');
}

// QML strings have .arg(); a String object with one stands in for them.
const text = value => Object.assign(new String(value), {arg(replacement) { return text(this.replace('%1', replacement)); }});
const palette = {m3error: 'error', m3tertiary: 'tertiary', m3primary: 'primary'};
const ctx = vm.createContext({Tr: {tr: text}, Colours: {palette}});
vm.runInContext(functions('shell/services/AgentUsage.qml',
    ['generalLimits', 'primaryPercent', 'tone', 'formatTokens', 'formatReset', 'formatAge']), ctx);
const run = expression => vm.runInContext(expression, ctx);

// Token counts.
for (const [count, shown] of [[0, '0'], [999, '999'], [1500, '1.5k'], [12000, '12k'], [2.5e6, '2.5M'], [3e9, '3.0B']])
    assert.equal(run(`formatTokens(${count})`), shown);

// Reset countdowns, from a fixed "now".
const now = new Date('2026-10-28T12:00:00Z');
ctx.now = now;
const after = minutes => `"${new Date(now.getTime() + minutes * 60000).toISOString()}"`;
assert.equal(run(`formatReset(${after(12)}, now)`), '12m');
assert.equal(run(`formatReset(${after(134)}, now)`), '2h 14m');
assert.equal(run(`formatReset(${after(3 * 1440 + 4 * 60)}, now)`), '3d 4h');
assert.equal(String(run(`formatReset(${after(-5)}, now)`)), 'now');
assert.equal(run('formatReset("", now)'), '');
assert.equal(run('formatReset("not a time", now)'), '');

// How long ago the numbers were taken.
const ago = minutes => now.getTime() - minutes * 60000;
assert.equal(run('formatAge(0, now)'), '');
assert.equal(String(run(`formatAge(${ago(0.2)}, now)`)), 'just now');
assert.equal(String(run(`formatAge(${ago(5)}, now)`)), '5 min ago');
assert.equal(String(run(`formatAge(${ago(180)}, now)`)), '3 h ago');

// The bar's figure is the busiest account-wide window; a model's own allowance never counts.
ctx.agent = {limits: [{percent: 0.2}, {percent: 0.55}, {percent: 0.99, scoped: true}]};
assert.equal(run('primaryPercent(agent)'), 0.55);
assert.equal(run('primaryPercent({limits: [{percent: 0.9, scoped: true}]})'), -1);
assert.equal(run('primaryPercent({limits: []})'), -1);
assert.equal(run('primaryPercent(null)'), -1);

// Quiet, warm, urgent.
assert.equal(run('tone(0.2)'), 'primary');
assert.equal(run('tone(0.75)'), 'tertiary');
assert.equal(run('tone(0.9)'), 'error');
assert.equal(run('tone(1)'), 'error');
console.log('agent usage runtime checks passed');
