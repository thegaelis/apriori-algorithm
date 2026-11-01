/* Client-side checkout: validates the form, shows a receipt, stores nothing. */
(() => {
  const $ = id => document.getElementById(id);
  const esc = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const vnd = n => StoreCart.vnd(n);
  const CART = StoreCart.load();
  let STORE = null;
  let summary = null;

  function renderSummary() {
    const comboLines = summary.applied.map(entry =>
      `<div class="saving"><dt>${esc(entry.combo.items.map(code => STORE.catalog[code].display_name).join(' + '))} × ${entry.times}</dt><dd>−${vnd(entry.saving)}</dd></div>`
    ).join('');
    $('orderSummary').innerHTML = `<h3>Tóm tắt đơn hàng</h3>
      <ul class="mini-lines">
        ${summary.lines.map(line => `<li><span>${esc(line.product.display_name)} × ${line.qty}</span><b>${vnd(line.total)}</b></li>`).join('')}
      </ul>
      <dl>
        <div><dt>Tạm tính</dt><dd>${vnd(summary.subtotal)}</dd></div>
        ${comboLines}
        <div><dt>Phí giao hàng</dt><dd>${summary.shipping ? vnd(summary.shipping) : 'Miễn phí'}</dd></div>
        <div class="grand"><dt>Tổng cộng</dt><dd>${vnd(summary.total)}</dd></div>
      </dl>
      `;
  }

  function setError(field, message) {
    const wrapper = document.querySelector(`[data-field="${field}"]`);
    if (!wrapper) return;
    wrapper.classList.add('field-error');
    let small = wrapper.querySelector('small');
    if (!small) {
      small = document.createElement('small');
      wrapper.appendChild(small);
    }
    small.textContent = message;
  }

  function clearErrors() {
    document.querySelectorAll('.field-error').forEach(wrapper => {
      wrapper.classList.remove('field-error');
      const small = wrapper.querySelector('small');
      if (small) small.remove();
    });
  }

  function placeOrder() {
    const id = 'DH' + (crypto.randomUUID?.() || Math.random().toString(16).slice(2)).replace(/-/g, '').slice(0, 8).toUpperCase();
    const total = summary.total;
    const count = summary.count;
    StoreCart.save({});
    $('cartCountBadge').textContent = '0';
    $('checkoutMain').innerHTML = `<section class="order-ok">
      <span aria-hidden="true">✅</span>
      <h1>Đặt hàng thành công!</h1>
      <p>Cảm ơn bạn đã mua sắm tại BasketIQ Fresh Market. Mã đơn hàng của bạn là <b>${esc(id)}</b>.</p>
      <div class="order-box">
        <dl>
          <div><dt>Mã đơn</dt><dd>${esc(id)}</dd></div>
          <div><dt>Số món</dt><dd>${count}</dd></div>
          <div class="grand"><dt>Tổng cộng</dt><dd>${vnd(total)}</dd></div>
        </dl>
        <div class="empty" style="padding:20px 0 0;border:0;background:transparent">
          <a class="btn" href="/shop">Tiếp tục mua sắm</a>
          <a class="btn btn-ghost" href="/dataset">Xem thống kê Apriori</a>
        </div>
      </div>
    </section>`;
  }

  $('checkoutForm').addEventListener('submit', event => {
    event.preventDefault();
    if (!summary) return;
    clearErrors();
    const data = new FormData(event.target);
    const name = String(data.get('name') || '').trim();
    const phone = String(data.get('phone') || '').replace(/\s/g, '');
    const address = String(data.get('address') || '').trim();
    let ok = true;

    if (!name) { setError('name', 'Vui lòng nhập họ tên'); ok = false; }
    if (!/^0\d{9,10}$/.test(phone)) { setError('phone', 'Số điện thoại gồm 10–11 chữ số, bắt đầu bằng 0'); ok = false; }
    if (address.length < 5) { setError('address', 'Vui lòng nhập địa chỉ giao hàng'); ok = false; }
    if (!ok) return;

    placeOrder();
  });

  fetch('/api/store', {cache: 'no-store'})
    .then(r => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
    .then(store => {
      STORE = store;
      summary = StoreCart.price(CART, STORE);
      if (!summary.lines.length) {
        location.replace('/cart');
        return;
      }
      $('cartCountBadge').textContent = summary.count;
      renderSummary();
    })
    .catch(error => {
      $('orderSummary').innerHTML = `<p class="muted">Không tải được dữ liệu: ${esc(error.message)}</p>`;
    });
})();
