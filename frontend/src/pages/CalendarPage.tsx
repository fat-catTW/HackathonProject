import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getCalendar, type CalendarDay } from "../api/calendar";
import { BottomNav } from "../components/BottomNav";
import { ServiceIcon } from "../components/ServiceIcon";
import { StatusBadge } from "../components/StatusBadge";

export function CalendarPage() {
  const navigate = useNavigate();
  const [days, setDays] = useState<CalendarDay[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getCalendar()
      .then((r) => setDays(r.days))
      .finally(() => setLoading(false));
  }, []);

  return (
    <main className="mx-auto min-h-dvh max-w-md bg-[var(--color-canvas)] px-5 pb-32 pt-8">
      <div className="mb-6 flex items-center gap-3">
        <button
          type="button"
          onClick={() => navigate(-1)}
          aria-label="返回"
          className="flex h-11 w-11 items-center justify-center rounded-full bg-[var(--color-surface)] text-[var(--color-foreground)] shadow-sm"
        >
          <ServiceIcon type="back" size={20} />
        </button>
        <h1 className="text-2xl font-black text-[var(--color-foreground)]">行事曆</h1>
      </div>

      {loading && <p className="text-[var(--color-muted-foreground)]">載入中…</p>}
      {!loading && days.length === 0 && (
        <p className="text-[var(--color-muted-foreground)]">目前沒有已排定日期的服務。</p>
      )}

      <div className="flex flex-col gap-5">
        {days.map((day) => (
          <section key={day.date}>
            <h2 className="mb-2.5 text-base font-extrabold text-[var(--color-foreground)]">{day.date}</h2>
            <div className="flex flex-col gap-2.5">
              {day.items.map((item) => (
                <button
                  key={item.request_id}
                  type="button"
                  onClick={() => navigate(`/requests/${item.request_id}`)}
                  className="flex items-center justify-between rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-4 text-left shadow-sm"
                >
                  <span className="font-bold text-[var(--color-foreground)]">{item.service_name}</span>
                  <StatusBadge status={item.status} label={item.status_label} />
                </button>
              ))}
            </div>
          </section>
        ))}
      </div>

      <BottomNav />
    </main>
  );
}
