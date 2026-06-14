/* auth.js — login, logout, token storage, redirect guards */
const Auth = (() => {
  const TOKEN_KEY = 'sfa_token';
  const USER_KEY  = 'sfa_user';

  function getUser() {
    try { return JSON.parse(localStorage.getItem(USER_KEY)); } catch { return null; }
  }
  function getToken() { return localStorage.getItem(TOKEN_KEY); }

  function save(token, user) {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  }

  function logout() {
    API.post('/logout').catch(() => {});
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    window.location.href = '/login';
  }

  async function login(username, password) {
    const form = new URLSearchParams();
    form.append('username', username);
    form.append('password', password);
    const res = await fetch('/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: form,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || 'Login failed');
    save(data.access_token, data.user);
    return data.user;
  }

  function requireAuth() {
    if (!getToken()) { window.location.href = '/login'; return false; }
    return true;
  }

  function requireRole(...roles) {
    const user = getUser();
    if (!user || !roles.includes(user.role)) {
      window.location.href = '/analytics';
      return false;
    }
    return true;
  }

  /* Populate sidebar user pill on page load */
  function hydrateSidebar() {
    const user = getUser();
    if (!user) return;
    const name = document.getElementById('sidebar-username');
    const role = document.getElementById('sidebar-role');
    const initEl = document.getElementById('sidebar-avatar-init');
    if (name) name.textContent = user.username?.replace(/_/g, ' ') || '';
    if (role) role.textContent = user.role?.replace(/_/g, ' ') || '';
    if (initEl) initEl.textContent = (user.username?.[0] || 'U').toUpperCase();
  }

  return { login, logout, save, getUser, getToken, requireAuth, requireRole, hydrateSidebar };
})();
