import { api } from "./client";

export interface ServiceRequestCreateResult {
  success: boolean;
  request_id: string;
  status: string;
  message: string;
}

export function createServiceRequest(
  serviceId: string,
  payload: Record<string, string | number>,
) {
  return api<ServiceRequestCreateResult>(`/api/services/${serviceId}/requests`, {
    method: "POST",
    body: JSON.stringify({ payload }),
  });
}
