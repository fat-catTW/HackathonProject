import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { listRequests } from "../api/requests";
import { RequestCard } from "../components/RequestCard";
import { useAuth } from "../hooks/useAuth";
import type { RequestListItem } from "../types/request";

export function HomePage() {
  const { name, logout } = useAuth();
  const navigate = useNavigate();
  const [items, setItems] = useState<RequestListItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listRequests()
      .then((response) => setItems(response.items))
      .catch(() => navigate("/login"))
      .finally(() => setLoading(false));
  }, [navigate]);

  return (
    <main className="mx-auto max-w-md px-5 pb-16 pt-10">
      <header className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-black">你好，{name}</h1>
          <p className="mt-1 text-gray-500">查看你的申請進度，或直接新增一筆服務需求。</p>
        </div>
        <button
          type="button"
          onClick={() => {
            logout();
            navigate("/login");
          }}
          className="rounded-full px-3 py-1.5 text-sm text-gray-400 hover:text-ink"
        >
          登出
        </button>
      </header>

      <button
        type="button"
        onClick={() => navigate("/new")}
        className="mt-8 flex w-full items-center gap-4 rounded-3xl bg-pine p-5 text-left text-white shadow-lg transition hover:bg-pine-dark focus-visible:outline focus-visible:outline-4 focus-visible:outline-pine-soft"
      >
        <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-white/15">
          <svg viewBox="0 0 24 24" fill="currentColor" className="h-7 w-7" aria-hidden>
            <path d="M12 14a3 3 0 0 0 3-3V6a3 3 0 1 0-6 0v5a3 3 0 0 0 3 3Z" />
            <path d="M5 11a1 1 0 1 1 2 0 5 5 0 0 0 10 0 1 1 0 1 1 2 0 7 7 0 0 1-6 6.93V20h2a1 1 0 1 1 0 2H9a1 1 0 1 1 0-2h2v-2.07A7 7 0 0 1 5 11Z" />
          </svg>
        </span>
        <span>
          <span className="block text-lg font-bold">新增服務申請</span>
          <span className="block text-sm text-white/80">
            直接用對話或語音描述需求，管家會幫你整理成表單並送件。
          </span>
        </span>
      </button>

      <section className="mt-10">
        <h2 className="text-lg font-bold">我的案件</h2>
        <div className="mt-4 space-y-3">
          {loading && <p className="text-gray-400">載入中...</p>}
          {!loading && items.length === 0 && (
            <p className="rounded-2xl border border-dashed border-pine-soft p-6 text-center text-gray-400">
              目前還沒有案件。按上方按鈕就可以開始建立第一筆申請。
            </p>
          )}
          {items.map((item) => (
            <RequestCard key={item.request_id} item={item} />
          ))}
        </div>
      </section>
    </main>
  );
}
