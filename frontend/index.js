import { createApiClient } from "./api.mjs";
import { createAccountViews } from "./account.mjs";
import { createShopping } from "./shopping.mjs";

const $ = (id) => document.getElementById(id);
const app = $("app");
const state = { restaurants: null, cuisine: "All", query: "" };
let sessionStorageForAPI = null;
try { sessionStorageForAPI = window.sessionStorage; } catch (_) { /* Session works without persistence. */ }
const client = createApiClient({ baseURL: $("apiBase").value, storage: sessionStorageForAPI });
const request = (path, options) => client.request(path, options);
let routeVersion = 0;
let started = false;

function el(tag, props = {}, ...children) {
  const node = document.createElement(tag);
  Object.entries(props).forEach(([k, v]) => {
    if (v === undefined || v === null) return;
    if (k === "style") node.style.cssText = v;
    else if (k === "class") node.className = v;
    else if (k.startsWith("aria-") || k.startsWith("data-") || k === "role") node.setAttribute(k, v);
    else node[k] = v;
  });
  children.flat().forEach((c) => node.append(c instanceof Node ? c : document.createTextNode(c)));
  return node;
}

// Local illustrative food photos; no restaurant or menu photo field is assumed.
const EMOJI = [
  [/pizza|italian/i, "\u{1F355}"], [/burger|american|grill|bbq/i, "\u{1F354}"],
  [/sushi|japan|ramen/i, "\u{1F363}"], [/indian|curry/i, "\u{1F35B}"],
  [/mexic|taco/i, "\u{1F32E}"], [/chinese/i, "\u{1F961}"], [/thai|viet|noodle/i, "\u{1F35C}"],
  [/salad|health|vegan|vegetarian/i, "\u{1F957}"], [/dessert|bakery|cake|sweet/i, "\u{1F370}"],
  [/coffee|cafe|tea/i, "\u2615"], [/chicken|wings/i, "\u{1F357}"], [/seafood|fish/i, "\u{1F990}"],
  [/african|nigerian|jollof/i, "\u{1F372}"], [/breakfast|brunch/i, "\u{1F95E}"],
];
const emojiFor = (cuisine) => (EMOJI.find(([re]) => re.test(cuisine || "")) || [null, "\u{1F37D}\uFE0F"])[1];
const FOOD = [
  { pattern: /pizza|pizzeria|flatbread|margherita|pepperoni|calzone/i, cuisine: /italian/i, label: "pizza" },
  { pattern: /burger|slider|cheesesteak|sandwich/i, cuisine: /american|barbecue|bbq|grill/i, label: "burger" },
  { pattern: /taco|burrito|quesadilla|enchilada/i, cuisine: /mexic|tex.?mex/i, label: "tacos" },
  { pattern: /sushi|sashimi|maki|nigiri|poke/i, cuisine: /japan|seafood|fish|salmon/i, label: "sushi" },
  { pattern: /noodle|ramen|pho\b|udon|pasta|spaghetti|rice|bowl|curry/i, cuisine: /indian|thai|chinese|viet|korean|mediterranean|middle eastern|african|halal/i, label: "noodles and bowls" },
  { pattern: /salad|greens|grain/i, cuisine: /vegan|vegetarian|healthy/i, label: "salad" },
  { pattern: /chicken|wings|tender|fried|kfc|popeye/i, label: "fried chicken" },
  { pattern: /dessert|cake|cookie|brownie|ice.?cream|sweet|bakery|donut|doughnut|pastry|pancake/i, cuisine: /coffee|café|cafe|breakfast|brunch/i, label: "dessert" },
];
function foodPhoto(...descriptions) {
  const name = String(descriptions[0] || "");
  const category = String(descriptions[1] || "");
  const namedFood = /\b(cake|cookies?|brownie|pie|pastry|pudding|ice[ -]?cream|salad|burger|sandwich|chicken|steak|duck|pork|pizza|tacos?|noodles?|ramen|sauce)\b/i.test(name);
  const drinkCategory = /^(drinks?|beverages?|coffee\s*(?:&|and)\s*tea)$/i.test(category.trim());
  const drinkName = /\b(water|teas?|lemonade|limeade|lassi|coffee|espresso|latte|cappuccino|mocha|juice|soda|smoothie|milkshake|kombucha|chai|matcha|cocoa)\b/i.test(name);
  if (!namedFood && (drinkCategory || drinkName)) {
    return el("div", { class: "food-photo drink-photo", role: "img", "aria-label": "Illustrative citrus drink photograph" });
  }
  // Match the dish before its category/restaurant cuisine, so a salad at a pizzeria stays a salad.
  let tile = -1;
  for (const description of descriptions) {
    tile = FOOD.findIndex(({ pattern }) => pattern.test(String(description || "")));
    if (tile !== -1) break;
  }
  if (tile === -1) tile = FOOD.findIndex(({ cuisine }) => cuisine?.test(descriptions.join(" ")));
  if (tile === -1) tile = [...descriptions.join(" ")].reduce((sum, char) => sum + char.charCodeAt(0), 0) % FOOD.length;
  return el("div", { class: "food-photo", role: "img", "aria-label": `Illustrative ${FOOD[tile].label} photograph`,
    style: `--food-x:${(tile % 4) * 100 / 3}%;--food-y:${Math.floor(tile / 4) * 100}%;` });
}
const isManager = () => client.snapshot().user?.role === "manager";
const onHome = () => !location.hash || location.hash === "#/";
// Adding a restaurant only makes sense from the restaurant list, not inside one restaurant
const updateCreateButton = () => { $("openCreate").hidden = !isManager() || !onHome(); };
const money = (p) => (typeof p === "number" ? "$" + p.toFixed(2) : String(p ?? ""));
const ratingBadge = (r, suffix = "") => (r.rating
  ? el("span", { class: "rating" }, r.rating + suffix)
  : el("span", { class: "rating-new" }, "New"));

function banner(r, extraClass = "") {
  return el("div", { class: "banner " + extraClass },
    foodPhoto(r.name, r.cuisine),
    el("span", { class: "badge " + (r.is_open ? "open" : "closed") }, r.is_open ? "Open now" : "Closed"));
}

function menuDescription(item) {
  const description = String(item.description || "").trim();
  if (!/^Demo menu:/i.test(description)) return description;
  const content = description.replace(/^Demo menu:\s*/i, "");
  const disclaimer = "Fictional sample dish and price, not the restaurant's real menu.";
  return (content.endsWith(disclaimer) ? content.slice(0, -disclaimer.length) : content).trim();
}

// ---------- Home ----------
async function loadRestaurants() {
  state.restaurants = await request("/restaurants");
}

function filtered() {
  const q = state.query.toLowerCase();
  return (state.restaurants || []).filter((r) =>
    (state.cuisine === "All" || r.cuisine === state.cuisine) &&
    (!q || [r.name, r.cuisine, r.address].some((v) => String(v).toLowerCase().includes(q))));
}

function renderGrid() {
  const holder = $("gridHolder");
  if (!holder) return;
  holder.textContent = "";
  const list = filtered();
  holder.append(el("p", { class: "count", role: "status" }, list.length + (list.length === 1 ? " restaurant to explore" : " restaurants to explore")));
  if (!list.length) {
    holder.append(el("div", { class: "state" }, "No restaurants match your search. Try a different word or clear the cuisine filter."));
    return;
  }
  holder.append(el("div", { class: "grid" }, list.map((r) =>
    el("a", { class: "rcard" + (r.is_open ? "" : " is-closed"), href: "#/restaurant/" + r.id },
      banner(r),
      el("div", { class: "rbody" },
        el("div", { class: "card-heading" }, el("p", { class: "rname" }, r.name), el("span", { class: "card-arrow", "aria-hidden": "true" }, "↗")),
        el("div", { class: "rmeta" }, ratingBadge(r), el("span", {}, r.cuisine)),
        el("div", { class: "addr" }, r.address))))));
}

function renderChips() {
  const holder = $("chips");
  if (!holder) return;
  const scrollPosition = holder.scrollLeft;
  holder.textContent = "";
  const cuisines = ["All", ...new Set(state.restaurants.map((r) => r.cuisine).filter(Boolean))].sort((a, b) =>
    a === "All" ? -1 : b === "All" ? 1 : a.localeCompare(b));
  cuisines.forEach((c) => {
    const chip = el("button", { class: "chip", type: "button", "aria-pressed": String(state.cuisine === c) },
      el("span", { class: "chip-icon", "aria-hidden": "true" }, c === "All" ? "\u{1F37D}\uFE0F" : emojiFor(c)), c === "All" ? "All cuisines" : c);
    chip.addEventListener("click", () => { state.cuisine = c; renderChips(); renderGrid(); });
    holder.append(chip);
  });
  holder.scrollLeft = scrollPosition;
}

async function showHome(viewVersion) {
  $("searchWrap").hidden = false;
  app.textContent = "";
  app.append(el("section", { class: "catalog", id: "restaurants", "aria-labelledby": "catalogTitle" },
    el("div", { class: "catalog-heading" }, el("div", {}, el("p", { class: "eyebrow" }, "So many ways to satisfy a craving"),
      el("h2", { id: "catalogTitle", tabIndex: -1 }, "Find something delicious.")), el("span", { class: "catalog-accent", "aria-hidden": "true" }, "Made for your appetite ↗")),
    el("div", { class: "chips", id: "chips", role: "group", "aria-label": "Filter by cuisine" }), el("div", { id: "gridHolder" })));
  $("gridHolder").append(el("div", { class: "grid" }, [1, 2, 3, 4, 5, 6].map(() => el("div", { class: "skeleton" }))));
  try {
    if (!state.restaurants) await loadRestaurants();
    if (viewVersion !== routeVersion) return;
    renderChips();
    renderGrid();
  } catch (err) {
    if (viewVersion !== routeVersion || err.code === "SESSION_CHANGED") return;
    $("gridHolder").textContent = "";
    $("gridHolder").append(el("div", { class: "state error" },
      "Could not load restaurants (" + err.message + "). Check that the backend is running and the API address below is right."));
  }
}

// ---------- Restaurant page ----------
async function showDetail(id, viewVersion) {
  $("searchWrap").hidden = true;
  app.textContent = "";
  app.append(el("a", { class: "back", href: "#/" }, "\u2190 All restaurants"), el("div", { class: "skeleton", style: "height:300px" }));
  let r;
  try {
    r = await request("/restaurants/" + id);
    if (viewVersion !== routeVersion) return;
  } catch (err) {
    if (viewVersion !== routeVersion || err.code === "SESSION_CHANGED") return;
    app.textContent = "";
    app.append(el("a", { class: "back", href: "#/" }, "\u2190 All restaurants"),
      el("div", { class: "state error" }, err.message.startsWith("404")
        ? "That restaurant doesn't exist. It may have been removed."
        : "Could not load this restaurant (" + err.message + ")."));
    return;
  }
  const menuHolder = el("div", {}, el("div", { class: "skeleton", style: "height:100px" }));
  const addItemBtn = el("button", { class: "btn", type: "button", id: "openMenuCreate" }, "Add menu item");
  addItemBtn.hidden = !isManager();
  addItemBtn.addEventListener("click", () => openMenuDialog(r.id));
  app.textContent = "";
  app.append(
    el("a", { class: "back", href: "#/" }, "\u2190 All restaurants"),
    el("section", { class: "hero" },
      banner(r),
      el("div", { class: "hero-body" },
        el("h1", {}, r.name),
        el("div", { class: "facts" },
          ratingBadge(r, " rating"),
          el("span", {}, r.cuisine),
          el("span", {}, r.address),
          el("span", {}, r.is_open ? "Open now" : "Closed right now")))),
    el("div", { class: "section-head" }, el("div", {}, el("h2", {}, "Menu"), el("p", { class: "menu-image-note" }, "Illustrative food photography")), addItemBtn),
    menuHolder);
  try {
    const items = await request("/restaurants/" + id + "/menu");
    if (viewVersion !== routeVersion) return;
    menuCategories = [...new Set(items.map((m) => m.category).filter(Boolean))];
    menuHolder.textContent = "";
    if (!items.length) {
      menuHolder.append(el("div", { class: "state" }, "This restaurant hasn't added any menu items yet."));
      return;
    }
    if (items.some((item) => /^Demo menu:/i.test(String(item.description || "").trim()))) {
      menuHolder.append(el("p", { class: "demo-note" }, el("span", { class: "demo-pill" }, "Demo menu"), "Sample dishes and prices for this project."));
    }
    const groups = {};
    items.forEach((m) => { (groups[m.category || ""] = groups[m.category || ""] || []).push(m); });
    Object.entries(groups).forEach(([cat, group]) => {
      if (cat) menuHolder.append(el("h2", {}, cat));
      menuHolder.append(el("div", { class: "menu-grid" }, group.map((m) =>
        el("div", { class: "mitem" + (m.is_available ? "" : " unavailable") },
          el("div", { class: "menu-copy" },
            el("p", { class: "mname" }, m.name, m.is_available ? "" : el("span", { class: "tag" }, "Unavailable")),
            menuDescription(m) ? el("p", { class: "mdesc" }, menuDescription(m)) : ""),
          el("div", { class: "menu-photo" }, foodPhoto(m.name, m.category, r.cuisine)),
          el("div", { class: "mprice" }, money(m.price)), shopping.menuActions(m, r.is_open)))));
    });
  } catch (err) {
    if (viewVersion !== routeVersion || err.code === "SESSION_CHANGED") return;
    menuHolder.textContent = "";
    menuHolder.append(el("div", { class: "state error" }, "Could not load the menu (" + err.message + ")."));
  }
}

// ---------- Routing ----------
const accountViews = createAccountViews({ app, el, client, onSignedIn: () => { location.hash = "#/"; } });
const shopping = createShopping({ app, el, request, money, getUser: () => client.snapshot().user,
  navigate: hash => { location.hash = hash; }, toast });
function route() {
  const viewVersion = ++routeVersion;
  const m = location.hash.match(/^#\/restaurant\/(\d+)/);
  const order = location.hash.match(/^#\/orders\/(\d+)$/);
  $("searchWrap").hidden = !onHome();
  $("homeHero").hidden = !onHome();
  document.body.classList.toggle("home-route", onHome());
  updateCreateButton();
  if ((location.hash === "#/signin" || location.hash === "#/register") && client.snapshot().user) {
    location.replace("#/account");
    return;
  }
  if (location.hash === "#/signin") accountViews.showAuth("signin");
  else if (location.hash === "#/register") accountViews.showAuth("register");
  else if (location.hash === "#/account") accountViews.showAccount();
  else if (location.hash === "#/cart") shopping.showCart();
  else if (location.hash === "#/orders") shopping.showOrders();
  else if (order) shopping.showOrder(order[1]);
  else if (m) showDetail(m[1], viewVersion);
  else showHome(viewVersion);
  window.scrollTo(0, 0);
}
window.addEventListener("hashchange", route);

// ---------- Search ----------
$("search").addEventListener("input", (e) => { state.query = e.target.value; renderGrid(); });
function browseRestaurants() {
  $("restaurants")?.scrollIntoView({ behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start" });
  $("catalogTitle")?.focus({ preventScroll: true });
}
$("searchWrap").addEventListener("submit", (event) => { event.preventDefault(); browseRestaurants(); });
$("browseRestaurants").addEventListener("click", browseRestaurants);
$("apiBase").addEventListener("change", () => {
  try {
    client.setBaseURL($("apiBase").value);
    $("apiBase").value = client.snapshot().baseURL;
    $("apiMsg").textContent = "";
    state.restaurants = null;
    route();
  } catch (err) {
    $("apiMsg").textContent = err.message;
    $("apiBase").value = client.snapshot().baseURL;
  }
});

// ---------- Create restaurant ----------
const dialog = $("createDialog");
$("openCreate").addEventListener("click", () => {
  if (client.snapshot().user?.role !== "manager") return;
  $("formMsg").textContent = "";
  dialog.showModal();
});
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

// ---------- Add menu item ----------
const menuDialog = $("menuDialog");
let menuRestaurantId = null;
let menuCategories = [];

function openMenuDialog(restaurantId) {
  if (!isManager()) return;
  menuRestaurantId = restaurantId;
  $("menuForm").reset();
  $("menuMsg").className = "form-msg";
  $("menuMsg").textContent = "";
  // Suggest the restaurant's existing categories so new items join the right group
  const list = $("menuCategories");
  list.textContent = "";
  menuCategories.forEach((c) => list.append(el("option", { value: c })));
  menuDialog.showModal();
}
$("cancelMenu").addEventListener("click", () => menuDialog.close());

$("menuForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const msg = $("menuMsg");
  msg.className = "form-msg"; msg.textContent = "Saving...";
  const f = e.target.elements;
  const body = {
    name: f.name.value.trim(),
    category: f.category.value.trim(),
    price: parseFloat(f.price.value),
    description: f.description.value.trim(),
    is_available: f.is_available.checked,
  };
  try {
    const created = await request("/restaurants/" + menuRestaurantId + "/menu", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    menuDialog.close();
    toast("Added " + created.name + " to the menu");
    route();
  } catch (err) {
    msg.className = "form-msg error";
    msg.textContent = "Could not add the menu item: " + err.message;
  }
});

let previousUserId = null;
let previousLoading = false;
client.subscribe(({ user, loading, error }) => {
  updateCreateButton();
  if ($("openMenuCreate")) $("openMenuCreate").hidden = !user || user.role !== "manager";
  if (!user && dialog.open) dialog.close();
  if ((!user || user.role !== "manager") && menuDialog.open) menuDialog.close();
  const nav = $("sessionNav");
  nav.textContent = "";
  if (user) {
    const signout = el("button", { class: "btn ghost", type: "button" }, "Sign out");
    signout.addEventListener("click", () => {
      client.logout();
      if (location.hash === "#/") route(); else location.hash = "#/";
      toast("Signed out");
    });
    nav.append(el("a", { class: "account-link", href: "#/cart" }, "Cart"),
      el("a", { class: "account-link", href: "#/orders" }, "My orders"),
      el("a", { class: "account-link", href: "#/account" }, user.name), signout);
  } else if (!loading) {
    nav.append(el("a", { class: "btn ghost", href: "#/signin" }, "Sign in"),
      el("a", { class: "btn", href: "#/register" }, "Register"));
  }
  $("sessionStatus").textContent = loading ? "Checking your sign-in…" : error;
  const identityChanged = previousUserId !== (user?.id ?? null);
  const restored = previousLoading && !loading;
  previousUserId = user?.id ?? null;
  previousLoading = loading;
  const sessionView = /^(#\/(account|cart|orders)(\/|$)|#\/restaurant\/)/.test(location.hash);
  if (started && sessionView && (identityChanged || restored)) route();
});

app.append(el("div", { class: "state", role: "status" }, "Loading Food Delivery…"));
client.restore().catch(() => { /* The session status contains the API error. */ }).finally(() => {
  started = true;
  route();
});
