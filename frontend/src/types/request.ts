import type { ClinicChatRecommendation } from "./clinic";
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

export interface ChatRestaurantCard {
  id: string;
  name: string;
  address: string;
  phone: string;
  reason?: string;
  source?: string;
}

export interface ChatEvent {
  role: "USER" | "ASSISTANT";
  content: string;
  redirectPath?: string;
  taskCards?: { service_id: string; service_name: string }[];
  restaurantCards?: ChatRestaurantCard[];
  shareText?: string;
  clinicRecommendation?: ClinicChatRecommendation;
}

export interface RequestDetail extends RequestListItem {
  session_id: string | null;
  service_id: string;
  form_data: Record<string, CollectedFieldValue>;
  events: ChatEvent[];
  estimated_fee_min?: number;
  estimated_fee_max?: number;
}

/** AI 代操表單時，Agent 要前端在畫面上執行的一個動作。 */
export interface FormAction {
  type: "fill" | "clear";
  field_id: string;
  label: string;
  /** 直接寫進輸入框的值（select 為 option value、number 為數字字串）。 */
  value: string;
  /** 給人看的值，例如 `直立式`、`2 台`。 */
  display_value: string;
  /** 資料來源說明，例如「沿用你上次填的資料」。 */
  note: string | null;
}

/** 送出訊息時附上的表單快照，讓 Agent 以畫面上的內容為準。 */
export interface FormContext {
  service_id: string;
  values: Record<string, string>;
}

export interface ChatResponse {
  session_id: string;
  reply: string;
  service_id: string | null;
  service_name: string | null;
  collected_fields: Record<string, CollectedFieldValue>;
  missing_fields: string[];
  form_actions: FormAction[];
  request_id: string | null;
  status: string;
  redirect_path: string | null;
  redirect_requires_confirmation: boolean;
  task_cards: { service_id: string; service_name: string }[] | null;
  restaurant_cards: ChatRestaurantCard[] | null;
  share_text: string | null;
  clinic_recommendation: ClinicChatRecommendation | null;
}
