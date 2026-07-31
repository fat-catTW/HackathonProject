import type { RequestStatus } from "./request";

export type VendorScope = "pending" | "orders" | "all";

/** 廠商能對案件做的狀態切換；後端的狀態機決定當下有哪些可用。 */
export type VendorAction = "accept" | "reject";

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
}

export interface VendorRequestDetail
  extends Omit<VendorRequestItem, "summary"> {
  fields: VendorRequestField[];
  estimated_fee_min?: number;
  estimated_fee_max?: number;
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
