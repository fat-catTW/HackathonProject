export type RequestStatus =
  | "DRAFT"
  | "AWAITING_USER_CONFIRMATION"
  | "SUBMITTED"
  | "PENDING_PROVIDER"
  | "CONFIRMED"
  | "IN_PROGRESS"
  | "COMPLETED"
  | "CANCELLED"
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
}

export interface FormFieldSchema {
  id: string;
  label: string;
  type: string;
  required: boolean;
  options?: string[];
}

export interface FormSchema {
  service_id: string | null;
  service_name: string | null;
  fields: FormFieldSchema[];
}

export interface FormDraft {
  service_id: string | null;
  service_name: string | null;
  status: string;
  request_id: string | null;
  fields: Record<string, string | number | null>;
  missing_fields: string[];
  active_field: string | null;
  ready_for_confirmation: boolean;
}

export interface RequestDetail extends RequestListItem {
  session_id: string | null;
  service_id: string;
  form_data: Record<string, string | number>;
  events: ChatEvent[];
}

export interface ChatResponse {
  session_id: string;
  reply: string;
  service_id: string | null;
  service_name: string | null;
  collected_fields: Record<string, string | number>;
  missing_fields: string[];
  form_schema: FormSchema | null;
  form_draft: FormDraft | null;
  active_field: string | null;
  request_id: string | null;
  status: string;
}
