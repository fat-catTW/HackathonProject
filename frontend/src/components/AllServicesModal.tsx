import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { SERVICES } from "../data/services";
import { SERVICE_TONES } from "../utils/serviceTones";
import { ServiceIcon } from "./ServiceIcon";

interface Props {
  onClose: () => void;
}

interface Point {
  x: number;
  y: number;
}

const ENTRY_SERVICES = SERVICES.filter((service) => !service.hidden);

/**
 * 「所有服務」視窗：管家頭像置中，服務圖示以他為圓心一圈排開、虛線連過去，
 * 呼應首頁 AI 管家入口的光暈圓形頭像，等於在這裡再次確認「這是管家在幫你導覽」。
 *
 * 圓的半徑用 ResizeObserver 量測容器實際寬高換算，而非寫死像素——手機寬度
 * 從 360px 到 max-w-md（448px）都要能把 9 個圖示排滿一圈不互相重疊。
 */
export function AllServicesModal({ onClose }: Props) {
  const navigate = useNavigate();
  const stageRef = useRef<HTMLDivElement>(null);
  const [positions, setPositions] = useState<Point[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    const el = stageRef.current;
    if (!el) return;

    function measure() {
      if (!el) return;
      const { width, height } = el.getBoundingClientRect();
      const cx = width / 2;
      const cy = height / 2;
      const radius = Math.min(width, height) / 2 - 48;
      setPositions(
        ENTRY_SERVICES.map((_, index) => {
          const angle = (Math.PI * 2 * index) / ENTRY_SERVICES.length - Math.PI / 2;
          return {
            x: cx + radius * Math.cos(angle),
            y: cy + radius * Math.sin(angle),
          };
        }),
      );
    }

    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const selected = ENTRY_SERVICES.find((service) => service.service_id === selectedId) ?? null;

  return (
    <section
      role="dialog"
      aria-modal="true"
      aria-label="所有服務"
      className="sheet-in flex max-h-[90dvh] w-full max-w-lg flex-col overflow-hidden rounded-[28px] bg-[var(--color-surface)] shadow-2xl"
    >
      <header className="flex shrink-0 items-center justify-between border-b border-[var(--color-border)] px-5 py-4">
        <div>
          <p className="text-sm font-bold text-brand">所有服務</p>
          <h2 className="mt-0.5 text-xl font-black text-[var(--color-foreground)]">選一個開始</h2>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="關閉所有服務視窗"
          className="flex h-10 w-10 items-center justify-center rounded-full bg-[var(--color-canvas)] text-[var(--color-muted-foreground)] transition hover:text-[var(--color-foreground)]"
        >
          <ServiceIcon type="close" size={18} />
        </button>
      </header>

      <div className="min-h-0 flex-1 overflow-y-auto">
        <div ref={stageRef} className="relative mx-auto mt-2 h-[420px] w-full max-w-[420px]">
          <svg aria-hidden className="pointer-events-none absolute inset-0 h-full w-full">
            {positions.map((point, index) => (
              <line
                key={ENTRY_SERVICES[index].service_id}
                className="radial-line"
                x1="50%"
                y1="50%"
                x2={point.x}
                y2={point.y}
                stroke="var(--color-primary-accent)"
                strokeWidth={1.5}
                strokeDasharray="3 5"
                strokeLinecap="round"
                style={{ animationDelay: `${80 + index * 45}ms` }}
              />
            ))}
          </svg>

          {/* 中央光暈頭像：跟首頁 AI 管家入口同一張圖、同一套光暈手法 */}
          <div className="orb-pop-in absolute left-1/2 top-1/2 h-[112px] w-[112px]">
            <span
              aria-hidden
              className="pointer-events-none absolute -inset-5 rounded-full opacity-70 blur-xl"
              style={{ background: "var(--color-primary-accent)" }}
            />
            <span
              aria-hidden
              className="pointer-events-none absolute -inset-1.5 rounded-full opacity-60 blur-md"
              style={{ background: "var(--color-primary)" }}
            />
            <div className="relative h-full w-full overflow-hidden rounded-full shadow-[0_16px_30px_-12px_var(--color-primary)]">
              <img
                src="/images/ai-companion.jpg"
                alt=""
                aria-hidden
                className="h-full w-full object-cover"
                style={{ objectPosition: "50% 25%" }}
              />
            </div>
          </div>

          {ENTRY_SERVICES.map((service, index) => {
            const point = positions[index];
            if (!point) return null;
            const tone = SERVICE_TONES[index % SERVICE_TONES.length];
            const isSelected = service.service_id === selectedId;
            return (
              <button
                key={service.service_id}
                type="button"
                onClick={() => setSelectedId(service.service_id)}
                aria-pressed={isSelected}
                style={{ left: point.x, top: point.y, animationDelay: `${140 + index * 45}ms` }}
                className="radial-pop absolute flex w-20 flex-col items-center gap-1.5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand"
              >
                <span
                  className="flex h-14 w-14 items-center justify-center rounded-full transition-shadow"
                  style={{
                    backgroundImage: `linear-gradient(145deg, var(--color-surface) 0%, ${tone.soft} 100%)`,
                    color: tone.ink,
                    boxShadow: isSelected
                      ? `0 0 0 3px var(--color-primary)`
                      : `inset 0 1px 1px rgba(255,255,255,0.8), 0 6px 14px -8px ${tone.ink}`,
                  }}
                >
                  <ServiceIcon type={service.icon} size={24} strokeWidth={2} />
                </span>
                <span className="line-clamp-2 text-center text-xs font-bold leading-tight text-[var(--color-foreground)]">
                  {service.title}
                </span>
              </button>
            );
          })}
        </div>

        {/* 管家對話泡泡：預設引導文字，點圖示後換成該服務說明＋開始申請 CTA */}
        <div className="px-5 pb-5 pt-3">
          <div className="rounded-[20px] bg-[var(--color-primary-soft)] p-4">
            <p className="text-base font-extrabold text-[var(--color-foreground)]">
              {selected ? selected.title : "請選擇想要的服務唷"}
            </p>
            <p className="mt-1 text-sm leading-6 text-[var(--color-muted-foreground)]">
              {selected ? selected.subtitle : "點一下圓圈裡的圖示，我來幫你介紹！"}
            </p>
            {selected && (
              <div className="mt-3 text-right">
                <button
                  type="button"
                  onClick={() => {
                    navigate(`/services/${selected.service_id}`);
                    onClose();
                  }}
                  className="inline-flex min-h-[40px] items-center gap-1 rounded-full bg-brand px-4 text-base font-bold text-[var(--color-on-primary)] transition hover:opacity-90"
                >
                  開始申請
                  <ServiceIcon type="chevronRight" size={16} />
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
