import type { CollectedFieldValue } from "../utils/fieldLabels";

export type RequestStatus =
  | "DRAFT"
  | "AWAITING_USER_CONFIRMATION"
  | "SUBMITTED"
  | "AWAITING_QUOTE"
  | "PENDING_PROVIDER"
  | "CONFIRMED"
  | "IN_PROGRESS"
  | "COMPLETED"
  | "CANCELLED"
  | "REJECTED"
  | "FAILED";

export interface RequestListItem {
  request_id: string;
  service_name: string;
  status: RequestStatus;
  status_label: string;
  created_at: string;
  updated_at: string;
}

export interface ChatEvent {
  role: "USER" | "ASSISTANT";
  content: string;
  redirectPath?: string;
  taskCards?: { service_id: string; service_name: string }[];
  shareText?: string;
}

export interface RequestDetail extends RequestListItem {
  session_id: string | null;
  service_id: string;
  form_data: Record<string, CollectedFieldValue>;
  events: ChatEvent[];
  estimated_fee_min?: number;
  estimated_fee_max?: number;
}

export interface ChatResponse {
  session_id: string;
  reply: string;
  service_id: string | null;
  service_name: string | null;
  collected_fields: Record<string, CollectedFieldValue>;
  missing_fields: string[];
  request_id: string | null;
  status: string;
  redirect_path: string | null;
  redirect_requires_confirmation: boolean;
  task_cards: { service_id: string; service_name: string }[] | null;
  share_text: string | null;
}
