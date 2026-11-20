// Shared browser/Node HTTP client. Store only a token; always obtain the profile from the API.
export class ApiError extends Error {
  constructor(status, detail) {
    super(`${status} ${detail}`);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

export class SessionChangedError extends Error {
  constructor() {
    super("The session changed. Please try again.");
    this.name = "SessionChangedError";
    this.code = "SESSION_CHANGED";
  }
}

function normalizeBase(value) {
  const url = new URL(value.trim());
  if (!["http:", "https:"].includes(url.protocol) || url.username || url.password || url.search || url.hash) {
    throw new Error("Enter an HTTP or HTTPS API address without credentials, a query or a fragment.");
  }
  return url.href.replace(/\/+$/, "");
}

function errorDetail(body, fallback) {
  if (typeof body?.detail === "string") return body.detail;
  if (Array.isArray(body?.detail)) {
    return body.detail.map((entry) => `${(entry.loc || []).filter((part) => part !== "body").join(".")}: ${entry.msg}`).join("; ");
  }
  return fallback || "Request failed";
}

export function createApiClient({ baseURL, fetchImpl = globalThis.fetch, storage = null }) {
  let base = normalizeBase(baseURL);
  let token = null;
  let user = null;
  let loading = false;
  let error = "";
  let revision = 0;
  const listeners = new Set();
  const key = () => `food-delivery:token:${base}`;
  const stored = (method, ...args) => {
    // Browsers may disable storage. In that case the session still works until refresh.
    try { return storage?.[method](...args); } catch (_) { return null; }
  };
  const snapshot = () => ({ user, loading, error, baseURL: base });
  const notify = () => listeners.forEach((listener) => listener(snapshot()));
  const assertCurrent = (expected) => {
    if (expected !== revision) throw new SessionChangedError();
  };
  function clearSession(message = "") {
    revision += 1;
    token = null;
    user = null;
    loading = false;
    error = message;
    stored("removeItem", key());
    notify();
  }

  async function send(path, options = {}, expected = revision, bearer = token) {
    if (!path.startsWith("/") || path.startsWith("//")) throw new Error("Use a relative API path beginning with /.");
    const { auth = true, ...fetchOptions } = options;
    const headers = new Headers(fetchOptions.headers);
    // The caller cannot accidentally keep a token from another session or API.
    headers.delete("Authorization");
    if (auth && bearer) headers.set("Authorization", `Bearer ${bearer}`);
    let response;
    try {
      response = await fetchImpl(base + path, { ...fetchOptions, headers, credentials: "omit", redirect: "error" });
    } catch (err) {
      assertCurrent(expected);
      throw err;
    }
    assertCurrent(expected);
    let body = null;
    if (response.status !== 204) {
      try { body = await response.json(); } catch (_) { /* Preserve the HTTP error if its body is not JSON. */ }
    }
    assertCurrent(expected);
    if (!response.ok) {
      const detail = errorDetail(body, response.statusText);
      if (auth && bearer && (response.status === 401 || (response.status === 403 && /deactivated/i.test(detail)))) {
        clearSession(detail);
      }
      throw new ApiError(response.status, detail);
    }
    return body;
  }
  const json = (body) => ({ headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

  function beginSession() {
    clearSession();
    loading = true;
    notify();
    return revision;
  }

  async function signIn(credentials, expected) {
    const result = await send("/auth/login", { method: "POST", auth: false, ...json(credentials) }, expected);
    if (!result?.access_token) throw new Error("The API did not return a sign-in token.");
    const profile = await send("/customers/me", {}, expected, result.access_token);
    assertCurrent(expected);
    token = result.access_token;
    user = Object.freeze(profile);
    stored("setItem", key(), token);
    loading = false;
    error = "";
    notify();
    return user;
  }

  async function authenticate(credentials, registration) {
    const expected = beginSession();
    try {
      if (registration) await send("/customers", { method: "POST", auth: false, ...json(registration) }, expected);
      return await signIn(credentials, expected);
    } catch (err) {
      if (expected === revision) {
        loading = false;
        error = err.message;
        notify();
      }
      throw err;
    }
  }

  return {
    snapshot,
    subscribe(listener) {
      listeners.add(listener);
      listener(snapshot());
      return () => listeners.delete(listener);
    },
    request: (path, options) => send(path, options),
    login: ({ email, password }) => authenticate({ email, password }),
    register: ({ name, email, password, delivery_address }) => authenticate(
      { email, password }, { name, email, password, delivery_address },
    ),
    async restore() {
      const saved = stored("getItem", key());
      if (!saved) return null;
      const expected = ++revision;
      loading = true;
      error = "";
      notify();
      try {
        const profile = await send("/customers/me", {}, expected, saved);
        assertCurrent(expected);
        token = saved;
        user = Object.freeze(profile);
        loading = false;
        notify();
        return user;
      } catch (err) {
        if (expected === revision) clearSession(err.message);
        throw err;
      }
    },
    async updateAccount(changes) {
      const expected = revision;
      const profile = await send("/customers/me", { method: "PATCH", ...json(changes) }, expected);
      assertCurrent(expected);
      user = Object.freeze(profile);
      notify();
      return user;
    },
    logout: () => clearSession(),
    setBaseURL(value) {
      const next = normalizeBase(value);
      if (next === base) return;
      revision += 1;
      token = null;
      user = null;
      loading = false;
      error = "";
      stored("removeItem", key());
      base = next;
      // Changing servers explicitly signs out, even if that server was used before.
      stored("removeItem", key());
      notify();
    },
  };
}
