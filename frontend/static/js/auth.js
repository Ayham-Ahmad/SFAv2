"use strict";
const Auth = (() => {
  const TOKEN_KEY = "sfa_token";
  const USER_KEY = "sfa_user";
  const getUser = () => {
    try {
      const userStr = localStorage.getItem(USER_KEY);
      return userStr ? JSON.parse(userStr) : null;
    } catch {
      return null;
    }
  };
  const getToken = () => localStorage.getItem(TOKEN_KEY);
  const save = (token, user) => {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  };
  const logout = () => {
    API.post("/logout").catch(() => {});
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    window.location.href = "/login";
  };
  const login = async (username, password) => {
    const form = new URLSearchParams();
    form.append("username", username);
    form.append("password", password);
    const res = await fetch("/token", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: form,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || "Login failed");
    save(data.access_token, data.user);
    return data.user;
  };
  const requireAuth = () => {
    if (!getToken()) {
      window.location.href = "/login";
      return false;
    }
    return true;
  };
  const requireRole = (...roles) => {
    const user = getUser();
    if (!user || !roles.includes(user.role)) {
      window.location.href = "/analytics";
      return false;
    }
    return true;
  };
  const hydrateSidebar = () => {
    const user = getUser();
    if (!user) return;
    const nameEl = document.getElementById("sidebar-username");
    const roleEl = document.getElementById("sidebar-role");
    const initEl = document.getElementById("sidebar-avatar-init");
    if (nameEl) nameEl.textContent = user.username?.replace(/_/g, " ") || "";
    if (roleEl) roleEl.textContent = user.role?.replace(/_/g, " ") || "";
    if (initEl) initEl.textContent = (user.username?.[0] || "U").toUpperCase();
  };
  return {
    login,
    logout,
    save,
    getUser,
    getToken,
    requireAuth,
    requireRole,
    hydrateSidebar,
  };
})();
