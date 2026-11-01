const fs = require('fs');
const vm = require('vm');
const path = require('path');

const root = path.dirname(__dirname);
const store = JSON.parse(fs.readFileSync(path.join(root, 'src/data/store.json'), 'utf8'));
const code = fs.readFileSync(path.join(root, 'src/web/store-cart.js'), 'utf8');
const storage = new Map();
const context = {
  window: {},
  localStorage: {
    getItem: key => (storage.has(key) ? storage.get(key) : null),
    setItem: (key, value) => storage.set(key, value),
  },
  Intl,
};
vm.createContext(context);
vm.runInContext(code, context);
const cart = context.window.StoreCart;

function assert(condition, message) {
  if (!condition) throw new Error(message);
}
function same(actual, expected, label) {
  assert(actual === expected, `${label}: expected ${expected}, got ${actual}`);
}

const combo = cart.price({ flour: 1, sugar: 1 }, store);
same(combo.subtotal, 49000, 'flour+sugar subtotal');
same(combo.discount, 5000, 'flour+sugar discount');
same(combo.total, 64000, 'flour+sugar total including shipping');

const nudge = cart.price({ flour: 1 }, store);
same(nudge.nudges.length, 1, 'flour nudge count');
same(nudge.nudges[0].missing.display_name, 'Đường', 'flour nudge target');

const large = cart.price({ 'whole milk': 20 }, store);
assert(large.subtotal >= 300000, 'large cart subtotal');
same(large.shipping, 0, 'large cart free shipping');

const small = cart.price({ 'whole milk': 1 }, store);
same(small.shipping, 20000, 'small cart shipping');

console.log('storefront smoke ok');
