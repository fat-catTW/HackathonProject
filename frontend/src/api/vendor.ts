import type {
  VendorAction,
  VendorActionResult,
  VendorContactReveal,
  VendorDemoAccount,
  VendorLoginResult,
  VendorProfile,
  VendorRequestDetail,
  VendorRequestList,
  VendorScope,
} from "../types/vendor";
import { api, vendorApi } from "./client";

export function vendorLogin(email: string, password: string) {
  // 尚未登入，用不帶 token 的 api()。
  return api<VendorLoginResult>("/api/vendor/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function fetchVendorDemoAccounts() {
  return api<{ accounts: VendorDemoAccount[] }>("/api/vendor/demo-accounts");
}

export function fetchVendorProfile() {
  return vendorApi<VendorProfile>("/api/vendor/me");
}

export function listVendorRequests(scope: VendorScope) {
  return vendorApi<VendorRequestList>(`/api/vendor/requests?scope=${scope}`);
}

export function getVendorRequest(requestId: string) {
  return vendorApi<VendorRequestDetail>(`/api/vendor/requests/${requestId}`);
}

/**
 * 解密顯示完整聯絡資訊。用 POST 是因為它有副作用：後端每次呼叫都會寫一筆存取
 * 紀錄，回傳的 contact_access_log 已經含這一筆。
 */
export function revealVendorContact(requestId: string) {
  return vendorApi<VendorContactReveal>(`/api/vendor/requests/${requestId}/contact`, {
    method: "POST",
  });
}

/**
 * 接單／拒單。version 是畫面上這筆案件的版本，後端比對不符會回 409
 * （REQUEST_STATUS_CONFLICT／REQUEST_VERSION_CONFLICT），避免重複或蓋掉別人的操作。
 */
export function actOnVendorRequest(
  requestId: string,
  action: VendorAction,
  version: number,
) {
  return vendorApi<VendorActionResult>(`/api/vendor/requests/${requestId}/${action}`, {
    method: "POST",
    body: JSON.stringify({ version }),
  });
}
