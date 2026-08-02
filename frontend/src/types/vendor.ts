import type { RequestStatus } from "./request";

export type VendorScope = "pending" | "orders" | "all";

/** 廠商能對案件做的狀態切換；後端的狀態機決定當下有哪些可用。 */
export type VendorAction =
  | "accept"
  | "reject"
  | "start"
  | "complete"
  | "verify"
  | "prepare"
  | "pickup"
  | "dispatch"
  | "deliver"
  | "confirm"
  | "ship";

export interface VendorRequestItem {
  request_id: string;
  service_id: string;
  service_name: string;
  status: RequestStatus;
  status_label: string;
  customer_name: string;
  summary: string;
  /** 樂觀鎖版本，接單／拒單時要原樣帶回後端。 */
  version: number;
  available_actions: VendorAction[];
  created_at: string;
  updated_at: string;
}

export interface VendorRequestField {
  id: string;
  label: string;
  value: string;
  /** 聯絡欄位；value 是遮罩後的內容，完整值要呼叫 revealVendorContact。 */
  masked: boolean;
}

/** 一次「解密看了聯絡資訊」的紀錄（Milestone 15）。 */
export interface VendorContactAccess {
  at: string;
  viewer_name: string;
  /** 這次看到的欄位名稱，例如「聯絡電話」。 */
  fields: string[];
}

export interface VendorRequestDetail
  extends Omit<VendorRequestItem, "summary"> {
  /**
   * 建單當下由 AI 算好的一句話重點。外送／商城後台不供這個欄位，Milestone 前建立
   * 的舊案件也沒有，因此是選填——沒有值時明細頁就不顯示那一列。
   */
  ai_summary?: string;
  fields: VendorRequestField[];
  /** 這筆案件有沒有可解密的聯絡資訊；沒有就不顯示解鎖按鈕。 */
  has_contact: boolean;
  contact_access_log: VendorContactAccess[];
  estimated_fee_min?: number;
  estimated_fee_max?: number;
}

/**
 * 廠商替一張單貼的自訂標籤（急件／大型案件／待報價…）。
 *
 * 標籤是廠商後台的內部註記，住戶端看不到，也不隨案件本體回傳——所以它不在
 * VendorRequestItem／VendorRequestDetail 裡，而是另外一組端點（api/vendorTags）。
 */
export interface VendorCaseTags {
  request_id: string;
  tags: string[];
}

/** `{案件編號: [標籤…]}`；沒貼過標籤的案件不會出現在這份字典裡。 */
export type CaseTagMap = Record<string, string[]>;

export interface VendorContactReveal {
  success: true;
  request_id: string;
  contact: { id: string; label: string; value: string }[];
  contact_access_log: VendorContactAccess[];
}

/** 接單／拒單成功後回傳案件的最新樣貌（含新版本號）。 */
export interface VendorActionResult extends VendorRequestDetail {
  success: true;
}

export interface VendorRequestList {
  items: VendorRequestItem[];
  counts: Record<VendorScope, number>;
}

export interface VendorLoginResult {
  token: string;
  vendor_id: number;
  name: string;
}

export interface VendorDemoAccount {
  email: string;
  name: string;
  password: string;
}

export interface VendorProfile {
  vendor_id: number;
  name: string;
  service_ids: string[];
}

export type VendorKind = "generic" | "delivery" | "shop";

const DELIVERY_VENDOR_ID = 30;
const SHOP_VENDOR_ID = 40;

/** 依登入的 vendor_id 判斷這個帳號屬於哪種案件——沿用 catalog.py 裡「一個服務線一個廠商帳號」的慣例。 */
export function vendorKindOf(vendorId: number | null): VendorKind {
  if (vendorId === DELIVERY_VENDOR_ID) return "delivery";
  if (vendorId === SHOP_VENDOR_ID) return "shop";
  return "generic";
}
