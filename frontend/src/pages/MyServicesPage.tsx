import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { listRequests } from "../api/requests";
import { RequestCard } from "../components/RequestCard";
import { ServiceIcon } from "../components/ServiceIcon";
import { BottomNav } from "../components/BottomNav";
import { SupportPanel } from "../components/SupportPanel";
import { SearchAndCategoryFilter, SegmentedFilterGroup } from "../components/SearchAndCategoryFilter";
import { SERVICES } from "../data/services";
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

/** 服務在目錄中的顯示順序，用來排序分類 chip；不在目錄裡的服務名稱排到最後。 */
const SERVICE_ORDER = new Map(SERVICES.map((service, index) => [service.title, index]));

/** 篩選列只列出目前資料裡實際出現過的服務種類，避免出現使用者從沒申請過的空分類。 */
const MIN_ITEMS_FOR_FILTER = 3;

/**
 * 把細分的案件狀態歸類成住戶好理解的四種篩選標籤：
 * 待確認（草稿／等待廠商回應）、已確認（廠商已接單，含已聯繫／已報價／服務進行中）、
 * 已完成、已婉拒（廠商拒單、住戶取消、或處理失敗，都算沒有繼續進行）。
 */
const STATUS_GROUP: Record<string, string> = {
  DRAFT: "PENDING",
  AWAITING_USER_CONFIRMATION: "PENDING",
  SUBMITTED: "PENDING",
  AWAITING_QUOTE: "PENDING",
  PENDING_PROVIDER: "PENDING",
  CONFIRMED: "CONFIRMED",
  CONTACTED: "CONFIRMED",
  QUOTED: "CONFIRMED",
  IN_PROGRESS: "CONFIRMED",
  COMPLETED: "COMPLETED",
  CANCELLED: "DECLINED",
  REJECTED: "DECLINED",
  FAILED: "DECLINED",
};

const STATUS_GROUP_LABELS: { id: string; label: string }[] = [
  { id: "PENDING", label: "待確認" },
  { id: "CONFIRMED", label: "已確認" },
  { id: "COMPLETED", label: "已完成" },
  { id: "DECLINED", label: "已婉拒" },
];

export function MyServicesPage() {
  const navigate = useNavigate();
  const [items, setItems] = useState<RequestListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [supportOpen, setSupportOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [activeCategory, setActiveCategory] = useState("all");
  const [activeStatus, setActiveStatus] = useState("all");

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

  const categories = useMemo(() => {
    const names = [...new Set(items.map((item) => item.service_name))].sort(
      (a, b) => (SERVICE_ORDER.get(a) ?? 999) - (SERVICE_ORDER.get(b) ?? 999),
    );
    return [
      { id: "all", label: "全部", count: items.length },
      ...names.map((name) => ({
        id: name,
        label: name,
        count: items.filter((item) => item.service_name === name).length,
      })),
    ];
  }, [items]);

  const statusFilters = useMemo(() => {
    return [
      { id: "all", label: "全部", count: items.length },
      ...STATUS_GROUP_LABELS.map((group) => ({
        ...group,
        count: items.filter((item) => STATUS_GROUP[item.status] === group.id).length,
      })).filter((group) => group.count > 0),
    ];
  }, [items]);

  const filteredItems = useMemo(() => {
    const keyword = search.trim().toLowerCase();
    return items.filter((item) => {
      const matchesCategory = activeCategory === "all" || item.service_name === activeCategory;
      const matchesStatus = activeStatus === "all" || STATUS_GROUP[item.status] === activeStatus;
      const matchesSearch = !keyword || item.service_name.toLowerCase().includes(keyword);
      return matchesCategory && matchesStatus && matchesSearch;
    });
  }, [items, search, activeCategory, activeStatus]);

  const showFilterBar = items.length > MIN_ITEMS_FOR_FILTER;

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

        {showFilterBar && (
          <section className="mt-8 space-y-3">
            <SearchAndCategoryFilter
              searchValue={search}
              onSearchChange={setSearch}
              searchLabel="搜尋服務名稱"
              searchPlaceholder="搜尋服務名稱"
              categoryGroupLabel="服務種類篩選"
              categories={categories}
              activeCategory={activeCategory}
              onCategoryChange={setActiveCategory}
            />
            <SegmentedFilterGroup
              groupLabel="案件狀態篩選"
              options={statusFilters}
              activeId={activeStatus}
              onChange={setActiveStatus}
            />
          </section>
        )}

        <section className={`space-y-3.5 ${showFilterBar ? "mt-5" : "mt-8"}`}>
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
          {!loading && items.length > 0 && filteredItems.length === 0 && (
            <p className="rounded-2xl border border-dashed border-[var(--color-border)] bg-[var(--color-surface)] p-6 text-center text-[var(--color-muted-foreground)]">
              找不到符合的服務案件，換個關鍵字看看。
            </p>
          )}
          {filteredItems.map((item) => (
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
