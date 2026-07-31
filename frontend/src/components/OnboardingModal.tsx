import { useRef, useState } from "react";
import { Mascot } from "./Mascot";
import { ServiceIcon, type ServiceIconType } from "./ServiceIcon";

interface Slide {
  icon: ServiceIconType;
  title: string;
  description: string;
}

// M13 導引內容：①平台服務類型 ②如何送出諮詢單 ③如何追蹤訂單進度 ④語音/對話輸入功能介紹。
// 新增頁面時記得同步提高 useOnboarding.ts 的 ONBOARDING_VERSION，讓已完成舊版本的
// 使用者能重新看到差異式導引。
const SLIDES: Slide[] = [
  {
    icon: "cleaning",
    title: "多元到府服務任你選",
    description: "水電修繕、洗衣機清洗、冷氣清洗、居家清潔，還有餐廳訂位、美食外送與包裹寄送，都能在這裡一次搞定。",
  },
  {
    icon: "chat",
    title: "說出需求，AI 管家幫你送單",
    description: "點選服務卡片填單，或直接跟 AI 管家對話，管家會協助整理需求並送出諮詢單，不用自己填一大堆表格。",
  },
  {
    icon: "clock",
    title: "隨時掌握訂單進度",
    description: "到「我的服務」就能看到每筆案件目前的狀態，從送出、確認到完成，進度一目了然。",
  },
  {
    icon: "mic",
    title: "也能用語音說出需求",
    description: "不想打字也沒問題，點下麥克風按鈕直接用說話的方式告訴 AI 管家你想要什麼服務。",
  },
];

interface Props {
  /** 跳過或看完最後一頁都視為「已完成導引」，見設計書：後續登入不再自動彈出。 */
  onComplete: () => void;
}

/**
 * 首次登入的全螢幕導引卡片（M13）。可左右滑動、點擊「下一步」，含跳過按鈕。
 *
 * 配色一律引用語意色 Token（Requirement 6.6），Light/Dark 共用同一份 className。
 * 底層改用不透明的 `--color-surface`：此為覆蓋整個視窗的全螢幕層，若沿用半透明的
 * `--color-primary-soft`（Dark 模式為 16% 半透明藍）會讓下層畫面透出來、內容無法閱讀。
 */
export function OnboardingModal({ onComplete }: Props) {
  const [index, setIndex] = useState(0);
  const touchStartX = useRef<number | null>(null);
  const isLast = index === SLIDES.length - 1;

  function goTo(next: number) {
    setIndex(Math.max(0, Math.min(SLIDES.length - 1, next)));
  }

  function handleNext() {
    if (isLast) {
      onComplete();
    } else {
      goTo(index + 1);
    }
  }

  function handleTouchStart(e: React.TouchEvent) {
    touchStartX.current = e.touches[0].clientX;
  }

  function handleTouchEnd(e: React.TouchEvent) {
    if (touchStartX.current === null) return;
    const deltaX = e.changedTouches[0].clientX - touchStartX.current;
    touchStartX.current = null;
    const SWIPE_THRESHOLD = 48;
    if (deltaX <= -SWIPE_THRESHOLD) goTo(index + 1);
    else if (deltaX >= SWIPE_THRESHOLD) goTo(index - 1);
  }

  const slide = SLIDES[index];

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="新手導引"
      className="fixed inset-0 z-[60] flex flex-col bg-[var(--color-surface)]"
    >
      <div className="flex justify-end px-5 pt-6">
        <button
          type="button"
          onClick={onComplete}
          className="rounded-full px-4 py-2 text-sm font-bold text-[var(--color-muted-foreground)] transition hover:text-[var(--color-primary)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]"
        >
          跳過
        </button>
      </div>

      <div
        className="flex flex-1 flex-col items-center justify-center px-8 text-center"
        onTouchStart={handleTouchStart}
        onTouchEnd={handleTouchEnd}
      >
        <div className="flex h-40 w-40 items-center justify-center rounded-full bg-[var(--color-primary-soft)] shadow-xl">
          <Mascot size={92} />
        </div>
        <span className="mt-6 flex h-14 w-14 items-center justify-center rounded-2xl bg-[var(--color-primary)] text-[var(--color-on-primary)]">
          <ServiceIcon type={slide.icon} size={28} />
        </span>
        <h2 className="mt-5 text-2xl font-black text-[var(--color-foreground)]">{slide.title}</h2>
        <p className="mt-3 max-w-xs text-base leading-7 text-[var(--color-muted-foreground)]">
          {slide.description}
        </p>
      </div>

      <div className="flex items-center justify-center gap-2 pb-6">
        {SLIDES.map((s, i) => (
          <button
            key={s.title}
            type="button"
            aria-label={`前往第 ${i + 1} 頁`}
            aria-current={i === index}
            onClick={() => goTo(i)}
            className={`h-2 rounded-full transition-all ${
              i === index
                ? "w-6 bg-[var(--color-primary)]"
                : "w-2 bg-[var(--color-muted-foreground)]"
            }`}
          />
        ))}
      </div>

      <div className="px-5 pb-10">
        <button
          type="button"
          onClick={handleNext}
          className="w-full rounded-2xl bg-[var(--color-primary)] py-4 text-lg font-black text-[var(--color-on-primary)] shadow-lg transition hover:bg-[var(--color-primary-hover)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]"
        >
          {isLast ? "開始使用" : "下一步"}
        </button>
      </div>
    </div>
  );
}
