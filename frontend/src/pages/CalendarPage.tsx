import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getCalendar, type CalendarDay } from "../api/calendar";
import { BottomNav } from "../components/BottomNav";
import { ServiceIcon } from "../components/ServiceIcon";

const WEEKDAY_LABELS = ["一", "二", "三", "四", "五", "六", "日"];

/** 事件色塊沿用 HomePage 服務捷徑列同一組 Token 順序，依服務名稱雜湊挑色，讓同一服務在不同日期顏色一致。 */
const EVENT_TONES = [
  { soft: "var(--color-primary-soft)", ink: "var(--color-primary)" },
  { soft: "var(--color-secondary-soft)", ink: "var(--color-secondary)" },
  { soft: "var(--color-tertiary-soft)", ink: "var(--color-tertiary)" },
  { soft: "var(--color-info-soft)", ink: "var(--color-info)" },
] as const;

function toneForService(name: string) {
  let hash = 0;
  for (let i = 0; i < name.length; i += 1) hash = (hash * 31 + name.charCodeAt(i)) >>> 0;
  return EVENT_TONES[hash % EVENT_TONES.length];
}

function dateKey(date: Date) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

/** 產生月曆網格：週一為每列第一欄，並補上前後月份的日期填滿完整週數（對齊 Google 日曆版面）。 */
function buildMonthGrid(year: number, month: number): Date[] {
  const firstOfMonth = new Date(year, month, 1);
  const mondayOffset = (firstOfMonth.getDay() + 6) % 7;
  const gridStart = new Date(year, month, 1 - mondayOffset);
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const totalCells = Math.ceil((mondayOffset + daysInMonth) / 7) * 7;
  return Array.from({ length: totalCells }, (_, i) => {
    const d = new Date(gridStart);
    d.setDate(gridStart.getDate() + i);
    return d;
  });
}

export function CalendarPage() {
  const navigate = useNavigate();
  const [days, setDays] = useState<CalendarDay[]>([]);
  const [loading, setLoading] = useState(true);
  const today = useMemo(() => new Date(), []);
  const [viewYear, setViewYear] = useState(today.getFullYear());
  const [viewMonth, setViewMonth] = useState(today.getMonth());

  useEffect(() => {
    getCalendar()
      .then((r) => setDays(r.days))
      .finally(() => setLoading(false));
  }, []);

  const itemsByDate = useMemo(() => {
    const map = new Map<string, CalendarDay["items"]>();
    for (const day of days) map.set(day.date, day.items);
    return map;
  }, [days]);

  const gridDays = useMemo(() => buildMonthGrid(viewYear, viewMonth), [viewYear, viewMonth]);
  const todayKey = dateKey(today);
  const isCurrentMonth = viewYear === today.getFullYear() && viewMonth === today.getMonth();

  function goToMonth(offset: number) {
    const next = new Date(viewYear, viewMonth + offset, 1);
    setViewYear(next.getFullYear());
    setViewMonth(next.getMonth());
  }

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

      <div className="mb-4 flex items-center justify-between">
        <button
          type="button"
          onClick={() => goToMonth(-1)}
          aria-label="上個月"
          className="flex h-11 w-11 items-center justify-center rounded-full bg-[var(--color-surface)] text-[var(--color-foreground)] shadow-sm"
        >
          <ServiceIcon type="back" size={16} />
        </button>
        <div className="flex items-center gap-2">
          <span className="text-lg font-black text-[var(--color-foreground)]">
            {viewYear}年{viewMonth + 1}月
          </span>
          {!isCurrentMonth && (
            <button
              type="button"
              onClick={() => {
                setViewYear(today.getFullYear());
                setViewMonth(today.getMonth());
              }}
              className="rounded-full bg-[var(--color-primary-soft)] px-3 py-1.5 text-xs font-bold text-[var(--color-primary)]"
            >
              今天
            </button>
          )}
        </div>
        <button
          type="button"
          onClick={() => goToMonth(1)}
          aria-label="下個月"
          className="flex h-11 w-11 items-center justify-center rounded-full bg-[var(--color-surface)] text-[var(--color-foreground)] shadow-sm"
        >
          <ServiceIcon type="chevronRight" size={16} />
        </button>
      </div>

      {loading && <p className="text-[var(--color-muted-foreground)]">載入中…</p>}

      {!loading && (
        <div className="overflow-hidden rounded-3xl border border-[var(--color-border)] bg-[var(--color-surface)] shadow-sm">
          <div className="grid grid-cols-7 border-b border-[var(--color-border)]">
            {WEEKDAY_LABELS.map((label) => (
              <div
                key={label}
                className="py-2.5 text-center text-xs font-bold text-[var(--color-muted-foreground)]"
              >
                {label}
              </div>
            ))}
          </div>
          <div className="grid grid-cols-7">
            {gridDays.map((date, index) => {
              const key = dateKey(date);
              const items = itemsByDate.get(key) ?? [];
              const inMonth = date.getMonth() === viewMonth;
              const isToday = key === todayKey;
              const isFirstRow = index < 7;
              const isFirstCol = index % 7 === 0;
              return (
                <div
                  key={key}
                  className={`min-h-[84px] border-[var(--color-border)] p-1.5 ${isFirstRow ? "" : "border-t"} ${isFirstCol ? "" : "border-l"}`}
                >
                  <span
                    className={`inline-flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold ${
                      isToday
                        ? "bg-[var(--color-primary)] text-[var(--color-on-primary)]"
                        : inMonth
                          ? "text-[var(--color-foreground)]"
                          : "text-[var(--color-muted-foreground)] opacity-50"
                    }`}
                  >
                    {date.getDate()}
                  </span>
                  <div className="mt-1 flex flex-col gap-1">
                    {items.map((item) => {
                      const tone = toneForService(item.service_name);
                      return (
                        <button
                          key={item.request_id}
                          type="button"
                          onClick={() => navigate(`/requests/${item.request_id}`)}
                          title={item.service_name}
                          className="w-full truncate rounded-md px-1.5 py-0.5 text-left text-[11px] font-bold leading-tight"
                          style={{ background: tone.soft, color: tone.ink }}
                        >
                          {item.service_name}
                        </button>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {!loading && days.length === 0 && (
        <p className="mt-4 text-center text-[var(--color-muted-foreground)]">目前沒有已排定日期的服務。</p>
      )}

      <BottomNav />
    </main>
  );
}
