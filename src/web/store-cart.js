/* Shared cart storage, VND formatting, and combo-aware pricing. */
window.StoreCart = (() => {
  const KEY = 'basketiq.cart.groceries';
  const FREE_SHIPPING = 300000;
  const SHIPPING_FEE = 20000;

  function load() {
    try {
      const raw = JSON.parse(localStorage.getItem(KEY) || '{}');
      const clean = {};
      for (const [code, qty] of Object.entries(raw)) {
        if (Number.isInteger(qty) && qty > 0) clean[code] = qty;
      }
      return clean;
    } catch (error) {
      return {};
    }
  }

  function save(cart) {
    try {
      localStorage.setItem(KEY, JSON.stringify(cart));
    } catch (error) {
      /* Storage can be unavailable in private mode; keep the in-memory cart. */
    }
  }

  function vnd(n) {
    return new Intl.NumberFormat('vi-VN').format(Math.round(n)) + 'đ';
  }

  function price(cart, store) {
    const lines = [];
    for (const [code, qty] of Object.entries(cart || {})) {
      const product = store.catalog[code];
      if (!product) continue;
      lines.push({ code, qty, product, total: product.price * qty });
    }

    const remaining = Object.fromEntries(lines.map(line => [line.code, line.qty]));
    const combos = [...(store.combos || [])].sort((a, b) => b.saving - a.saving);
    const applied = [];
    for (const combo of combos) {
      const times = Math.min(...combo.items.map(item => remaining[item] || 0));
      if (times > 0) {
        applied.push({ combo, times, saving: combo.saving * times });
        for (const item of combo.items) remaining[item] -= times;
      }
    }

    const nudges = [];
    for (const combo of combos) {
      if (applied.some(entry => entry.combo.id === combo.id)) continue;
      const missing = combo.items.filter(item => !(item in (cart || {})));
      if (missing.length === 1 && store.catalog[missing[0]]) {
        nudges.push({ combo, missing: store.catalog[missing[0]] });
      }
      if (nudges.length === 3) break;
    }

    const subtotal = lines.reduce((sum, line) => sum + line.total, 0);
    const discount = applied.reduce((sum, entry) => sum + entry.saving, 0);
    const after = subtotal - discount;
    const shipping = lines.length && after < FREE_SHIPPING ? SHIPPING_FEE : 0;
    return {
      lines,
      applied,
      nudges,
      subtotal,
      discount,
      shipping,
      total: after + shipping,
      toFreeShipping: Math.max(0, FREE_SHIPPING - after),
      count: lines.reduce((sum, line) => sum + line.qty, 0),
    };
  }

  return { KEY, FREE_SHIPPING, SHIPPING_FEE, load, save, vnd, price };
})();
