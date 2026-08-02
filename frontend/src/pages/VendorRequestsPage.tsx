import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ApiError } from "../api/client";
import { getVendorApiForKind } from "../api/vendorRouting";
import { listVendorCaseTags } from "../api/vendorTags";
import { vendorKindOf } from "../types/vendor";
import { CaseTagBadge } from "../components/CaseTagBadge";
import { ServiceIcon } from "../components/ServiceIcon";
import { FilterChipGroup, SearchAndCategoryFilter } from "../components/SearchAndCategoryFilter";
import { StatusBadge } from "../components/StatusBadge";
import { useVendorAuth } from "../hooks/useVendorAuth";
import { CASE_TAG_PRESETS } from "../data/caseTags";
import { SERVICES } from "../data/services";
import type { CaseTagMap, VendorRequestItem, VendorScope } from "../types/vendor";
import { serviceIconType } from "../utils/serviceIcons";

/** 服務在目錄中的顯示順序，用來排序分類 chip；不在目錄裡的服務排到最後。 */
const SERVICE_ORDER = new Map(SERVICES.map((service, index) => [service.service_id, index]));

/** 常用標籤排在自訂標籤前面，讓「急件」永遠在同一個位置，不隨資料變動跳來跳去。 */
const TAG_ORDER = new Map(CASE_TAG_PRESETS.map((tag, index) => [tag as string, index]));

const TABS: { scope: VendorScope; label: string }[] = [
  { scope: "pending", label: "待確認諮詢單" },
  { scope: "orders", label: "已接訂單" },
  { scope: "all", label: "全部" },
];

function formatTime(value: string) {
  if (!value) return "";
  return new Date(value).toLocaleString("zh-TW", {
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function VendorRequestsPage() {
  const navigate = useNavigate();
  const { name, vendorId, logout } = useVendorAuth();
  const vendorApiSet = getVendorApiForKind(vendorKindOf(vendorId));
  const [scope, setScope] = useState<VendorScope>("pending");
  const [items, setItems] = useState<VendorRequestItem[]>([]);
  const [counts, setCounts] = useState<Record<VendorScope, number>>({
    pending: 0,
    orders: 0,
    all: 0,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [activeCategory, setActiveCategory] = useState("all");
  // 廠商自己貼的標籤（案件編號 → 標籤），跟案件清單分開讀（見 api/vendorTags）。
  const [tagMap, setTagMap] = useState<CaseTagMap>({});
  const [activeTag, setActiveTag] = useState("all");

  const load = useCallback(
    (next: VendorScope) => {
      setLoading(true);
      setError("");
      // 標籤是輔助資訊：讀失敗就沿用手上這份（一開始是空的），不要讓整份清單失敗。
      listVendorCaseTags()
        .then((result) => setTagMap(result.tags))
        .catch(() => {});
      vendorApiSet
        .list(next)
        .then((r) => {
          setItems(r.items);
          setCounts(r.counts);
        })
        .catch((e) => {
          if (e instanceof ApiError && e.code === "UNAUTHORIZED") {
            navigate("/vendor/login");
            return;
          }
          setError(e instanceof ApiError ? e.message : "載入失敗，請稍後再試");
        })
        .finally(() => setLoading(false));
    },
    [navigate, vendorApiSet],
  );

  useEffect(() => {
    load(scope);
  }, [load, scope]);

  const categories = useMemo(() => {
    const ids = [...new Set(items.map((item) => item.service_id))].sort(
      (a, b) => (SERVICE_ORDER.get(a) ?? 999) - (SERVICE_ORDER.get(b) ?? 999),
    );
    return [
      { id: "all", label: "全部", count: items.length },
      ...ids.map((id) => {
        const label = items.find((item) => item.service_id === id)?.service_name ?? id;
        return { id, label, count: items.filter((item) => item.service_id === id).length };
      }),
    ];
  }, [items]);

  // 標籤 chip 只列出這個分頁的案件實際貼過的標籤，避免出現一個點下去是空的篩選。
  const tagOptions = useMemo(() => {
    const counts = new Map<string, number>();
    for (const item of items) {
      for (const tag of tagMap[item.request_id] ?? []) {
        counts.set(tag, (counts.get(tag) ?? 0) + 1);
      }
    }
    if (counts.size === 0) return [];
    const sorted = [...counts.keys()].sort(
      (a, b) => (TAG_ORDER.get(a) ?? 999) - (TAG_ORDER.get(b) ?? 999) || a.localeCompare(b, "zh-TW"),
    );
    return [
      { id: "all", label: "全部標籤", count: items.length },
      ...sorted.map((tag) => ({ id: tag, label: tag, count: counts.get(tag) ?? 0 })),
    ];
  }, [items, tagMap]);

  // 切換狀態分頁後資料會換一批，若原本選的分類／標籤在新資料裡已經不存在，回到
  // 「全部」避免空列表。
  useEffect(() => {
    if (activeCategory === "all") return;
    if (!categories.some((category) => category.id === activeCategory)) {
      setActiveCategory("all");
    }
  }, [categories, activeCategory]);

  useEffect(() => {
    if (activeTag === "all") return;
    if (!tagOptions.some((option) => option.id === activeTag)) setActiveTag("all");
  }, [tagOptions, activeTag]);

  const filteredItems = useMemo(() => {
    const keyword = search.trim().toLowerCase();
    return items.filter((item) => {
      const matchesCategory = activeCategory === "all" || item.service_id === activeCategory;
      const matchesTag = activeTag === "all" || (tagMap[item.request_id] ?? []).includes(activeTag);
      const matchesSearch =
        !keyword ||
        item.service_name.toLowerCase().includes(keyword) ||
        item.customer_name.toLowerCase().includes(keyword) ||
        item.request_id.toLowerCase().includes(keyword) ||
        // 標籤也吃搜尋：打「急件」找得到，不必先繞到標籤 chip。
        (tagMap[item.request_id] ?? []).some((tag) => tag.toLowerCase().includes(keyword));
      return matchesCategory && matchesTag && matchesSearch;
    });
  }, [items, search, activeCategory, activeTag, tagMap]);

  return (
    <main className="mx-auto min-h-dvh max-w-4xl bg-canvas px-5 pb-16 pt-8 sm:px-8">
      {/*
        僅頂部標題區使用極淡漸層色帶（`.bg-brand-gradient-soft`），不搶下方列表焦點；
        Tab 列與案件列表一律維持不透明實色卡片，不套玻璃擬態（Requirement 14.1、15.2）。
      */}
      <header className="bg-brand-gradient-soft -mx-5 flex flex-wrap items-center justify-between gap-4 rounded-b-[28px] px-5 pb-6 sm:-mx-8 sm:px-8">
        <div>
          <p className="text-sm font-semibold text-brand">廠商後台</p>
          <h1 className="font-[family-name:var(--font-display)] text-2xl font-black text-[var(--color-foreground)] sm:text-3xl">
            {name || "服務廠商"}
          </h1>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => load(scope)}
            className="rounded-full bg-[var(--color-surface)] px-4 py-2.5 text-sm font-bold text-brand shadow-sm transition hover:bg-brand-soft"
          >
            重新整理
          </button>
          <button
            type="button"
            onClick={() => {
              logout();
              navigate("/vendor/login");
            }}
            className="rounded-full bg-[var(--color-surface)] px-4 py-2.5 text-sm font-bold text-[var(--color-muted-foreground)] shadow-sm transition hover:text-danger"
          >
            登出
          </button>
        </div>
      </header>

      <nav className="mt-7 flex flex-wrap gap-2">
        {TABS.map((tab) => (
          <button
            key={tab.scope}
            type="button"
            onClick={() => setScope(tab.scope)}
            aria-current={scope === tab.scope}
            className={`rounded-full px-4.5 py-2.5 text-base font-bold transition ${
              scope === tab.scope
                ? "bg-brand text-[var(--color-on-primary)]"
                : "bg-[var(--color-surface)] text-[var(--color-muted-foreground)] hover:text-brand"
            }`}
          >
            {tab.label}
            <span
              className={`ml-2 rounded-full px-2 py-0.5 text-sm ${
                scope === tab.scope ? "bg-[var(--color-surface-glass)]" : "bg-[var(--color-canvas)] text-[var(--color-muted-foreground)]"
              }`}
            >
              {counts[tab.scope]}
            </span>
          </button>
        ))}
      </nav>

      {!loading && !error && items.length > 0 && (
        <section className="mt-5">
          <SearchAndCategoryFilter
            searchValue={search}
            onSearchChange={setSearch}
            searchLabel="搜尋案件編號、客戶或服務"
            searchPlaceholder="搜尋案件編號、客戶或服務"
            categoryGroupLabel="服務種類篩選"
            categories={categories}
            activeCategory={activeCategory}
            onCategoryChange={setActiveCategory}
          />
          {/* 標籤篩選另起一列，跟服務種類分開：一個是案件本來的分類，一個是自己貼的。 */}
          {tagOptions.length > 0 && (
            <div className="mt-3">
              <FilterChipGroup
                groupLabel="標籤篩選"
                options={tagOptions}
                activeId={activeTag}
                onChange={setActiveTag}
              />
            </div>
          )}
        </section>
      )}

      <section className="mt-5 space-y-3">
        {loading && (
          <p className="rounded-2xl bg-[var(--color-surface)] p-6 text-center text-[var(--color-muted-foreground)] shadow-sm">
            正在載入案件…
          </p>
        )}
        {!loading && error && (
          <p className="rounded-2xl bg-[var(--color-surface)] p-6 text-center text-danger shadow-sm">{error}</p>
        )}
        {!loading && !error && items.length === 0 && (
          <p className="rounded-2xl border border-dashed border-[var(--color-border)] bg-[var(--color-surface)] p-8 text-center text-[var(--color-muted-foreground)]">
            這個分頁目前沒有案件。
          </p>
        )}
        {!loading && !error && items.length > 0 && filteredItems.length === 0 && (
          <p className="rounded-2xl border border-dashed border-[var(--color-border)] bg-[var(--color-surface)] p-8 text-center text-[var(--color-muted-foreground)]">
            找不到符合的案件，換個關鍵字看看。
          </p>
        )}
        {!loading &&
          !error &&
          filteredItems.map((item) => (
            <Link
              key={item.request_id}
              to={`/vendor/requests/${item.request_id}`}
              className="flex items-center gap-4 rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4 shadow-sm transition hover:border-brand focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand"
            >
              <span className="flex h-13 w-13 shrink-0 items-center justify-center rounded-2xl bg-brand-soft text-brand">
                <ServiceIcon type={serviceIconType(item.service_name)} size={26} />
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                  <p className="text-lg font-bold text-[var(--color-foreground)]">{item.service_name}</p>
                  <p className="text-sm text-[var(--color-muted-foreground)]">{item.request_id}</p>
                </div>
                {(tagMap[item.request_id] ?? []).length > 0 && (
                  <div className="mt-1 flex flex-wrap gap-1.5">
                    {(tagMap[item.request_id] ?? []).map((tag) => (
                      <CaseTagBadge key={tag} tag={tag} />
                    ))}
                  </div>
                )}
                <p className="mt-0.5 truncate text-sm text-[var(--color-muted-foreground)]">
                  {item.customer_name}
                  {item.summary && `　${item.summary}`}
                </p>
                <p className="mt-0.5 text-sm text-[var(--color-muted-foreground)]">
                  最近更新 {formatTime(item.updated_at)}
                </p>
              </div>
              <StatusBadge status={item.status} label={item.status_label} />
            </Link>
          ))}
      </section>
    </main>
  );
}
