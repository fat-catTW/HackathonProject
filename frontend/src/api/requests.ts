import type { RequestDetail, RequestListItem } from "../types/request";
import { api } from "./client";

export function listRequests() {
  return api<{ items: RequestListItem[] }>("/api/requests");
}

export function getRequest(requestId: string) {
  return api<RequestDetail>(`/api/requests/${requestId}`);
}

export function cancelRequest(requestId: string) {
  return api<{ success: boolean; status: string }>(
    `/api/requests/${requestId}/cancel`,
    { method: "POST" },
  );
}

export function simulateStatus(requestId: string, next: string) {
  return api<{ success: boolean; status: string }>(
    `/api/requests/${requestId}/simulate/${next}`,
    { method: "POST" },
  );
}
