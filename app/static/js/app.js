/* OrderFlow frontend helpers. Talks to the JSON API using a JWT stored in
 * localStorage. No framework -- plain fetch + DOM, kept intentionally
 * simple per the project spec ("do not make the UI unnecessarily
 * complicated"). */

const OrderFlow = (() => {
  const TOKEN_KEY = "orderflow_token";
  const USER_KEY = "orderflow_user";

  function getToken() {
    return localStorage.getItem(TOKEN_KEY);
  }

  function getUser() {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  }

  function setSession(token, user) {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  }

  function clearSession() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  }

  function isLoggedIn() {
    return !!getToken();
  }

  function isAdmin() {
    const user = getUser();
    return !!user && user.role === "ADMIN";
  }

  async function api(path, { method = "GET", body = null, auth = true } = {}) {
    const headers = { "Content-Type": "application/json" };
    if (auth && getToken()) {
      headers["Authorization"] = `Bearer ${getToken()}`;
    }
    const res = await fetch(path, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });

    if (res.status === 401) {
      clearSession();
      window.location.href = "/login";
      throw new Error("Session expired");
    }

    if (res.status === 204) return null;

    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const detail = Array.isArray(data.detail)
        ? data.detail.map((d) => d.msg || JSON.stringify(d)).join(", ")
        : data.detail || "Request failed";
      throw new Error(detail);
    }
    return data;
  }

  function requireAuth() {
    if (!isLoggedIn()) window.location.href = "/login";
  }

  function requireAdmin() {
    requireAuth();
    if (!isAdmin()) window.location.href = "/dashboard";
  }

  function money(value) {
    const num = typeof value === "string" ? parseFloat(value) : value;
    return `$${num.toFixed(2)}`;
  }

  function badge(status) {
    return `<span class="badge ${status}">${status}</span>`;
  }

  function formatDate(iso) {
    return new Date(iso).toLocaleString();
  }

  function renderNav(activePath) {
    const nav = document.getElementById("orderflow-nav");
    if (!nav) return;
    const user = getUser();

    const links = [];
    if (user) {
      links.push(["/dashboard", "Dashboard"]);
      links.push(["/products", "Products"]);
      links.push(["/orders", "My Orders"]);
      links.push(["/profile", "Profile"]);
      if (user.role === "ADMIN") {
        links.push(["/admin", "Admin"]);
      }
    }

    const linkHtml = links
      .map(([href, label]) => {
        const isActive = activePath === href || (href !== "/" && activePath.startsWith(href));
        return `<a href="${href}" class="${isActive ? "active" : ""}">${label}</a>`;
      })
      .join("");

    const rightHtml = user
      ? `<span class="muted" style="font-size:0.85rem;">${user.name}</span>
         <a href="#" id="orderflow-logout">Log out</a>`
      : `<a href="/login">Login</a><a class="btn small" href="/register">Sign up</a>`;

    nav.innerHTML = `
      <a class="brand" href="/">Order<span>Flow</span></a>
      <div class="nav-links">${linkHtml}${rightHtml}</div>
    `;

    const logoutLink = document.getElementById("orderflow-logout");
    if (logoutLink) {
      logoutLink.addEventListener("click", (e) => {
        e.preventDefault();
        clearSession();
        window.location.href = "/login";
      });
    }
  }

  function showAlert(container, message, type = "error") {
    container.innerHTML = `<div class="alert ${type}">${message}</div>`;
  }

  return {
    api,
    getToken,
    getUser,
    setSession,
    clearSession,
    isLoggedIn,
    isAdmin,
    requireAuth,
    requireAdmin,
    money,
    badge,
    formatDate,
    renderNav,
    showAlert,
  };
})();
