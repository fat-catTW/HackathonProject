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

interface Props {
  serviceName: string | null;
  collected: Record<string, string | number>;
  missing: string[];
}

/** 對話頁側欄：已填欄位＋尚缺欄位即時呈現。 */
export function FormSummary({ serviceName, collected, missing }: Props) {
  return (
    <div className="rounded-2xl border border-pine-soft bg-white p-4">
      <p className="text-sm font-bold text-pine">
        {serviceName ? `服務：${serviceName}` : "正在了解您的需求⋯"}
      </p>
      <dl className="mt-3 space-y-2">
        {Object.entries(collected).map(([k, v]) => (
          <div key={k} className="flex justify-between gap-3 text-sm">
            <dt className="text-gray-500">{FIELD_LABELS[k] ?? k}</dt>
            <dd className="font-medium">{VALUE_LABELS[String(v)] ?? v}</dd>
          </div>
        ))}
      </dl>
      {missing.length > 0 && (
        <p className="mt-3 border-t border-dashed border-pine-soft pt-3 text-sm text-gray-500">
          還需要：{missing.map((m) => FIELD_LABELS[m] ?? m).join("、")}
        </p>
      )}
    </div>
  );
}
