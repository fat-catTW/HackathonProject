import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ApiError } from "../api/client";
import { listVendorRequests } from "../api/vendor";
import { ServiceIcon } from "../components/ServiceIcon";
import { StatusBadge } from "../components/StatusBadge";
import { useVendorAuth } from "../hooks/useVendorAuth";
import type { VendorRequestItem, VendorScope } from "../types/vendor";
import { serviceIconType } from "../utils/serviceIcons";

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
  const { name, logout } = useVendorAuth();
  const [scope, setScope] = useState<VendorScope>("pending");
  const [items, setItems] = useState<VendorRequestItem[]>([]);
  const [counts, setCounts] = useState<Record<VendorScope, number>>({
    pending: 0,
    orders: 0,
    all: 0,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(
    (next: VendorScope) => {
      setLoading(true);
      setError("");
      listVendorRequests(next)
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
    [navigate],
  );

  useEffect(() => {
    load(scope);
  }, [load, scope]);

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
        {!loading &&
          !error &&
          items.map((item) => (
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
