/* Cart page rendering and mutations. */
(() => {
  const $ = id => document.getElementById(id);
  const esc = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const vnd = n => StoreCart.vnd(n);

  let STORE = null;
  let DATA = null;
  let CART = {};

  const titleOf = combo => combo.items.map(code => STORE.catalog[code].display_name).join(' + ');

  function productCard(code) {
    const p = STORE.catalog[code];
    const category = STORE.categories.find(c => c.id === p.category) || STORE.categories[0];
    return `<article class="card">
      <div class="card-media" style="--tint:${esc(category.color)}">
        <span class="emoji" aria-hidden="true">${esc(p.icon)}</span>
      </div>
      <div class="card-body">
        <span class="card-title">${esc(p.display_name)}</span>
        <span class="card-unit">${esc(p.unit)}</span>
        <div class="card-foot">
          <span class="price">${vnd(p.price)}</span>
          <button class="btn-add" type="button" data-act="add" data-code="${esc(code)}" aria-label="Thêm ${esc(p.display_name)}">+</button>
        </div>
      </div>
    </article>`;
  }

  function renderSummary(summary) {
    const empty = summary.count === 0;
    const progress = summary.toFreeShipping
      ? ((StoreCart.FREE_SHIPPING - summary.toFreeShipping) / StoreCart.FREE_SHIPPING * 100)
      : 100;
    const ship = empty ? '' : summary.toFreeShipping
      ? `<div class="ship">
          <p>Mua thêm <b>${vnd(summary.toFreeShipping)}</b> để được miễn phí giao hàng</p>
          <div class="ship-bar"><span style="width:${progress}%"></span></div>
        </div>`
      : '<div class="ship ship-ok"><p>🎉 Đơn hàng được <b>miễn phí giao hàng</b></p></div>';
    const comboSavings = summary.applied.map(entry =>
      `<div class="saving"><dt>${esc(titleOf(entry.combo))} × ${entry.times}</dt><dd>−${vnd(entry.saving)}</dd></div>`
    ).join('');
    $('cartSummary').innerHTML = empty
      ? `<h3>Tóm tắt đơn hàng</h3><p class="muted">Giỏ hàng đang trống.</p>`
      : `<h3>Tóm tắt đơn hàng</h3>
         ${ship}
         <dl>
           <div><dt>Tạm tính</dt><dd>${vnd(summary.subtotal)}</dd></div>
           ${comboSavings}
           <div><dt>Phí giao hàng</dt><dd>${summary.shipping ? vnd(summary.shipping) : 'Miễn phí'}</dd></div>
           <div class="grand"><dt>Tổng cộng</dt><dd>${vnd(summary.total)}</dd></div>
         </dl>
         <a class="btn btn-block" href="/checkout">Đặt hàng</a>
         `;
  }

  function renderForgot() {
    const codes = Object.keys(CART);
    const recs = StoreRecs.compute(new Set(codes), DATA, 6).recs.filter(rec => rec.rule);
    const picks = recs.length ? recs.map(rec => rec.code) : STORE.bestsellers.slice(0, 6);
    $('forgotGrid').innerHTML = picks.map(productCard).join('');
  }

  function render() {
    const summary = StoreCart.price(CART, STORE);
    $('cartCountBadge').textContent = summary.count;
    $('cartCount').textContent = `${summary.count} món`;
    $('nudges').innerHTML = summary.nudges.map(({ combo, missing }) =>
      `<div class="nudge">
        <span class="nudge-icon" aria-hidden="true">🎁</span>
        <p>Thêm <b>${esc(missing.display_name)}</b> để nhận combo <b>${esc(titleOf(combo))}</b>, tiết kiệm ${vnd(combo.saving)}.</p>
        <button class="btn btn-sm" type="button" data-act="add" data-code="${esc(combo.items.find(code => !(code in CART)))}">Thêm ${vnd(missing.price)}</button>
      </div>`
    ).join('');
    $('cartLines').innerHTML = summary.lines.length ? summary.lines.map(line => {
      const p = line.product;
      const category = STORE.categories.find(c => c.id === p.category) || STORE.categories[0];
      return `<li class="cart-line">
        <span class="cart-thumb" style="--tint:${esc(category.color)}" aria-hidden="true">${esc(p.icon)}</span>
        <div class="cart-desc">
          <a href="/shop">${esc(p.display_name)}</a>
          <span>${esc(p.unit)} · ${vnd(p.price)}</span>
        </div>
        <div class="stepper stepper-sm">
          <button type="button" data-act="dec" data-code="${esc(line.code)}" aria-label="Giảm">−</button>
          <span>${line.qty}</span>
          <button type="button" data-act="inc" data-code="${esc(line.code)}" aria-label="Tăng">+</button>
        </div>
        <b class="cart-total">${vnd(line.total)}</b>
        <button class="link-btn" type="button" data-act="remove" data-code="${esc(line.code)}">Xóa</button>
      </li>`;
    }).join('') : `<li class="empty" style="border:0;background:transparent">
        <span aria-hidden="true">🛒</span><h1>Giỏ hàng đang trống</h1>
        <p>Hãy chọn vài món ngon từ cửa hàng nhé.</p>
        <a class="btn" href="/shop">Mua sắm ngay</a>
      </li>`;
    renderSummary(summary);
    renderForgot();
  }

  function add(code) {
    if (!STORE.catalog[code]) return;
    CART[code] = (CART[code] || 0) + 1;
    StoreCart.save(CART);
    render();
  }

  document.addEventListener('click', event => {
    const el = event.target.closest('[data-act]');
    if (!el) return;
    const code = el.dataset.code;
    switch (el.dataset.act) {
      case 'add': add(code); break;
      case 'inc': CART[code] = (CART[code] || 0) + 1; StoreCart.save(CART); render(); break;
      case 'dec':
        CART[code] = (CART[code] || 0) - 1;
        if (CART[code] <= 0) delete CART[code];
        StoreCart.save(CART);
        render();
        break;
      case 'remove': delete CART[code]; StoreCart.save(CART); render(); break;
    }
  });

  const cartButton = document.querySelector('.page-cart-btn');
  if (cartButton) {
    cartButton.addEventListener('click', event => {
      event.preventDefault();
      const lines = document.getElementById('cartLines');
      lines.scrollIntoView({behavior: 'smooth', block: 'center'});
      lines.classList.add('cart-flash');
      setTimeout(() => lines.classList.remove('cart-flash'), 700);
    });
  }

  Promise.all([
    fetch('/api/store', {cache: 'no-store'}).then(r => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); }),
    fetch('/api/ecom-rules', {cache: 'no-store'}).then(r => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
  ]).then(([store, data]) => {
    STORE = store;
    DATA = data;
    CART = StoreCart.load();
    for (const code of Object.keys(CART)) if (!STORE.catalog[code]) delete CART[code];
    StoreCart.save(CART);
    render();
  }).catch(error => {
    $('cartLines').innerHTML = `<li class="empty"><p>Không tải được dữ liệu: ${esc(error.message)}</p></li>`;
  });
})();
