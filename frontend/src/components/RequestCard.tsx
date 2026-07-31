import { Link } from "react-router-dom";
import type { RequestListItem } from "../types/request";
import { ServiceIcon } from "./ServiceIcon";
import { serviceIconType } from "../utils/serviceIcons";
import { StatusBadge } from "./StatusBadge";

function formatTime(value: string) {
  if (!value) return "";
  return new Date(value).toLocaleString("zh-TW", {
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * 案件列表項目。屬於資料密集的列表元件，依 Requirement 15.2 一律維持不透明實色卡片
 * （`--color-surface`），不套 `.glass-panel` 或品牌漸層，確保長列表的可讀性與掃視效率。
 * 配色一律引用語意色 Token（Requirement 6.6），Light/Dark 共用同一份 className。
 * 時間戳改用 `--font-mono`（Requirement 7.3：資料型文字使用等寬字族）。
 */
export function RequestCard({ item }: { item: RequestListItem }) {
  // 建立時間是住戶認得出這張單的依據（「我昨天晚上叫的那筆」），一定要留著。
  // 以前卡片只顯示 updated_at 又沒標籤，廠商一接單時間就跳掉，住戶會以為案件不見了。
  const hasProgress = Boolean(item.updated_at) && item.updated_at !== item.created_at;
  return (
    <Link
      to={`/requests/${item.request_id}`}
      className="flex items-center gap-4 rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4 shadow-sm transition hover:border-[var(--color-primary)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-primary)]"
    >
      <span className="flex h-13 w-13 shrink-0 items-center justify-center rounded-2xl bg-[var(--color-primary-soft)] text-[var(--color-primary)]">
        <ServiceIcon type={serviceIconType(item.service_name)} size={26} />
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate text-lg font-bold text-[var(--color-foreground)]">{item.service_name}</p>
        <p className="mt-0.5 font-[family-name:var(--font-mono)] text-sm text-[var(--color-muted-foreground)]">
          建立 {formatTime(item.created_at)}
        </p>
        {hasProgress && (
          <p className="mt-0.5 font-[family-name:var(--font-mono)] text-sm text-[var(--color-muted-foreground)] opacity-80">
            更新 {formatTime(item.updated_at)}
          </p>
        )}
      </div>
      <StatusBadge status={item.status} label={item.status_label} />
    </Link>
  );
}
