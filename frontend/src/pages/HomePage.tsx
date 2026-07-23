import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { listRequests } from "../api/requests";
import { Mascot } from "../components/Mascot";
import { RequestCard } from "../components/RequestCard";
import { ServiceIcon, type ServiceIconType } from "../components/ServiceIcon";
import { useAuth } from "../hooks/useAuth";
import type { RequestListItem } from "../types/request";

const QUICK_SERVICES: { name: string; icon: ServiceIconType }[] = [
  { name: "冷氣清潔", icon: "aircon" },
  { name: "水電維修", icon: "plumbing" },
  { name: "家電安裝", icon: "appliance" },
  { name: "居家清潔", icon: "cleaning" },
  { name: "除蟲", icon: "pest" },
  { name: "搬家", icon: "moving" },
];

const STATUS_ORDER: Record<string, number> = {
  SUBMITTED: 0, PENDING_PROVIDER: 0, CONFIRMED: 1, IN_PROGRESS: 1, COMPLETED: 2, CANCELLED: 3, FAILED: 3,
};

export function HomePage() {
  const { name, logout } = useAuth();
  const navigate = useNavigate();
  const [items, setItems] = useState<RequestListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [showPicker, setShowPicker] = useState(false);

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

  function startChat(autoMessage?: string) {
    navigate("/new", { state: autoMessage ? { autoMessage } : undefined });
  }

  return (
    <main className="mx-auto max-w-md bg-canvas px-5 pb-16 pt-10">
      <header className="flex items-center gap-3.5">
        <button
          type="button"
          onClick={() => {
            logout();
            navigate("/login");
          }}
          aria-label="登出"
          className="flex-none text-gray-500"
        >
          <ServiceIcon type="back" size={22} />
        </button>
        <Mascot size={50} />
        <div>
          <h1 className="text-2xl font-black">您好，{name}</h1>
          <p className="mt-1 text-lg text-gray-500">今天需要什麼協助？</p>
        </div>
      </header>

      <div className="relative mt-8 overflow-hidden rounded-3xl bg-gradient-to-br from-brand to-brand-dark p-8 text-center shadow-lg">
        <button
          type="button"
          onClick={() => startChat()}
          aria-label="點擊，說出您的需求"
          className="mx-auto flex h-24 w-24 items-center justify-center rounded-full border-4 border-white/50 bg-paper2"
        >
          <Mascot size={64} />
        </button>
        <div className="mt-4 text-lg font-bold text-white">點擊並說出需求</div>
        <div className="mt-1.5 text-sm leading-relaxed text-white/75">
          例如：「我要預約明天下午洗兩台冷氣」
        </div>
        <button
          type="button"
          onClick={() => startChat()}
          className="mt-5 w-full rounded-2xl bg-paper2 py-4 text-base font-bold text-brand-dark"
        >
          直接輸入文字說明需求
        </button>
        <button
          type="button"
          onClick={() => setShowPicker(true)}
          className="mt-3.5 inline-flex items-center gap-2 whitespace-nowrap rounded-full border border-accent/60 bg-accent/20 px-4.5 py-2 text-sm font-bold text-white"
        >
          <ServiceIcon type="appliance" size={16} />
          常見服務快速選
        </button>
      </div>

      {showPicker && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[rgba(10,25,40,0.45)] p-6">
          <button
            type="button"
            aria-label="關閉"
            onClick={() => setShowPicker(false)}
            className="absolute inset-0"
          />
          <div className="relative w-full max-w-[360px] rounded-2xl bg-white p-5.5 shadow-xl">
            <div className="mb-3.5 flex items-center justify-between">
              <span className="text-lg font-black">選擇常見服務</span>
              <button type="button" onClick={() => setShowPicker(false)} className="text-gray-400">
                <ServiceIcon type="close" size={22} />
              </button>
            </div>
            <div className="grid grid-cols-2 gap-2.5">
              {QUICK_SERVICES.map((s) => (
                <button
                  key={s.name}
                  type="button"
                  onClick={() => {
                    setShowPicker(false);
                    startChat(s.name);
                  }}
                  className="flex items-center gap-2 rounded-2xl border border-gray-200 bg-canvas px-3.5 py-3.5 text-left text-sm font-bold"
                >
                  <span className="flex-none text-brand"><ServiceIcon type={s.icon} size={20} /></span>
                  {s.name}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      <section className="mt-10">
        <h2 className="text-lg font-bold">我的服務</h2>
        <div className="mt-4 space-y-3.5">
          {loading && <p className="text-gray-400">載入中⋯</p>}
          {!loading && items.length === 0 && (
            <p className="rounded-2xl border border-dashed border-gray-300 p-6 text-center text-gray-400">
              還沒有服務案件。點上方按鈕，說出您的需求開始。
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
