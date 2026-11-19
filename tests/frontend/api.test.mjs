import test from "node:test";
import assert from "node:assert/strict";
import { ApiError, SessionChangedError, createApiClient } from "../../frontend/api.mjs";

const API = "http://127.0.0.1:8000";
const TOKEN_KEY = `food-delivery:token:${API}`;
const profile = { id: 1, name: "Ana", email: "ana@example.com", delivery_address: "123 Main St", role: "customer", is_active: true };
const credentials = { email: profile.email, password: "never-persist-this" };
const response = (body, status = 200) => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

function memoryStorage(entries = []) {
  const data = new Map(entries);
  return { data, getItem: (key) => data.get(key) ?? null, setItem: (key, value) => data.set(key, value), removeItem: (key) => data.delete(key) };
}

function harness({ storage = memoryStorage(), baseURL = API } = {}) {
  const calls = [];
  const replies = [];
  const fetchImpl = async (url, options) => {
    calls.push({ url, ...options });
    assert.ok(replies.length, `Unexpected request: ${url}`);
    const reply = replies.shift();
    return typeof reply === "function" ? reply() : reply;
  };
  const client = createApiClient({ baseURL, fetchImpl, storage });
  return { client, calls, replies, storage };
}

async function signIn(h, token = "first-token", account = profile) {
  h.replies.push(response({ access_token: token, token_type: "bearer" }), response(account));
  await h.client.login(credentials);
}

function deferred() {
  let resolve;
  const promise = new Promise((done) => { resolve = done; });
  return { promise, resolve };
}

test("sign in obtains the profile from /customers/me and stores only the token", async () => {
  const h = harness();
  await signIn(h);
  assert.equal(h.calls[0].url, `${API}/auth/login`);
  assert.equal(h.calls[0].headers.get("Authorization"), null);
  assert.deepEqual(JSON.parse(h.calls[0].body), credentials);
  assert.equal(h.calls[1].url, `${API}/customers/me`);
  assert.equal(h.calls[1].headers.get("Authorization"), "Bearer first-token");
  assert.deepEqual(h.client.snapshot().user, profile);
  assert.deepEqual([...h.storage.data], [[TOKEN_KEY, "first-token"]]);
  assert.ok(!JSON.stringify([...h.storage.data]).includes(credentials.password));
  assert.ok(!("token" in h.client.snapshot()));
});

test("every protected request uses the current bearer token and keeps caller headers and JSON", async () => {
  const h = harness();
  await signIn(h);
  for (const path of ["/cart", "/orders", "/checkout"]) {
    h.replies.push(response({ ok: true }));
    await h.client.request(path, { method: "POST", headers: { "Content-Type": "application/json", Authorization: "Bearer stale-token" }, body: "{}" });
    const call = h.calls.at(-1);
    assert.equal(call.headers.get("Authorization"), "Bearer first-token");
    assert.equal(call.headers.get("Content-Type"), "application/json");
    assert.equal(call.body, "{}");
    assert.equal(call.credentials, "omit");
    assert.equal(call.redirect, "error");
  }
});

test("registration sends only accepted fields and then signs in", async () => {
  const h = harness();
  h.replies.push(response(profile, 201), response({ access_token: "new-token" }), response(profile));
  await h.client.register({ ...profile, ...credentials, role: "manager" });
  assert.equal(h.calls[0].url, `${API}/customers`);
  assert.equal(h.calls[0].headers.get("Authorization"), null);
  assert.deepEqual(JSON.parse(h.calls[0].body), {
    name: profile.name, ...credentials, delivery_address: profile.delivery_address,
  });
  assert.equal(h.client.snapshot().user.role, "customer");
});

for (const [status, detail, register] of [
  [401, "Incorrect email or password", false],
  [403, "Customer account has been deactivated", false],
  [409, "An account with this email already exists", true],
]) {
  test(`displays the API error for ${status}: ${detail}`, async () => {
    const h = harness();
    h.replies.push(response({ detail }, status));
    await assert.rejects(register ? h.client.register({ ...profile, ...credentials }) : h.client.login(credentials),
      (error) => error instanceof ApiError && error.status === status && error.message === `${status} ${detail}`);
    assert.equal(h.client.snapshot().user, null);
    assert.equal(h.client.snapshot().loading, false);
    assert.equal(h.storage.data.size, 0);
  });
}

test("refresh validates the stored token with the server rather than trusting stored profile data", async () => {
  const h = harness({ storage: memoryStorage([[TOKEN_KEY, "saved-token"]]) });
  const manager = { ...profile, role: "manager" };
  h.replies.push(response(manager));
  await h.client.restore();
  assert.equal(h.calls[0].headers.get("Authorization"), "Bearer saved-token");
  assert.equal(h.client.snapshot().user.role, "manager");
});

for (const [status, detail] of [[401, "Invalid or expired token"], [403, "Customer account has been deactivated"]]) {
  test(`invalid refresh session (${status}) is removed`, async () => {
    const h = harness({ storage: memoryStorage([[TOKEN_KEY, "saved-token"]]) });
    h.replies.push(response({ detail }, status));
    await assert.rejects(h.client.restore(), ApiError);
    assert.equal(h.storage.data.size, 0);
    assert.equal(h.client.snapshot().user, null);
    assert.equal(h.client.snapshot().loading, false);
  });
}

test("wrong-role 403 preserves the session, while a protected 401 signs out", async () => {
  const h = harness();
  await signIn(h);
  h.replies.push(response({ detail: "Only a manager can do this" }, 403));
  await assert.rejects(h.client.request("/restaurants", { method: "POST" }), ApiError);
  assert.equal(h.client.snapshot().user.id, profile.id);
  h.replies.push(response({ detail: "Invalid or expired token" }, 401));
  await assert.rejects(h.client.request("/cart"), ApiError);
  assert.equal(h.client.snapshot().user, null);
  assert.equal(h.storage.data.size, 0);
});

test("logout prevents a pending sign-in profile response from restoring the session", async () => {
  const h = harness();
  const pending = deferred();
  const startedProfile = deferred();
  h.replies.push(response({ access_token: "late-token" }), () => { startedProfile.resolve(); return pending.promise; });
  const login = h.client.login(credentials);
  await startedProfile.promise;
  h.client.logout();
  pending.resolve(response(profile));
  await assert.rejects(login, SessionChangedError);
  assert.equal(h.client.snapshot().user, null);
  assert.equal(h.storage.data.size, 0);
});

test("logout prevents a pending refresh from restoring the session", async () => {
  const h = harness({ storage: memoryStorage([[TOKEN_KEY, "saved-token"]]) });
  const pending = deferred();
  h.replies.push(() => pending.promise);
  const restored = h.client.restore();
  h.client.logout();
  pending.resolve(response(profile));
  await assert.rejects(restored, SessionChangedError);
  assert.equal(h.client.snapshot().user, null);
  assert.equal(h.storage.data.size, 0);
});

test("a late 401 from an earlier session cannot sign out a later login", async () => {
  const h = harness();
  await signIn(h);
  const pending = deferred();
  h.replies.push(() => pending.promise);
  const oldRequest = h.client.request("/orders");
  h.client.logout();
  await signIn(h, "second-token", { ...profile, id: 2 });
  pending.resolve(response({ detail: "Invalid or expired token" }, 401));
  await assert.rejects(oldRequest, SessionChangedError);
  assert.equal(h.client.snapshot().user.id, 2);
  assert.equal(h.storage.data.get(TOKEN_KEY), "second-token");
});

test("API changes clear sessions and prevent tokens or pending data crossing server boundaries", async () => {
  const other = "http://localhost:9000";
  const h = harness({ storage: memoryStorage([[`food-delivery:token:${other}`, "other-saved-token"]]) });
  await signIn(h);
  const pending = deferred();
  h.replies.push(() => pending.promise);
  const oldRequest = h.client.request("/orders");
  h.client.setBaseURL(`${other}/`);
  pending.resolve(response([{ id: 1 }]));
  await assert.rejects(oldRequest, SessionChangedError);
  assert.equal(h.client.snapshot().baseURL, other);
  assert.equal(h.client.snapshot().user, null);
  assert.equal(h.storage.data.size, 0);
  h.replies.push(response([]));
  await h.client.request("/orders");
  assert.equal(h.calls.at(-1).url, `${other}/orders`);
  assert.equal(h.calls.at(-1).headers.get("Authorization"), null);
});

test("a token for one API is not loaded for another API", async () => {
  const h = harness({ storage: memoryStorage([["food-delivery:token:http://another.example", "other-token"]]) });
  assert.equal(await h.client.restore(), null);
  assert.equal(h.calls.length, 0);
});

test("profile edits use PATCH with the bearer token and update the server-returned user", async () => {
  const h = harness();
  await signIn(h);
  const changes = { name: "Ana S", email: "new@example.com", delivery_address: "321 Second St" };
  h.replies.push(response({ ...profile, ...changes }));
  await h.client.updateAccount(changes);
  assert.equal(h.calls.at(-1).method, "PATCH");
  assert.equal(h.calls.at(-1).url, `${API}/customers/me`);
  assert.equal(h.calls.at(-1).headers.get("Authorization"), "Bearer first-token");
  assert.deepEqual(JSON.parse(h.calls.at(-1).body), changes);
  assert.equal(h.client.snapshot().user.email, changes.email);
});

test("structured validation errors remain readable", async () => {
  const h = harness();
  h.replies.push(response({ detail: [{ loc: ["body", "email"], msg: "Invalid email" }] }, 422));
  await assert.rejects(h.client.request("/customers", { method: "POST" }), /422 email: Invalid email/);
});

test("blocked storage still permits sign in and sign out", async () => {
  const storage = new Proxy({}, { get() { throw new Error("Storage blocked"); } });
  const h = harness({ storage });
  await signIn(h);
  assert.equal(h.client.snapshot().user.id, profile.id);
  h.client.logout();
  assert.equal(h.client.snapshot().user, null);
});

test("unsafe API addresses and absolute request destinations are rejected", async () => {
  const h = harness();
  for (const address of ["javascript:alert(1)", "https://user:password@example.com", "https://example.com?token=x"]) {
    assert.throws(() => h.client.setBaseURL(address));
  }
  await assert.rejects(h.client.request("//other.example/orders"));
  assert.equal(h.calls.length, 0);
});
