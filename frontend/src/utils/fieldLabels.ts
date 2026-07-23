const FIELD_LABELS: Record<string, string> = {
  quantity: "數量",
  hours: "服務時數",
  machine_type: "洗衣機類型",
  issue_description: "問題描述",
  preferred_date: "希望日期",
  preferred_time_slot: "希望時段",
  address: "服務地址",
  phone: "聯絡電話",
};

const VALUE_LABELS: Record<string, string> = {
  MORNING: "上午",
  AFTERNOON: "下午",
  EVENING: "晚上",
  TOP_LOAD: "直立式",
  FRONT_LOAD: "滾筒式",
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

/** 把後端回傳的 collected_fields／form_data 轉成畫面顯示用的列表。 */
export function buildFieldRows(collected: Record<string, string | number>): FieldRow[] {
  return Object.entries(collected).map(([key, value]) => ({
    key,
    label: fieldLabel(key),
    value: fieldValueLabel(value),
  }));
}
