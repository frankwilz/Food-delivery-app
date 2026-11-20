// Every amount displayed here comes from the API, including cart and order totals.
export function createShopping({ app, el, request, money, getUser, navigate, toast }) {
  const button = (text, action, className = 'btn') => {
    const node = el('button', { type: 'button', class: className }, text);
    node.addEventListener('click', action);
    return node;
  };
  const message = () => el('p', { class: 'form-msg', role: 'status' });
  const report = (node, error) => { node.className = 'form-msg error'; node.textContent = error.message; };
  const json = (method, body) => ({ method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  const active = () => {
    const hash = location.hash;
    const id = getUser()?.id;
    return () => location.hash === hash && getUser()?.id === id;
  };

  function start(title) {
    app.textContent = '';
    app.append(el('a', { href: '#/', class: 'back' }, '← Restaurants'), el('h1', {}, title));
    if (!getUser()) {
      app.append(el('p', { class: 'state' }, 'Sign in to see your cart and orders. ', el('a', { href: '#/signin', class: 'text-link' }, 'Sign in')));
      return false;
    }
    return true;
  }

  function quantity(value, label) {
    return el('input', { type: 'number', class: 'field quantity', min: 1, max: 99, step: 1, required: true, value, 'aria-label': label });
  }

  function menuActions(item, restaurantOpen) {
    const holder = el('div', { class: 'menu-actions' });
    if (!item.is_active || !item.is_available || !restaurantOpen) {
      holder.append(el('span', { class: 'unavailable' }, restaurantOpen ? 'Currently unavailable' : 'Restaurant closed'));
      return holder;
    }
    if (!getUser()) {
      holder.append(el('a', { href: '#/signin', class: 'text-link' }, 'Sign in to order'));
      return holder;
    }
    const input = quantity(1, `Quantity of ${item.name}`);
    const submit = el('button', { class: 'btn', type: 'submit' }, 'Add to cart');
    const status = message();
    const form = el('form', { class: 'add-item-form' }, input, submit);
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      if (!form.reportValidity()) return;
      const current = active();
      submit.disabled = true;
      status.textContent = 'Adding…';
      try {
        await request('/cart/items', json('POST', { menu_item_id: item.id, quantity: Number(input.value) }));
        if (current()) { status.className = 'form-msg'; status.textContent = 'Added to cart.'; toast('Added ' + item.name); }
      } catch (error) { if (current()) report(status, error); }
      finally { submit.disabled = false; }
    });
    holder.append(form, status);
    return holder;
  }

  function totals(record) {
    return el('dl', { class: 'totals' },
      el('dt', {}, 'Subtotal'), el('dd', {}, money(record.subtotal)),
      el('dt', {}, 'Total'), el('dd', { class: 'grand-total' }, money(record.total)));
  }

  async function showCart() {
    if (!start('Your cart')) return;
    const current = active();
    const holder = el('section', { class: 'shopping-panel', 'aria-label': 'Shopping cart' });
    const status = message();
    holder.append(el('p', {}, 'Loading your cart…'));
    app.append(holder, status);
    let busy = false;
    async function change(action) {
      if (busy) return;
      busy = true;
      holder.setAttribute('aria-busy', 'true');
      holder.querySelectorAll('button, input').forEach(node => { node.disabled = true; });
      status.className = 'form-msg'; status.textContent = 'Updating…';
      try {
        const cart = await action();
        if (current()) { render(cart); status.textContent = ''; }
      } catch (error) { if (current()) report(status, error); }
      finally {
        busy = false;
        holder.setAttribute('aria-busy', 'false');
        holder.querySelectorAll('button, input').forEach(node => { node.disabled = false; });
      }
    }
    function render(cart) {
      holder.textContent = '';
      if (!cart.items.length) {
        holder.append(el('p', { class: 'state' }, 'Your cart is empty. ', el('a', { href: '#/', class: 'text-link' }, 'Browse restaurants')));
        return;
      }
      holder.append(el('p', { class: 'muted' }, 'Prices are checked again when you place your order.'));
      for (const line of cart.items) {
        const input = quantity(line.quantity, `Quantity of ${line.name}`);
        const update = el('button', { class: 'btn ghost', type: 'submit' }, 'Update');
        const form = el('form', { class: 'quantity-form' }, input, update);
        form.addEventListener('submit', event => {
          event.preventDefault();
          if (!form.reportValidity()) return;
          const value = Number(input.value);
          change(() => request(`/cart/items/${line.menu_item_id}`, json('PATCH', { quantity: value })));
        });
        holder.append(el('article', { class: 'cart-line' },
          el('div', {}, el('h2', {}, line.name), el('p', {}, money(line.unit_price) + ' each'),
            line.is_orderable ? '' : el('p', { class: 'unavailable' }, 'Currently unavailable. Remove this item before checkout.')),
          form,
          el('strong', {}, money(line.line_total)),
          button('Remove ' + line.name, () => change(() => request(`/cart/items/${line.menu_item_id}`, { method: 'DELETE' })), 'btn ghost')));
      }
      holder.append(totals(cart), button('Clear cart', () => change(() => request('/cart', { method: 'DELETE' })), 'btn ghost'));
      const checkout = button('Place order', async () => {
        if (busy) return;
        busy = true;
        holder.querySelectorAll('button, input').forEach(node => { node.disabled = true; });
        status.className = 'form-msg'; status.textContent = 'Placing your order…';
        try {
          const order = await request('/checkout', { method: 'POST' });
          if (current()) { toast('Order placed'); navigate('#/orders/' + order.id); }
        } catch (error) {
          if (current()) report(status, error);
        } finally {
          busy = false;
          holder.querySelectorAll('button, input').forEach(node => { node.disabled = false; });
        }
      });
      holder.append(el('p', { class: 'muted' }, 'Delivering to: ' + getUser().delivery_address),
        el('a', { href: '#/account', class: 'text-link' }, 'Update delivery address'), checkout);
    }
    try { const cart = await request('/cart'); if (current()) render(cart); }
    catch (error) { if (current()) { holder.textContent = ''; report(status, error); } }
  }

  function orderLines(order) {
    return el('div', { class: 'order-lines' }, order.items.map(line =>
      el('div', { class: 'order-line' },
        el('span', {}, `${line.quantity} × ${line.name} (${money(line.unit_price)} each)`),
        el('strong', {}, money(line.line_total)))));
  }

  async function showOrders() {
    if (!start('My orders')) return;
    const current = active();
    const holder = el('section', { class: 'order-list' }, el('p', {}, 'Loading orders…'));
    app.append(holder);
    try {
      const orders = await request('/orders');
      if (!current()) return;
      holder.textContent = '';
      if (!orders.length) holder.append(el('p', { class: 'state' }, 'You have no orders yet.'));
      for (const order of orders) holder.append(el('a', { href: '#/orders/' + order.id, class: 'order-card' },
        el('h2', {}, 'Order #' + order.id), el('p', {}, new Date(order.created_at).toLocaleString()),
        el('p', {}, 'Status: ' + order.status), el('strong', {}, money(order.total))));
    } catch (error) { if (current()) { holder.textContent = ''; holder.append(el('p', { class: 'state error' }, error.message)); } }
  }

  async function showOrder(id) {
    if (!start('Order confirmation')) return;
    const current = active();
    const holder = el('section', { class: 'shopping-panel' }, el('p', {}, 'Loading order…'));
    app.append(holder);
    try {
      const order = await request('/orders/' + id);
      if (!current()) return;
      holder.textContent = '';
      holder.append(el('h2', {}, 'Order #' + order.id), el('p', {}, 'Status: ' + order.status),
        el('p', {}, 'Placed: ' + new Date(order.created_at).toLocaleString()),
        el('p', {}, 'Delivery address: ' + order.delivery_address), orderLines(order), totals(order),
        el('a', { href: '#/orders', class: 'text-link' }, 'View all my orders'));
    } catch (error) { if (current()) { holder.textContent = ''; holder.append(el('p', { class: 'state error' }, error.message)); } }
  }

  return { menuActions, showCart, showOrders, showOrder };
}
