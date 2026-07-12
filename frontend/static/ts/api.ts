declare const Auth: {
  logout(): void;
};

interface ApiResponse<T = any> {
  ok: boolean;
  status: number;
  data: T;
}

interface RequestOptions extends RequestInit {
  [key: string]: any;
}

interface ApiMethods {
  get<T = any>(path: string): Promise<ApiResponse<T> | null>;
  post<T = any>(path: string, body?: any): Promise<ApiResponse<T> | null>;
  patch<T = any>(path: string, body?: any): Promise<ApiResponse<T> | null>;
  delete<T = any>(path: string): Promise<ApiResponse<T> | null>;
  postForm(path: string, formData: FormData): Promise<ApiResponse | null>;
}

const API = (() => {
  const base = "";

  const getToken = (): string | null => localStorage.getItem("sfa_token");

  const request = async <T = any>(
    method: string,
    path: string,
    body?: any,
    opts: RequestOptions = {},
  ): Promise<ApiResponse<T> | null> => {
    const headers: HeadersInit = { "Content-Type": "application/json" };
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const fetchOpts: RequestInit = {
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
    get: <T = any>(path: string) => request<T>("GET", path),
    post: <T = any>(path: string, body?: any) => request<T>("POST", path, body),
    patch: <T = any>(path: string, body?: any) =>
      request<T>("PATCH", path, body),
    delete: <T = any>(path: string) => request<T>("DELETE", path),
    postForm: async (
      path: string,
      formData: FormData,
    ): Promise<ApiResponse | null> => {
      const headers: HeadersInit = {};
      const token = getToken();
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const fetchOpts: RequestInit = {
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
  } as ApiMethods;
})();
