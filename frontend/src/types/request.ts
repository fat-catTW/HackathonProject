import type { ClinicChatRecommendation } from "./clinic";
import type { CollectedFieldValue } from "../utils/fieldLabels";

export type RequestStatus =
  | "DRAFT"
  | "AWAITING_USER_CONFIRMATION"
  | "SUBMITTED"
  | "AWAITING_QUOTE"
  | "PENDING_PROVIDER"
  | "CONFIRMED"
  | "CONTACTED"
  | "QUOTED"
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
  /** 廠商報的價（新台幣元）；還沒報價是 null，不報價的服務根本沒有這個欄位。 */
  quote_amount?: number | null;
  created_at: string;
  updated_at: string;
}

/** 進度條上的一格。還沒走到的關卡也會回傳，`done` 為 false、`at` 是空字串。 */
export interface RequestProgressStep {
  status: RequestStatus | string;
  /** 關卡名稱，例如「已聯繫」；跟狀態徽章的文字刻意不同（那個講現況，這個講做完了沒）。 */
  label: string;
  /** 完成時間；這一格還沒走到、或案件早於進度歷程上線就是空字串。 */
  at: string;
  done: boolean;
}

export interface ChatRestaurantCard {
  id: string;
  name: string;
  address: string;
  phone: string;
  reason?: string;
  source?: string;
}

export interface ProductRecommendation {
  id: string | null;
  name: string;
  store_name: string;
  price: number | string | null;
  rating_avg: number | null;
  rating_count: number | null;
  reason: string;
}

export interface ChatEvent {
  role: "USER" | "ASSISTANT";
  content: string;
  redirectPath?: string;
  taskCards?: { service_id: string; service_name: string }[];
  restaurantCards?: ChatRestaurantCard[];
  shareText?: string;
  clinicRecommendation?: ClinicChatRecommendation;
  redirectLabel?: string;
  productRecommendations?: ProductRecommendation[];
}

export interface RequestDetail extends RequestListItem {
  session_id: string | null;
  service_id: string;
  form_data: Record<string, CollectedFieldValue>;
  /** 進度條的每一格；後端一律回傳，選填只是為了不讓部署交界的舊回應炸掉畫面。 */
  progress?: RequestProgressStep[];
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
  product_recommendations?: ProductRecommendation[] | null;
}
