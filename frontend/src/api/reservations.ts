import type { ReservationOrder, ReservationPayload, ReservationSubmitResult, RestaurantInfo } from "../types/reservation";
import { api } from "./client";

export async function listRestaurants(): Promise<RestaurantInfo[]> {
  const result = await api<{ restaurants: RestaurantInfo[] }>("/api/restaurants");
  return result.restaurants;
}

export function getRestaurant(id: string) {
  return api<RestaurantInfo>(`/api/restaurants/${id}`);
}

export function submitReservation(payload: ReservationPayload) {
  return api<ReservationSubmitResult>("/api/reservations/submit", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getReservation(requestId: string) {
  return api<ReservationOrder>(`/api/reservations/${requestId}`);
}

export function cancelReservation(requestId: string) {
  return api<{ success: boolean }>(`/api/reservations/${requestId}/cancel`, {
    method: "POST",
  });
}
