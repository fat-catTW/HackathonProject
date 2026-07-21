const TOKEN_KEY = "assistant_token";
const NAME_KEY = "assistant_name";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setAuth(token: string, name: string) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(NAME_KEY, name);
}

export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(NAME_KEY);
}

export function getUserName(): string {
  return localStorage.getItem(NAME_KEY) ?? "";
}

export class ApiError extends Error {
  constructor(public code: string, message: string) {
    super(message);
  }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  const res = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init.headers,
    },
  });
  if (!res.ok) {
    let code = "INTERNAL_ERROR";
    let message = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      const err = body?.detail?.error ?? body?.error;
      if (err) {
        code = err.code ?? code;
        message = err.message ?? message;
      }
    } catch {
      /* 保留預設錯誤 */
    }
    if (res.status === 401) clearAuth();
    throw new ApiError(code, message);
  }
  return res.json() as Promise<T>;
}
