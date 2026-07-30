import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { listRequests } from "../api/requests";
import { RequestCard } from "../components/RequestCard";
import { ServiceIcon } from "../components/ServiceIcon";
import { ButlerLauncher } from "../components/ButlerLauncher";
import type { RequestListItem } from "../types/request";

const STATUS_ORDER: Record<string, number> = {
  SUBMITTED: 0,
  PENDING_PROVIDER: 0,
  CONFIRMED: 1,
  IN_PROGRESS: 1,
  COMPLETED: 2,
  CANCELLED: 3,
  FAILED: 3,
};

export function MyServicesPage() {
  const navigate = useNavigate();
  const [items, setItems] = useState<RequestListItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listRequests()
      .then((r) =>
        setItems(
          [...r.items].sort(
            (a, b) => (STATUS_ORDER[a.status] ?? 9) - (STATUS_ORDER[b.status] ?? 9),
          ),
        ),
      )
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
            className="flex h-11 w-11 items-center justify-center rounded-full bg-white text-gray-500 shadow-sm transition hover:text-brand"
          >
            <ServiceIcon type="back" size={20} />
          </button>
          <div>
            <p className="text-sm font-semibold text-brand">服務紀錄</p>
            <h1 className="text-2xl font-black text-slate-900">我的服務</h1>
          </div>
        </header>

        <section className="mt-8 rounded-[28px] bg-white p-5 shadow-sm">
          <h2 className="text-lg font-black text-slate-900">查看案件與進度</h2>
          <p className="mt-2 text-sm leading-6 text-slate-500">
            這裡會列出你已建立的服務需求，包含目前狀態與最近更新時間。
          </p>
        </section>

        <section className="mt-6 space-y-3.5">
          {loading && (
            <p className="rounded-2xl bg-white p-5 text-center text-gray-400 shadow-sm">
              正在載入服務紀錄…
            </p>
          )}
          {!loading && items.length === 0 && (
            <p className="rounded-2xl border border-dashed border-gray-300 bg-white p-6 text-center text-gray-400">
              目前還沒有服務案件，按下下方的 AI 管家按鈕就能開始建立。
            </p>
          )}
          {items.map((item) => (
            <RequestCard key={item.request_id} item={item} />
          ))}
        </section>
      </main>

      <ButlerLauncher currentPageId="my_services" />
    </>
  );
}
