/* api.js — thin fetch wrapper, reads JWT from localStorage */
const API = (() => {
  const base = '';

  function getToken() { return localStorage.getItem('sfa_token'); }

  async function request(method, path, body, opts = {}) {
    const headers = { 'Content-Type': 'application/json' };
    const token = getToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(base + path, {
      method, headers,
      body: body ? JSON.stringify(body) : undefined,
      ...opts,
    });
    if (res.status === 401) { Auth.logout(); return null; }
    const data = await res.json().catch(() => ({}));
    return { ok: res.ok, status: res.status, data };
  }

  return {
    get:    (path)        => request('GET',    path),
    post:   (path, body)  => request('POST',   path, body),
    patch:  (path, body)  => request('PATCH',  path, body),
    delete: (path)        => request('DELETE', path),
    postForm: async (path, formData) => {
      const headers = {};
      const token = getToken();
      if (token) headers['Authorization'] = `Bearer ${token}`;
      const res = await fetch(base + path, { method: 'POST', headers, body: formData });
      if (res.status === 401) { Auth.logout(); return null; }
      const data = await res.json().catch(() => ({}));
      return { ok: res.ok, status: res.status, data };
    }
  };
})();
