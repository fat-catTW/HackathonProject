import type { HealthProduct, HealthRecommendationResult } from "../types/health";
import { api } from "./client";

export function recommendProducts(query: string) {
  return api<HealthRecommendationResult>("/api/health/recommendations", {
    method: "POST",
    body: JSON.stringify({ query }),
  });
}

export function getProduct(productId: string) {
  return api<HealthProduct>(`/api/health/products/${encodeURIComponent(productId)}`);
}
