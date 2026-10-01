// Run against `python app.py 8765` with: node tests/frontend_smoke.cjs
// Uses a minimal DOM stub to check rendering/data integration, not visual layout.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const base = process.env.APRIORI_TEST_URL || 'http://127.0.0.1:8765';
const elements = new Map();
const document = {
  getElementById(id) {
    if (!elements.has(id)) elements.set(id, {
      value: '', innerHTML: '', textContent: '',
      classList: {add() {}, remove() {}},
      addEventListener() {}, querySelectorAll() {return [];}, scrollIntoView() {},
    });
    return elements.get(id);
  },
  addEventListener() {},
};
const context = vm.createContext({
  document, window: {innerWidth: 1200}, console,
  fetch: (url, options) => fetch(new URL(url, base), options),
});
const html = fs.readFileSync(path.join(__dirname, '../src/web/index.html'), 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];

(async () => {
  await vm.runInContext(script, context);
  assert.equal(vm.runInContext('state.R.N', context), 10);
  for (const id of ['han', 'abcd', 'grocery', 'breakfast', 'dinner', 'custom']) {
    await vm.runInContext(`loadPreset(${JSON.stringify(id)})`, context);
    const result = vm.runInContext(`(() => {
      for (let i = 0; i < state.R.steps.length; i++) go(i);
      return {steps: state.R.steps.length, html: $('step').innerHTML};
    })()`, context);
    assert.ok(result.steps >= 5);
    assert.ok(result.html.includes('Tổng kết'));
    assert.ok(!result.html.includes('undefined'));
    console.log(`${id}: rendered ${result.steps} steps`);
  }
  await vm.runInContext("$('baskets').value = ''; run()", context);
  assert.equal(vm.runInContext('state.R', context), null);
  assert.ok(elements.get('step').innerHTML.includes('Chưa có giao dịch'));
  console.log('Frontend/API smoke checks passed');
})().catch(error => {console.error(error); process.exitCode = 1;});
