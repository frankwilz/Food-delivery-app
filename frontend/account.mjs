export function createAccountViews({ app, el, client, onSignedIn }) {
  function field(label, name, { type = "text", value = "", autocomplete, maxLength, minLength } = {}) {
    return el("label", {}, label, el("input", {
      class: "field", name, type, value, required: true, autocomplete,
      ...(maxLength ? { maxLength } : {}), ...(minLength ? { minLength } : {}),
    }));
  }

  function showAuth(mode = "signin") {
    const registering = mode === "register";
    app.textContent = "";
    const message = el("div", { class: "form-msg", role: "status", "aria-live": "polite" });
    const fields = el("fieldset", {},
      registering ? field("Full name", "name", { autocomplete: "name", maxLength: 100 }) : [],
      field("Email", "email", { type: "email", autocomplete: "username", maxLength: 254 }),
      field("Password", "password", { type: "password", autocomplete: registering ? "new-password" : "current-password", minLength: registering ? 8 : 1, maxLength: 128 }),
      registering ? field("Delivery address", "delivery_address", { autocomplete: "street-address", maxLength: 200 }) : [],
      el("button", { class: "btn", type: "submit" }, registering ? "Create account" : "Sign in"));
    const form = el("form", {}, fields, message);
    app.append(el("a", { class: "back", href: "#/" }, "← All restaurants"),
      el("section", { class: "account-card" },
        el("h1", {}, registering ? "Create your account" : "Welcome back"),
        el("p", { class: "muted" }, registering ? "Set up your account and delivery address." : "Sign in to manage your account and order food."),
        form,
        el("p", {}, registering ? "Already registered? " : "New here? ", el("a", { class: "text-link", href: registering ? "#/signin" : "#/register" }, registering ? "Sign in" : "Create an account"))));
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const f = form.elements;
      const values = { email: f.email.value.trim(), password: f.password.value };
      if (registering) Object.assign(values, { name: f.name.value.trim(), delivery_address: f.delivery_address.value.trim() });
      f.password.value = "";
      fields.disabled = true;
      form.setAttribute("aria-busy", "true");
      message.className = "form-msg";
      message.textContent = registering ? "Creating your account…" : "Signing in…";
      try {
        if (registering) await client.register(values); else await client.login(values);
        if (form.isConnected) onSignedIn();
      } catch (err) {
        if (!form.isConnected || err.code === "SESSION_CHANGED") return;
        message.className = "form-msg error";
        message.textContent = err.message;
      } finally {
        fields.disabled = false;
        form.removeAttribute("aria-busy");
      }
    });
  }

  function showAccount() {
    const { user, loading, error } = client.snapshot();
    let savedUser = user;
    app.textContent = "";
    if (loading) {
      app.append(el("div", { class: "state", role: "status" }, "Loading your account…"));
      return;
    }
    if (!user) {
      app.append(el("h1", {}, "Your account"), el("div", { class: "state" },
        error ? `${error}. ` : "Sign in to view and update your account. ",
        el("a", { class: "text-link", href: "#/signin" }, "Sign in")));
      return;
    }
    const message = el("div", { class: "form-msg", role: "status", "aria-live": "polite" });
    const fields = el("fieldset", {},
      field("Full name", "name", { value: user.name, autocomplete: "name", maxLength: 100 }),
      field("Email", "email", { type: "email", value: user.email, autocomplete: "email", maxLength: 254 }),
      field("Delivery address", "delivery_address", { value: user.delivery_address, autocomplete: "street-address", maxLength: 200 }),
      el("button", { class: "btn", type: "submit" }, "Save changes"));
    const form = el("form", {}, fields, message);
    app.append(el("a", { class: "back", href: "#/" }, "← All restaurants"),
      el("section", { class: "account-card" }, el("h1", {}, "Your account"),
        el("p", { class: "muted" }, "Update your details and where your food is delivered."), form));
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const changes = {};
      for (const name of ["name", "email", "delivery_address"]) {
        const value = form.elements[name].value.trim();
        if (value !== savedUser[name]) changes[name] = value;
      }
      if (!Object.keys(changes).length) { message.textContent = "Your details are already up to date."; return; }
      fields.disabled = true;
      form.setAttribute("aria-busy", "true");
      message.className = "form-msg";
      message.textContent = "Saving your account…";
      try {
        const updated = await client.updateAccount(changes);
        if (!form.isConnected) return;
        savedUser = updated;
        message.textContent = "Your account has been updated.";
      } catch (err) {
        if (!form.isConnected || err.code === "SESSION_CHANGED") return;
        message.className = "form-msg error";
        message.textContent = err.message;
      } finally {
        fields.disabled = false;
        form.removeAttribute("aria-busy");
      }
    });
  }
  return { showAuth, showAccount };
}
