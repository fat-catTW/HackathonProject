const TOKEN_KEY = "assistant_token";
const NAME_KEY = "assistant_name";
// 廠商後台的登入狀態獨立存放，讓同一台電腦可以同時開住戶端與廠商後台做 Demo。
const VENDOR_TOKEN_KEY = "assistant_vendor_token";
const VENDOR_NAME_KEY = "assistant_vendor_name";
const VENDOR_ID_KEY = "assistant_vendor_id";
const API_BASE_URL = "";

export function getToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY);
}

export function setAuth(token: string, name: string) {
  sessionStorage.setItem(TOKEN_KEY, token);
  sessionStorage.setItem(NAME_KEY, name);
}

export function clearAuth() {
  sessionStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(NAME_KEY);
}

export function getUserName(): string {
  return sessionStorage.getItem(NAME_KEY) ?? "";
}

export function getVendorToken(): string | null {
  return localStorage.getItem(VENDOR_TOKEN_KEY);
}

export function setVendorAuth(token: string, name: string, vendorId: number) {
  localStorage.setItem(VENDOR_TOKEN_KEY, token);
  localStorage.setItem(VENDOR_NAME_KEY, name);
  localStorage.setItem(VENDOR_ID_KEY, String(vendorId));
}

export function clearVendorAuth() {
  localStorage.removeItem(VENDOR_TOKEN_KEY);
  localStorage.removeItem(VENDOR_NAME_KEY);
  localStorage.removeItem(VENDOR_ID_KEY);
}

export function getVendorName(): string {
  return localStorage.getItem(VENDOR_NAME_KEY) ?? "";
}

export function getVendorId(): number | null {
  const raw = localStorage.getItem(VENDOR_ID_KEY);
  return raw === null ? null : Number(raw);
}

export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public details?: {
      missingFields?: string[];
    },
    /** 錯誤本體其餘欄位；409 衝突會帶回案件現況，畫面可直接更新。 */
    public data: Record<string, unknown> = {},
  ) {
    super(message);
  }
}

async function request<T>(
  path: string,
  init: RequestInit,
  token: string | null,
  onUnauthorized: () => void,
): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
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
    let missingFields: string[] | undefined;
    let data: Record<string, unknown> = {};
    try {
      const body = await res.json();
      const err = body?.detail?.error ?? body?.error;
      if (err) {
        code = err.code ?? code;
        message = err.message ?? message;
        missingFields = Array.isArray(err.missing_fields) ? err.missing_fields : undefined;
        data = err;
      }
    } catch {
      /* 保留預設錯誤 */
    }
    if (res.status === 401) onUnauthorized();
    throw new ApiError(code, message, { missingFields }, data);
  }
  return res.json() as Promise<T>;
}

export function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  return request<T>(path, init, getToken(), clearAuth);
}

export function vendorApi<T>(path: string, init: RequestInit = {}): Promise<T> {
  return request<T>(path, init, getVendorToken(), clearVendorAuth);
}
