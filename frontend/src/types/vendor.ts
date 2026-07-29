import type { RequestStatus } from "./request";

export type VendorScope = "pending" | "orders" | "all";

export interface VendorRequestItem {
  request_id: string;
  service_id: string;
  service_name: string;
  status: RequestStatus;
  status_label: string;
  customer_name: string;
  summary: string;
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
