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

export function fieldLabel(key: string): string {
  return FIELD_LABELS[key] ?? key;
}

export function fieldValueLabel(value: string | number): string {
  return VALUE_LABELS[String(value)] ?? String(value);
}

export interface FieldRow {
  key: string;
  label: string;
  value: string;
}

export function buildFieldRows(collected: Record<string, string | number>): FieldRow[] {
  return Object.entries(collected).map(([key, value]) => ({
    key,
    label: fieldLabel(key),
    value: fieldValueLabel(value),
  }));
}
