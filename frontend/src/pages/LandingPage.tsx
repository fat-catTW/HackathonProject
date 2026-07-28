import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { Mascot } from "../components/Mascot";
import { ServiceIcon } from "../components/ServiceIcon";
import { THEMES } from "../hooks/useTheme";

gsap.registerPlugin(ScrollTrigger);

const HIGHLIGHTS = [
  {
    icon: "mic" as const,
    title: "用說的就能建立需求",
    body: "直接描述你想做的事，AI 管家會幫你辨識服務、補齊欄位，整理成可以確認的申請內容。",
  },
  {
    icon: "check" as const,
    title: "表單同步整理完成",
    body: "需求、日期、時段與地址會同步顯示在畫面上，你可以自己核對、自己修改、自己送出。",
  },
  {
    icon: "chat" as const,
    title: "串接真正的 AWS 服務流程",
    body: "背後接上 Bedrock、長期記憶與 DynamoDB，這個 demo 不只是聊天畫面，而是能真的把案件送出去。",
  },
];

const SERVICES = [
  { icon: "plumbing" as const, name: "水電修繕" },
  { icon: "appliance" as const, name: "洗衣機清洗" },
  { icon: "aircon" as const, name: "冷氣清洗" },
  { icon: "cleaning" as const, name: "居家清潔" },
];

export function LandingPage() {
  const navigate = useNavigate();
  const rootRef = useRef<HTMLDivElement>(null);
  const [previewId, setPreviewId] = useState(THEMES[0].id);
  const previewTheme = THEMES.find((t) => t.id === previewId) ?? THEMES[0];

  useEffect(() => {
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReducedMotion) return;

    const ctx = gsap.context(() => {
      gsap.from(".ld-nav", { opacity: 0, y: -16, duration: 0.6, ease: "power2.out" });
      gsap.from(".ld-hero-title-line", {
        opacity: 0,
        y: 24,
        duration: 0.7,
        stagger: 0.1,
        ease: "power2.out",
        delay: 0.05,
      });
      gsap.from(".ld-hero-sub", { opacity: 0, y: 16, duration: 0.6, ease: "power2.out", delay: 0.3 });
      gsap.from(".ld-hero-cta", { opacity: 0, y: 16, duration: 0.6, stagger: 0.08, ease: "power2.out", delay: 0.42 });
      gsap.from(".ld-hero-panel", { opacity: 0, y: 24, duration: 0.7, ease: "power2.out", delay: 0.2 });
      gsap.utils.toArray<HTMLElement>(".ld-highlight-row").forEach((row, i) => {
        gsap.from(row, {
          opacity: 0,
          y: 20,
          duration: 0.5,
          delay: i * 0.06,
          ease: "power2.out",
          scrollTrigger: { trigger: row, start: "top 88%" },
        });
      });
      gsap.from(".ld-services-block", {
        opacity: 0,
        y: 28,
        duration: 0.6,
        ease: "power2.out",
        scrollTrigger: { trigger: ".ld-services-block", start: "top 86%" },
      });
      gsap.utils.toArray<HTMLElement>(".ld-service-card").forEach((card, i) => {
        gsap.from(card, {
          opacity: 0,
          y: 18,
          duration: 0.45,
          delay: i * 0.05,
          ease: "power2.out",
          scrollTrigger: { trigger: card, start: "top 92%" },
        });
      });
    }, rootRef);

    return () => ctx.revert();
  }, []);

  return (
    <main ref={rootRef} className="min-h-dvh overflow-hidden bg-paper text-ink">
      <div
        className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-[30rem]"
        style={{ background: "radial-gradient(ellipse at top, var(--color-brand-soft) 0%, transparent 65%)" }}
      />

      <section className="mx-auto max-w-6xl px-6 pb-24 pt-8 md:px-10 lg:px-12">
        <header className="ld-nav flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Mascot size={40} />
            <p className="text-lg font-black text-ink">AI 智慧生活服務管家</p>
          </div>
          <button
            type="button"
            onClick={() => navigate("/login")}
            className="rounded-2xl border-2 border-transparent bg-white px-4 py-2.5 text-sm font-bold text-brand shadow-sm transition hover:border-brand focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand"
          >
            進入系統
          </button>
        </header>

        <section className="grid items-center gap-14 pb-16 pt-14 lg:grid-cols-[1.05fr_0.95fr] lg:pt-20">
          <div>
            <h1 className="max-w-2xl text-balance text-[clamp(2.4rem,5.4vw,4.2rem)] font-black leading-[1.08] text-ink">
              <span className="ld-hero-title-line block">把生活服務申請</span>
              <span className="ld-hero-title-line block">變成一段自然對話</span>
            </h1>
            <p className="ld-hero-sub mt-6 max-w-xl text-lg leading-8 text-slate-600">
              跟熟悉的家人聊聊就好：說出你想做什麼，AI 管家會把服務、日期、地址都整理好，最後由你親自確認再送出。
            </p>
            <div className="mt-9 flex flex-wrap gap-4">
              <button
                type="button"
                onClick={() => navigate("/login")}
                className="ld-hero-cta rounded-2xl bg-brand px-7 py-4 text-base font-bold text-white shadow-[0_18px_45px_-12px_var(--color-brand)] transition hover:bg-brand-dark focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand"
              >
                開始體驗
              </button>
              <button
                type="button"
                onClick={() => navigate("/home")}
                className="ld-hero-cta rounded-2xl border-2 border-gray-200 bg-white px-7 py-4 text-base font-bold text-brand transition hover:border-brand focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand"
              >
                查看案件列表
              </button>
            </div>
          </div>

          <div className="ld-hero-panel">
            <div
              className="rounded-[32px] border border-gray-100 p-8 text-center shadow-[0_24px_60px_-24px_rgba(15,23,42,0.25)] transition-colors duration-500"
              style={{ backgroundColor: previewTheme.brandSoft }}
            >
              <Mascot
                size={104}
                className="mx-auto"
                bodyColor={previewTheme.brand}
                highlightColor={previewTheme.mascotHighlight}
              />
              <h2 className="mt-5 text-xl font-black text-ink">多顏色的小幫手</h2>
              <p className="mt-2 text-sm leading-6 text-slate-600">
                登入後可以隨時切換管家的顏色，先在這裡點一個試試看。
              </p>
              <div className="mt-6 flex justify-center gap-3">
                {THEMES.map((t) => {
                  const active = t.id === previewId;
                  return (
                    <button
                      key={t.id}
                      type="button"
                      aria-label={`預覽${t.name}`}
                      aria-pressed={active}
                      onClick={() => setPreviewId(t.id)}
                      className={`h-11 w-11 rounded-full border-2 transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand ${
                        active ? "scale-110 border-ink/70" : "border-white/60 hover:scale-105"
                      }`}
                      style={{ backgroundColor: t.brand }}
                    />
                  );
                })}
              </div>
            </div>
          </div>
        </section>

        <section className="mt-4 divide-y divide-gray-100 border-y border-gray-100">
          {HIGHLIGHTS.map((item) => (
            <div key={item.title} className="ld-highlight-row flex items-start gap-5 py-7">
              <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-brand-soft text-brand">
                <ServiceIcon type={item.icon} size={24} />
              </span>
              <div>
                <h2 className="text-lg font-black text-ink">{item.title}</h2>
                <p className="mt-1.5 max-w-2xl leading-7 text-slate-600">{item.body}</p>
              </div>
            </div>
          ))}
        </section>

        <section className="ld-services-block mt-16 rounded-[32px] bg-canvas p-8">
          <div className="flex flex-col gap-8 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <h2 className="text-2xl font-black text-ink">目前可用服務</h2>
              <p className="mt-3 max-w-2xl leading-7 text-slate-600">
                服務辨識、表單整理與案件建立已經串起來，適合直接展示完整體驗。
              </p>
            </div>
            <button
              type="button"
              onClick={() => navigate("/login")}
              className="shrink-0 rounded-2xl bg-brand px-6 py-3.5 text-sm font-bold text-white transition hover:bg-brand-dark focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand"
            >
              直接登入測試
            </button>
          </div>

          <div className="mt-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {SERVICES.map((service) => (
              <div
                key={service.name}
                className="ld-service-card rounded-2xl border border-gray-100 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
              >
                <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-soft text-brand">
                  <ServiceIcon type={service.icon} size={24} />
                </span>
                <p className="mt-4 text-lg font-bold text-ink">{service.name}</p>
              </div>
            ))}
          </div>
        </section>
      </section>
    </main>
  );
}
