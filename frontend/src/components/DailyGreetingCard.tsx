import { useNavigate } from "react-router-dom";
import type { DailyGreeting, GreetingItem } from "../api/greeting";
import { serviceIconForId } from "../utils/serviceIcons";
import { Mascot } from "./Mascot";
import { ServiceIcon, type ServiceIconType } from "./ServiceIcon";

interface Props {
  card: DailyGreeting;
  /** 關閉卡片；同時記下「今天已經看過」，一天只跳一次。 */
  onDismiss: () => void;
}

/**
 * 每則提醒的視覺：今天要發生的用主色、需要本人動手的用警示色、
 * 其餘的用資訊色。全部走語意色 Token，Light/Dark 共用同一份 className。
 */
const KIND_TONE: Record<GreetingItem["kind"], { soft: string; ink: string; badge: string }> = {
  today: { soft: "var(--color-primary-soft)", ink: "var(--color-primary)", badge: "今天" },
  action_needed: { soft: "var(--color-warning-soft)", ink: "var(--color-warning)", badge: "待處理" },
  upcoming: { soft: "var(--color-info-soft)", ink: "var(--color-info)", badge: "即將到來" },
  in_progress: { soft: "var(--color-info-soft)", ink: "var(--color-info)", badge: "進行中" },
  followup: { soft: "var(--color-success-soft)", ink: "var(--color-success)", badge: "已完成" },
};

/** 時段對應的裝飾圖示：白天太陽、夜裡月亮。 */
function periodIcon(period: DailyGreeting["period"]): ServiceIconType {
  return period === "evening" || period === "night" ? "moon" : "sun";
}

/**
 * 每日問候卡。
 *
 * 產品規格是「每天早上 7 點自動推播」；Demo 版沒有真的排程與 Web Push，改成一開
 * App 就跳這張卡（一天一次，見 useDailyGreeting）。卡片內容全部由後端從使用者
 * 自己的案件算出來，所以即使推播管道是假的，卡片上寫的每一句都是真的。
 */
export function DailyGreetingCard({ card, onDismiss }: Props) {
  const navigate = useNavigate();

  function goTo(path: string) {
    onDismiss();
    navigate(path);
  }

  function askButler(prompt: string) {
    onDismiss();
    navigate("/new", { state: { autoMessage: prompt } });
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="今日問候"
      className="fixed inset-0 z-[60] flex items-center justify-center px-4 py-6"
    >
      <button
        type="button"
        aria-label="關閉今日問候"
        onClick={onDismiss}
        className="absolute inset-0 bg-[var(--color-scrim)]"
      />

      <div className="relative flex max-h-full w-full max-w-md flex-col overflow-hidden rounded-[28px] bg-[var(--color-surface)] shadow-2xl">
        {/*
          卡頭沿用首頁 header 的多層柔光漸層，讓這張卡一看就知道是同一位管家送來的，
          而不是別的系統彈出來的通知視窗。
        */}
        <header
          className="relative shrink-0 overflow-hidden px-6 pb-6 pt-7 text-[var(--color-on-primary)]"
          style={{
            backgroundImage: `
              radial-gradient(55% 45% at 85% 5%, rgba(255,255,255,0.5) 0%, transparent 70%),
              radial-gradient(70% 60% at 8% 105%, var(--color-secondary) 0%, transparent 70%),
              linear-gradient(165deg, var(--color-primary-accent) 0%, var(--color-primary) 100%)
            `,
          }}
        >
          <Mascot
            size={130}
            tone="inverted"
            className="pointer-events-none absolute -bottom-7 -right-6 opacity-[0.16]"
          />
          <div className="relative flex items-center justify-between gap-3">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-white/25 px-3 py-1.5 text-xs font-bold">
              <ServiceIcon type={periodIcon(card.period)} size={14} />
              每天 {card.push_time} 為你整理
            </span>
            <button
              type="button"
              onClick={onDismiss}
              aria-label="關閉"
              className="flex h-9 w-9 items-center justify-center rounded-full bg-white/25 transition hover:bg-white/35 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-on-primary)]"
            >
              <ServiceIcon type="close" size={18} />
            </button>
          </div>
          <p className="relative mt-4 text-xs font-semibold opacity-90">{card.date_label}</p>
          <h2 className="relative mt-1 text-2xl font-black leading-tight">{card.greeting}</h2>
          <p className="relative mt-2 text-sm font-semibold leading-6 opacity-95">{card.message}</p>
        </header>

        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5">
          <p className="text-sm font-extrabold text-[var(--color-foreground)]">{card.headline}</p>

          {card.items.length > 0 && (
            <ul className="mt-3 grid gap-2.5">
              {card.items.map((item) => {
                const tone = KIND_TONE[item.kind];
                return (
                  <li key={item.id}>
                    <button
                      type="button"
                      onClick={() => goTo(item.action_path)}
                      className="flex w-full items-center gap-3 rounded-2xl bg-[var(--color-canvas)] p-3 text-left transition hover:-translate-y-0.5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand"
                    >
                      <span
                        aria-hidden
                        className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full"
                        style={{ background: tone.soft, color: tone.ink }}
                      >
                        <ServiceIcon type={serviceIconForId(item.service_id)} size={20} />
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="flex items-center gap-2">
                          <span
                            className="rounded-full px-2 py-0.5 text-[11px] font-bold"
                            style={{ background: tone.soft, color: tone.ink }}
                          >
                            {tone.badge}
                          </span>
                          <span className="truncate text-sm font-extrabold text-[var(--color-foreground)]">
                            {item.title}
                          </span>
                        </span>
                        <span className="mt-1 block truncate text-xs font-semibold text-[var(--color-muted-foreground)]">
                          {item.detail}
                        </span>
                      </span>
                      <span className="flex shrink-0 items-center gap-0.5 text-xs font-bold text-brand">
                        {item.action_label}
                        <ServiceIcon type="chevronRight" size={12} />
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}

          {card.suggestions.length > 0 && (
            <>
              <p className="mt-5 text-xs font-bold text-[var(--color-muted-foreground)]">
                也可以直接交給我
              </p>
              <div className="mt-2 flex flex-wrap gap-2">
                {card.suggestions.map((suggestion) => (
                  <button
                    key={suggestion.service_id}
                    type="button"
                    onClick={() => askButler(suggestion.prompt)}
                    className="inline-flex min-h-[40px] items-center gap-1 rounded-full border border-[var(--color-border)] bg-[var(--color-surface)] px-3.5 text-sm font-bold text-[var(--color-foreground)] transition hover:border-brand hover:text-brand focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand"
                  >
                    <ServiceIcon type={serviceIconForId(suggestion.service_id)} size={14} />
                    {suggestion.label}
                  </button>
                ))}
              </div>
            </>
          )}
        </div>

        <div className="shrink-0 border-t border-[var(--color-border)] px-5 py-4">
          <button
            type="button"
            onClick={onDismiss}
            className="w-full rounded-2xl bg-brand py-3.5 text-base font-black text-[var(--color-on-primary)] transition hover:opacity-90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand"
          >
            知道了
          </button>
        </div>
      </div>
    </div>
  );
}
