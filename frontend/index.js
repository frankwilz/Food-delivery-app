const $ = (id) => document.getElementById(id);
const app = $("app");
const state = { restaurants: null, cuisine: "All", query: "" };

const api = (path) => $("apiBase").value.replace(/\/$/, "") + path;

async function request(path, options) {
  const res = await fetch(api(path), options);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch (_) {}
    throw new Error(res.status + " " + detail);
  }
  return res.json();
}

function el(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  Object.entries(props).forEach(([k, v]) => {
    if (k === "style") node.style.cssText = v;
    else if (k === "class") node.className = v;
    else node[k] = v;
  });
  children.flat().forEach((c) => node.append(c instanceof Node ? c : document.createTextNode(c)));
  return node;
}

// Visual helpers: no image field in the API, so each cuisine gets a color and emoji.
const EMOJI = [
  [/pizza|italian/i, "\u{1F355}"], [/burger|american|grill|bbq/i, "\u{1F354}"],
  [/sushi|japan|ramen/i, "\u{1F363}"], [/indian|curry/i, "\u{1F35B}"],
  [/mexic|taco/i, "\u{1F32E}"], [/chinese/i, "\u{1F961}"], [/thai|viet|noodle/i, "\u{1F35C}"],
  [/salad|health|vegan|vegetarian/i, "\u{1F957}"], [/dessert|bakery|cake|sweet/i, "\u{1F370}"],
  [/coffee|cafe|tea/i, "\u2615"], [/chicken|wings/i, "\u{1F357}"], [/seafood|fish/i, "\u{1F990}"],
  [/african|nigerian|jollof/i, "\u{1F372}"], [/breakfast|brunch/i, "\u{1F95E}"],
];
const emojiFor = (cuisine) => (EMOJI.find(([re]) => re.test(cuisine || "")) || [null, "\u{1F37D}\uFE0F"])[1];
const hueFor = (s) => [...String(s || "")].reduce((a, c) => a + c.charCodeAt(0), 0) * 37 % 360;
const bannerStyle = (cuisine) => {
  const h = hueFor(cuisine);
  return `background: linear-gradient(135deg, hsl(${h} 75% 90%), hsl(${h} 65% 78%));`;
};
const money = (p) => (typeof p === "number" ? "$" + p.toFixed(2) : String(p ?? ""));

function banner(r, extraClass = "") {
  return el("div", { class: "banner " + extraClass, style: bannerStyle(r.cuisine) },
    el("span", { "aria-hidden": "true" }, emojiFor(r.cuisine)),
    el("span", { class: "badge " + (r.is_open ? "open" : "closed") }, r.is_open ? "Open now" : "Closed"));
}

// ---------- Home ----------
async function loadRestaurants() {
  state.restaurants = await request("/restaurants");
}

function filtered() {
  const q = state.query.toLowerCase();
  return state.restaurants.filter((r) =>
    (state.cuisine === "All" || r.cuisine === state.cuisine) &&
    (!q || [r.name, r.cuisine, r.address].some((v) => String(v).toLowerCase().includes(q))));
}

function renderGrid() {
  const holder = $("gridHolder");
  if (!holder) return;
  holder.textContent = "";
  const list = filtered();
  holder.append(el("p", { class: "count" }, list.length + (list.length === 1 ? " restaurant" : " restaurants")));
  if (!list.length) {
    holder.append(el("div", { class: "state" }, "No restaurants match your search. Try a different word or clear the cuisine filter."));
    return;
  }
  holder.append(el("div", { class: "grid" }, list.map((r) =>
    el("a", { class: "rcard" + (r.is_open ? "" : " is-closed"), href: "#/restaurant/" + r.id },
      banner(r),
      el("div", { class: "rbody" },
        el("p", { class: "rname" }, r.name),
        el("div", { class: "rmeta" }, el("span", { class: "rating" }, String(r.rating)), el("span", {}, r.cuisine)),
        el("div", { class: "addr" }, r.address))))));
}

function renderChips() {
  const holder = $("chips");
  if (!holder) return;
  holder.textContent = "";
  const cuisines = ["All", ...new Set(state.restaurants.map((r) => r.cuisine).filter(Boolean))].sort((a, b) =>
    a === "All" ? -1 : b === "All" ? 1 : a.localeCompare(b));
  cuisines.forEach((c) => {
    const chip = el("button", { class: "chip", type: "button", "aria-pressed": String(state.cuisine === c) },
      c === "All" ? "\u{1F37D}\uFE0F" : emojiFor(c), c);
    chip.addEventListener("click", () => { state.cuisine = c; renderChips(); renderGrid(); });
    holder.append(chip);
  });
}

async function showHome() {
  $("searchWrap").hidden = false;
  app.textContent = "";
  app.append(el("h1", {}, "Restaurants near you"), el("div", { class: "chips", id: "chips" }), el("div", { id: "gridHolder" }));
  $("gridHolder").append(el("div", { class: "grid" }, [1, 2, 3, 4, 5, 6].map(() => el("div", { class: "skeleton" }))));
  try {
    if (!state.restaurants) await loadRestaurants();
    renderChips();
    renderGrid();
  } catch (err) {
    $("gridHolder").textContent = "";
    $("gridHolder").append(el("div", { class: "state error" },
      "Could not load restaurants (" + err.message + "). Check that the backend is running and the API address below is right."));
  }
}

// ---------- Restaurant page ----------
async function showDetail(id) {
  $("searchWrap").hidden = true;
  app.textContent = "";
  app.append(el("a", { class: "back", href: "#/" }, "\u2190 All restaurants"), el("div", { class: "skeleton", style: "height:300px" }));
  let r;
  try {
    r = await request("/restaurants/" + id);
  } catch (err) {
    app.textContent = "";
    app.append(el("a", { class: "back", href: "#/" }, "\u2190 All restaurants"),
      el("div", { class: "state error" }, err.message.startsWith("404")
        ? "That restaurant doesn't exist. It may have been removed."
        : "Could not load this restaurant (" + err.message + ")."));
    return;
  }
  const menuHolder = el("div", {}, el("div", { class: "skeleton", style: "height:100px" }));
  app.textContent = "";
  app.append(
    el("a", { class: "back", href: "#/" }, "\u2190 All restaurants"),
    el("section", { class: "hero" },
      banner(r),
      el("div", { class: "hero-body" },
        el("h1", {}, r.name),
        el("div", { class: "facts" },
          el("span", { class: "rating" }, r.rating + " rating"),
          el("span", {}, r.cuisine),
          el("span", {}, r.address),
          el("span", {}, r.is_open ? "Open now" : "Closed right now")))),
    el("h2", {}, "Menu"),
    menuHolder);
  try {
    const items = await request("/restaurants/" + id + "/menu");
    menuHolder.textContent = "";
    if (!items.length) {
      menuHolder.append(el("div", { class: "state" }, "This restaurant hasn't added any menu items yet."));
      return;
    }
    const groups = {};
    items.forEach((m) => { (groups[m.category || ""] = groups[m.category || ""] || []).push(m); });
    Object.entries(groups).forEach(([cat, group]) => {
      if (cat) menuHolder.append(el("h2", {}, cat));
      menuHolder.append(el("div", { class: "menu-grid" }, group.map((m) =>
        el("div", { class: "mitem" },
          el("div", {}, el("p", { class: "mname" }, m.name), m.description ? el("p", { class: "mdesc" }, m.description) : ""),
          el("div", { class: "mprice" }, money(m.price))))));
    });
  } catch (err) {
    menuHolder.textContent = "";
    menuHolder.append(el("div", { class: "state error" }, "Could not load the menu (" + err.message + ")."));
  }
}

// ---------- Routing ----------
function route() {
  const m = location.hash.match(/^#\/restaurant\/(\d+)/);
  if (m) showDetail(m[1]); else showHome();
  window.scrollTo(0, 0);
}
window.addEventListener("hashchange", route);

// ---------- Search ----------
$("search").addEventListener("input", (e) => { state.query = e.target.value; renderGrid(); });
$("apiBase").addEventListener("change", () => { state.restaurants = null; route(); });

// ---------- Create restaurant ----------
const dialog = $("createDialog");
$("openCreate").addEventListener("click", () => { $("formMsg").textContent = ""; dialog.showModal(); });
$("cancelCreate").addEventListener("click", () => dialog.close());

function toast(text) {
  const t = el("div", { class: "toast", role: "status" }, text);
  document.body.append(t);
  setTimeout(() => t.remove(), 3000);
}

$("createForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const msg = $("formMsg");
  msg.className = "form-msg"; msg.textContent = "Saving...";
  const f = e.target.elements;
  const body = {
    name: f.name.value.trim(),
    cuisine: f.cuisine.value.trim(),
    address: f.address.value.trim(),
    rating: parseFloat(f.rating.value),
    is_open: f.is_open.checked,
  };
  try {
    const created = await request("/restaurants", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    e.target.reset();
    dialog.close();
    state.restaurants = null;
    toast("Added " + created.name);
    if (location.hash && location.hash !== "#/") location.hash = "#/"; else route();
  } catch (err) {
    msg.className = "form-msg error";
    msg.textContent = "Could not create the restaurant: " + err.message;
  }
});

route();
