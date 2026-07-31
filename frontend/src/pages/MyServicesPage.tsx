import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { listRequests } from "../api/requests";
import { RequestCard } from "../components/RequestCard";
import { ServiceIcon } from "../components/ServiceIcon";
import { BottomNav } from "../components/BottomNav";
import { SupportPanel } from "../components/SupportPanel";
import type { RequestListItem, RequestStatus } from "../types/request";

// 已結案的狀態：沒有後續進度可追，一律沉到清單底部。
const CLOSED_STATUSES: ReadonlySet<RequestStatus> = new Set<RequestStatus>([
  "COMPLETED",
  "CANCELLED",
  "REJECTED",
  "FAILED",
]);

function updatedAt(item: RequestListItem): number {
  return Date.parse(item.updated_at) || 0;
}

/**
 * 只分「還在跑的」與「已結案的」兩組，組內以 updated_at 新到舊排序。
 *
 * 早期版本是按狀態細分組（等待廠商確認 → 已確認 → 已完成），結果住戶累積幾十筆
 * 放著沒動的「等待廠商確認」之後，剛被廠商接單的那筆會整組被壓到那幾十筆後面 ——
 * 使用者剛收到的好消息反而看不見，像是案件消失了。細分組解決不了這件事：問題不在
 * 組內順序，而在「等待中」這組永遠蓋著「有進展」那組。
 *
 * 所以改成以「最近有動靜」為主軸：不管走到哪一步，剛更新的案件就在最上面；只有
 * 結案的案件因為沒有後續可追，才固定沉到底部（組內同樣最近的在前）。
 */
export function sortRequests(items: RequestListItem[]): RequestListItem[] {
  return [...items].sort((a, b) => {
    const byGroup = Number(CLOSED_STATUSES.has(a.status)) - Number(CLOSED_STATUSES.has(b.status));
    return byGroup !== 0 ? byGroup : updatedAt(b) - updatedAt(a);
  });
}

export function MyServicesPage() {
  const navigate = useNavigate();
  const [items, setItems] = useState<RequestListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [supportOpen, setSupportOpen] = useState(false);

  useEffect(() => {
    if (!supportOpen) return;
    const { body } = document;
    const previousOverflow = body.style.overflow;
    body.style.overflow = "hidden";
    return () => {
      body.style.overflow = previousOverflow;
    };
  }, [supportOpen]);

  useEffect(() => {
    listRequests()
      .then((r) => setItems(sortRequests(r.items)))
      .catch(() => navigate("/login"))
      .finally(() => setLoading(false));
  }, [navigate]);

  return (
    <>
      <main className="mx-auto min-h-dvh max-w-md bg-canvas px-5 pb-32 pt-8">
        <header className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => navigate("/home")}
            className="flex h-11 w-11 items-center justify-center rounded-full bg-[var(--color-surface)] text-[var(--color-muted-foreground)] shadow-sm transition hover:text-brand"
          >
            <ServiceIcon type="back" size={20} />
          </button>
          <div>
            <p className="text-sm font-semibold text-brand">服務紀錄</p>
            <h1 className="text-2xl font-black text-[var(--color-foreground)]">我的服務</h1>
          </div>
        </header>

        <section className="mt-8 rounded-[28px] bg-[var(--color-surface)] p-5 shadow-sm">
          <h2 className="text-lg font-black text-[var(--color-foreground)]">查看案件與進度</h2>
          <p className="mt-2 text-sm leading-6 text-[var(--color-muted-foreground)]">
            這裡會列出你已建立的服務需求，包含目前狀態與最近更新時間。
          </p>
        </section>

        <section className="mt-6 space-y-3.5">
          {loading && (
            <p className="rounded-2xl bg-[var(--color-surface)] p-5 text-center text-[var(--color-muted-foreground)] shadow-sm">
              正在載入服務紀錄…
            </p>
          )}
          {!loading && items.length === 0 && (
            <p className="rounded-2xl border border-dashed border-[var(--color-border)] bg-[var(--color-surface)] p-6 text-center text-[var(--color-muted-foreground)]">
              目前還沒有服務案件，按下下方的 AI 管家按鈕就能開始建立。
            </p>
          )}
          {items.map((item) => (
            <RequestCard key={item.request_id} item={item} />
          ))}
        </section>

        <section className="mt-6">
          <button
            type="button"
            onClick={() => setSupportOpen(true)}
            className="flex w-full items-center justify-between rounded-[28px] border border-[var(--color-border)] bg-[var(--color-surface)] px-5 py-5 text-left shadow-sm transition hover:border-brand/15 active:shadow-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand"
          >
            <div className="flex items-center gap-4">
              <span
                className="flex h-14 w-14 items-center justify-center rounded-2xl"
                style={{
                  backgroundImage: "linear-gradient(145deg, var(--color-surface) 0%, var(--color-secondary-soft) 100%)",
                  boxShadow:
                    "inset 0 1px 1px rgba(255,255,255,0.8), inset 0 -6px 10px -7px rgba(0,0,0,0.12), 0 10px 18px -12px var(--color-secondary)",
                  color: "var(--color-secondary)",
                }}
              >
                <ServiceIcon type="info" size={26} strokeWidth={2} />
              </span>
              <div>
                <p className="text-lg font-black text-[var(--color-foreground)]">客服中心</p>
                <p className="mt-1 text-sm text-[var(--color-muted-foreground)]">案件有疑問？FAQ 快速解答或轉真人客服</p>
              </div>
            </div>
            <ServiceIcon type="chevronRight" size={20} className="text-[var(--color-muted-foreground)]" />
          </button>
        </section>
      </main>

      {supportOpen && (
        <div className="fixed inset-0 z-50 bg-[var(--color-scrim)] px-4 py-6 backdrop-blur-[2px] sm:px-6 sm:py-8">
          <button
            type="button"
            aria-label="關閉客服視窗"
            onClick={() => setSupportOpen(false)}
            className="absolute inset-0"
          />
          <div className="relative flex h-full items-end justify-end">
            <SupportPanel currentPageId="my_services" onClose={() => setSupportOpen(false)} />
          </div>
        </div>
      )}

      <BottomNav />
    </>
  );
}
