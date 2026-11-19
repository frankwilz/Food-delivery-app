import test from 'node:test';
import assert from 'node:assert/strict';
import { createShopping } from '../../frontend/shopping.mjs';

// Small DOM adapter: exercise user actions and API responses without a browser dependency.
class Element {
  constructor(tag, props = {}, children = []) {
    this.tag = tag; this.children = children.flat(); this.events = {};
    Object.assign(this, props);
  }
  append(...children) { this.children.push(...children.flat()); }
  addEventListener(name, fn) { this.events[name] = fn; }
  setAttribute(name, value) { this[name] = value; }
  set textContent(value) { this.children = [value]; }
  get textContent() { return this.children.map(child => child instanceof Element ? child.textContent : child).join(' '); }
  querySelectorAll(selector) {
    return this.children.filter(child => child instanceof Element).flatMap(child =>
      [...(selector.split(', ').includes(child.tag) ? [child] : []), ...child.querySelectorAll(selector)]);
  }
  reportValidity() {
    return this.querySelectorAll('input').every(input =>
      Number.isInteger(Number(input.value)) && Number(input.value) >= input.min && Number(input.value) <= input.max);
  }
  async fire(name) { if (!this.disabled) await this.events[name]?.({ preventDefault() {} }); }
}
const el = (tag, props, ...children) => new Element(tag, props, children);
const flush = () => new Promise(resolve => setImmediate(resolve));
const user = { id: 1, delivery_address: '10 Original Street' };
const cart = {
  id: 3, items: [{ menu_item_id: 1, name: 'Pizza', quantity: 2, unit_price: 10, line_total: 20, is_orderable: true }],
  subtotal: 77.77, total: 77.77,
};
function setup(handler) {
  globalThis.location = { hash: '#/cart' };
  const app = el('main', {});
  const calls = [], destinations = [];
  let currentUser = user;
  const shopping = createShopping({ app, el, money: value => '$' + value.toFixed(2),
    getUser: () => currentUser,
    request: async (path, options) => { calls.push({ path, options }); return handler(path, options); },
    navigate: path => { destinations.push(path); location.hash = path; }, toast() {},
  });
  const findButton = name => app.querySelectorAll('button').find(node => node.textContent === name);
  return { app, shopping, calls, destinations, findButton, setUser(value) { currentUser = value; } };
}

test('cart totals come from the API, and a quantity update renders the new server total', async () => {
  const screen = setup((path, options) => options?.method === 'PATCH' ? { ...cart, total: 90, subtotal: 90 } : cart);
  await screen.shopping.showCart();
  assert.match(screen.app.textContent, /\$77\.77/); // Deliberately differs from unit price × quantity.
  const form = screen.app.querySelectorAll('form')[0];
  form.querySelectorAll('input')[0].value = '3';
  await form.fire('submit'); await flush();
  assert.equal(screen.calls[1].path, '/cart/items/1');
  assert.deepEqual(JSON.parse(screen.calls[1].options.body), { quantity: 3 });
  assert.match(screen.app.textContent, /\$90\.00/);
});

test('invalid quantity is refused before a cart update request', async () => {
  const screen = setup(() => cart);
  await screen.shopping.showCart();
  const form = screen.app.querySelectorAll('form')[0];
  form.querySelectorAll('input')[0].value = '0';
  await form.fire('submit'); await flush();
  assert.equal(screen.calls.length, 1);
});

test('remove and clear render the cart returned by the server', async () => {
  for (const [label, path] of [['Remove Pizza', '/cart/items/1'], ['Clear cart', '/cart']]) {
    const screen = setup((_, options) => options?.method === 'DELETE' ? { items: [] } : cart);
    await screen.shopping.showCart();
    await screen.findButton(label).fire('click'); await flush();
    assert.deepEqual(screen.calls[1], { path, options: { method: 'DELETE' } });
    assert.match(screen.app.textContent, /Your cart is empty/);
  }
});

test('checkout failure keeps the cart visible and allows retry; success opens the saved order', async () => {
  let fail = true;
  const screen = setup((path) => {
    if (path !== '/checkout') return cart;
    if (fail) throw new Error('409 Pizza is unavailable');
    return { id: 42 };
  });
  await screen.shopping.showCart();
  await screen.findButton('Place order').fire('click');
  assert.match(screen.app.textContent, /409 Pizza is unavailable/);
  assert.match(screen.app.textContent, /\$77\.77/);
  assert.equal(screen.findButton('Place order').disabled, false);
  fail = false;
  await screen.findButton('Place order').fire('click');
  assert.deepEqual(screen.destinations, ['#/orders/42']);
});

test('a late cart response cannot render after signing out or switching accounts', async () => {
  let resolve;
  const screen = setup(() => new Promise(done => { resolve = done; }));
  const pending = screen.shopping.showCart();
  screen.setUser({ id: 2 });
  screen.app.textContent = 'Another account';
  resolve(cart); await pending;
  assert.equal(screen.app.textContent, 'Another account');
});

test('order confirmation displays stored snapshots and API totals without reading the menu', async () => {
  const order = { ...cart, id: 42, status: 'placed', created_at: '2026-11-18T12:00:00Z', delivery_address: '99 Saved Street' };
  const screen = setup(() => order);
  location.hash = '#/orders/42';
  await screen.shopping.showOrder(42);
  assert.deepEqual(screen.calls.map(call => call.path), ['/orders/42']);
  assert.match(screen.app.textContent, /99 Saved Street/);
  assert.match(screen.app.textContent, /placed/);
  assert.match(screen.app.textContent, /\$77\.77/);
});

test('adding an item submits its quantity and preserves the backend mixed-restaurant error', async () => {
  const screen = setup(() => { throw new Error('409 Clear the cart to order from another restaurant.'); });
  const actions = screen.shopping.menuActions({ id: 4, name: 'Taco', is_active: true, is_available: true }, true);
  const form = actions.querySelectorAll('form')[0];
  form.querySelectorAll('input')[0].value = '2';
  await form.fire('submit');
  assert.deepEqual(JSON.parse(screen.calls[0].options.body), { menu_item_id: 4, quantity: 2 });
  assert.match(actions.textContent, /Clear the cart to order from another restaurant/);
});

test('signed-out users and unavailable items cannot submit an add-to-cart form', () => {
  const screen = setup(() => { throw new Error('No request expected'); });
  screen.setUser(null);
  const item = { id: 1, name: 'Pizza', is_active: true, is_available: true };
  const signedOut = screen.shopping.menuActions(item, true);
  assert.match(signedOut.textContent, /Sign in to order/);
  assert.equal(signedOut.querySelectorAll('form').length, 0);
  screen.setUser(user);
  const unavailable = screen.shopping.menuActions({ ...item, is_available: false }, true);
  assert.match(unavailable.textContent, /Currently unavailable/);
  assert.equal(unavailable.querySelectorAll('form').length, 0);
});
