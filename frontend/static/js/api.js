"use strict";
const API = (() => {
  const base = "";
  const getToken = () => localStorage.getItem("sfa_token");
  const request = async (method, path, body, opts = {}) => {
    const headers = { "Content-Type": "application/json" };
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
    const fetchOpts = {
      method,
      headers,
      body: body ? JSON.stringify(body) : null,
      ...opts,
    };
    const res = await fetch(base + path, fetchOpts);
    if (res.status === 401) {
      Auth.logout();
      return null;
    }
    const data = await res.json().catch(() => ({}));
    return { ok: res.ok, status: res.status, data };
  };
  return {
    get: (path) => request("GET", path),
    post: (path, body) => request("POST", path, body),
    patch: (path, body) => request("PATCH", path, body),
    delete: (path) => request("DELETE", path),
    postForm: async (path, formData) => {
      const headers = {};
      const token = getToken();
      if (token) headers["Authorization"] = `Bearer ${token}`;
      const fetchOpts = {
        method: "POST",
        headers,
        body: formData,
      };
      const res = await fetch(base + path, fetchOpts);
      if (res.status === 401) {
        Auth.logout();
        return null;
      }
      const data = await res.json().catch(() => ({}));
      return { ok: res.ok, status: res.status, data };
    },
  };
})();
