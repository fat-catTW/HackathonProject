import type {
  VendorAction,
  VendorActionResult,
  VendorContactReveal,
  VendorRequestDetail,
  VendorRequestList,
  VendorScope,
} from "../types/vendor";
import { vendorApi } from "./client";

export function listVendorDeliveryOrders(scope: VendorScope) {
  return vendorApi<VendorRequestList>(`/api/vendor/delivery-orders?scope=${scope}`);
}

export function getVendorDeliveryOrder(requestId: string) {
  return vendorApi<VendorRequestDetail>(`/api/vendor/delivery-orders/${requestId}`);
}

export function actOnVendorDeliveryOrder(requestId: string, action: VendorAction, version: number) {
  return vendorApi<VendorActionResult>(`/api/vendor/delivery-orders/${requestId}/${action}`, {
    method: "POST",
    body: JSON.stringify({ version }),
  });
}

/**
 * 解密顯示完整聯絡資訊。用 POST 是因為它有副作用：後端每次呼叫都會寫一筆存取
 * 紀錄，回傳的 contact_access_log 已經含這一筆。
 */
export function revealVendorDeliveryContact(requestId: string) {
  return vendorApi<VendorContactReveal>(`/api/vendor/delivery-orders/${requestId}/contact`, {
    method: "POST",
  });
}
