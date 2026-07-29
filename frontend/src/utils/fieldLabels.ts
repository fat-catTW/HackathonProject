const FIELD_LABELS: Record<string, string> = {
  quantity: "數量",
  hours: "服務時數",
  machine_type: "洗衣機類型",
  issue_description: "問題描述",
  preferred_date: "希望日期",
  preferred_time_slot: "希望時段",
  address: "服務地址",
  phone: "聯絡電話",
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

/** 格式化任一種 collected/form_data 欄位值，涵蓋一般文字/數字、購物車清單、地址物件。 */
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
