const FIELD_LABELS: Record<string, string> = {
  quantity: "數量",
  hours: "服務時數",
  cleaning_service_option: "服務方案",
  machine_type: "洗衣機類型",
  air_conditioner_type: "冷氣類型",
  antibacterial_film_addon: "是否加購抗菌膜",
  antibacterial_film_quantity: "抗菌膜數量",
  repair_item: "維修項目",
  issue_description: "問題描述",
  issue_photo: "問題照片",
  preferred_date: "希望日期",
  preferred_time_slot: "希望時段",
  address: "地址",
  phone: "聯絡電話",
  notes: "備註",
  restaurant_name: "餐廳",
  reserved_date: "訂位日期",
  time_slot: "用餐時段",
  specific_time: "指定時間",
  people: "用餐人數",
  contact_name: "聯絡人",
  is_premium: "訂位方案",
  store_id: "店家",
  goods: "餐點內容",
  note: "配送備註",
  pickup_method: "取件方式",
  sender_address: "寄件地址",
  receiver_address: "收件地址",
  sender_store: "寄件門市",
  receiver_store: "收件門市",
  weight_kg: "包裹重量",
  length_cm: "包裹長度",
  width_cm: "包裹寬度",
  height_cm: "包裹高度",
  item_description: "物品內容",
  declared_value: "申報價值",
  pickup_time_slot: "收件時段",
  faq_reference: "參考 FAQ",
  current_page_id: "頁面代碼",
  current_page_label: "目前頁面",
  related_request_id: "關聯案件編號",
  related_service_name: "關聯服務",
  issue_topic: "問題分類",
  issue_summary: "問題摘要",
  issue_details: "問題說明",
};

const VALUE_LABELS: Record<string, string> = {
  MORNING: "上午",
  AFTERNOON: "下午",
  EVENING: "晚上",
  TOP_LOAD: "直立式",
  FRONT_LOAD: "滾筒式",
  YES: "是",
  NO: "否",
  LUNCH: "午餐",
  DINNER: "晚餐",
  HOME_PICKUP: "到府收件",
  STORE_TO_STORE: "店到店",
  true: "進階方案",
  false: "標準方案",
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
    return "已上傳圖片";
  }
  return VALUE_LABELS[String(value)] ?? String(value);
}

function cartValueLabel(items: CartLineItem[]): string {
  if (items.length === 0) return "-";
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
