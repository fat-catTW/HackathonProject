import type {
  DeliveryOrder,
  DeliveryPayload,
  DeliveryStore,
  DeliveryStoreDetail,
  DeliverySubmitResult,
} from "../types/delivery";
import { api } from "./client";

export async function listDeliveryStores(): Promise<DeliveryStore[]> {
  const result = await api<{ stores: DeliveryStore[] }>("/api/delivery/stores");
  return result.stores;
}

export function getDeliveryStore(storeId: string): Promise<DeliveryStoreDetail> {
  return api<DeliveryStoreDetail>(`/api/delivery/stores/${storeId}`);
}

export function submitDeliveryOrder(payload: DeliveryPayload): Promise<DeliverySubmitResult> {
  return api<DeliverySubmitResult>("/api/delivery/submit", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getDeliveryOrder(requestId: string): Promise<DeliveryOrder> {
  return api<DeliveryOrder>(`/api/delivery/orders/${requestId}`);
}

export function cancelDeliveryOrder(requestId: string, reason = "USER_CANCEL"): Promise<{ success: boolean }> {
  return api<{ success: boolean }>(`/api/delivery/orders/${requestId}/cancel`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}
