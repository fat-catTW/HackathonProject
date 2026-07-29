const FIELD_LABELS: Record<string, string> = {
  quantity: "數量",
  hours: "服務時數",
  cleaning_service_option: "服務選項",
  machine_type: "洗衣機類型",
  air_conditioner_type: "冷氣機種",
  antibacterial_film_addon: "是否加購日本抗菌膜",
  antibacterial_film_quantity: "日本抗菌膜數量",
  repair_item: "叫修工項",
  issue_description: "問題描述",
  issue_photo: "現場照片",
  preferred_date: "服務日期",
  preferred_time_slot: "服務時間",
  address: "服務地址",
  phone: "聯絡電話",
  notes: "備註",
  restaurant_name: "餐廳",
  reserved_date: "用餐日期",
  time_slot: "用餐時段",
  specific_time: "用餐時間",
  people: "用餐人數",
  contact_name: "聯絡人姓名",
  is_premium: "訂位類型",
  store_id: "店家",
  goods: "餐點",
  note: "備註需求",
};

const VALUE_LABELS: Record<string, string> = {
  MORNING: "上午",
  AFTERNOON: "下午",
  EVENING: "晚上",
  TOP_LOAD: "直立式",
  FRONT_LOAD: "滾筒式",
  YES: "需要",
  NO: "不需要",
  LUNCH: "午餐",
  DINNER: "晚餐",
  "true": "高級訂位",
  "false": "一般訂位",
};

interface CartLineItem {
  id: string;
  title: string;
  price: number;
  quantity: number;
}

interface AddressLike {
  city?: string;
  area?: string;
  street?: string;
  remark?: string;
  [key: string]: unknown;
}

export type CollectedFieldValue = string | number | CartLineItem[] | AddressLike;

function isCartLineItemArray(value: CollectedFieldValue): value is CartLineItem[] {
  return Array.isArray(value);
}

function isAddressLike(value: CollectedFieldValue): value is AddressLike {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function fieldLabel(key: string): string {
  return FIELD_LABELS[key] ?? key;
}

export function fieldValueLabel(value: string | number): string {
  if (typeof value === "string" && value.startsWith("data:image/")) {
    return "已上傳照片";
  }
  return VALUE_LABELS[String(value)] ?? String(value);
}

function cartValueLabel(items: CartLineItem[]): string {
  if (items.length === 0) return "—";
  return items.map((item) => `${item.title} x${item.quantity}`).join("、");
}

function addressValueLabel(address: AddressLike): string {
  const line = `${address.city ?? ""}${address.area ?? ""}${address.street ?? ""}`;
  return address.remark ? `${line}（${address.remark}）` : line;
}

export function formatFieldValue(value: CollectedFieldValue): string {
  if (isCartLineItemArray(value)) return cartValueLabel(value);
  if (isAddressLike(value)) return addressValueLabel(value);
  return fieldValueLabel(value);
}

export interface FieldRow {
  key: string;
  label: string;
  value: string;
}

export function buildFieldRows(collected: Record<string, CollectedFieldValue>): FieldRow[] {
  return Object.entries(collected).map(([key, value]) => ({
    key,
    label: fieldLabel(key),
    value: formatFieldValue(value),
  }));
}
