import { api } from "./client";
import type {
  ShopCategory,
  ShopCompareGroup,
  ShopOrder,
  ShopPointsBalance,
  ShopProduct,
  ShopStore,
  ShopSubmitPayload,
  ShopSubmitResult,
} from "../types/shop";

export function listShopStores(): Promise<{ stores: ShopStore[] }> {
  return api("/api/shop/stores");
}

export function listShopCategories(): Promise<{ categories: ShopCategory[] }> {
  return api("/api/shop/categories");
}

export function listShopProducts(categoryId?: string): Promise<{ products: ShopProduct[] }> {
  const query = categoryId ? `?category_id=${encodeURIComponent(categoryId)}` : "";
  return api(`/api/shop/products${query}`);
}

export function getShopCompareGroup(groupId: string): Promise<ShopCompareGroup> {
  return api(`/api/shop/compare/${encodeURIComponent(groupId)}`);
}

export function getShopProduct(productId: string): Promise<ShopProduct> {
  return api(`/api/shop/products/${encodeURIComponent(productId)}`);
}

export function getShopPoints(): Promise<ShopPointsBalance> {
  return api("/api/shop/points");
}

export function submitShopOrder(payload: ShopSubmitPayload): Promise<ShopSubmitResult> {
  return api("/api/shop/submit", { method: "POST", body: JSON.stringify(payload) });
}

export function getShopOrder(requestId: string): Promise<ShopOrder> {
  return api(`/api/shop/orders/${encodeURIComponent(requestId)}`);
}

export function cancelShopOrder(requestId: string, reason = "USER_CANCEL"): Promise<{ success: boolean }> {
  return api(`/api/shop/orders/${encodeURIComponent(requestId)}/cancel`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}

export function simulateShopOrderProgress(requestId: string): Promise<{ success: boolean; status: string }> {
  return api(`/api/shop/orders/${encodeURIComponent(requestId)}/simulate`, { method: "POST" });
}
