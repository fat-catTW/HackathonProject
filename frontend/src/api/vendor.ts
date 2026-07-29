import type {
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
