import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { Mascot } from "../components/Mascot";
import { ServiceIcon } from "../components/ServiceIcon";

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
    body: "需求、日期、時段與地址會同步顯示在畫面上，使用者可以自己核對、自己修改、自己送出。",
  },
  {
    icon: "chat" as const,
    title: "接上 AWS Agent 工作流",
    body: "支援 Bedrock、Memory、MCP Gateway 與 DynamoDB，讓這個 demo 不只是聊天畫面，而是真的能串流程。",
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

  useEffect(() => {
    const ctx = gsap.context(() => {
      gsap.from(".ld-nav", { opacity: 0, y: -18, duration: 0.7, ease: "power2.out" });
      gsap.from(".ld-hero-badge", { opacity: 0, y: 18, duration: 0.7, ease: "power2.out", delay: 0.05 });
      gsap.from(".ld-hero-title-line", {
        opacity: 0,
        y: 30,
        duration: 0.9,
        stagger: 0.12,
        ease: "power3.out",
        delay: 0.1,
      });
      gsap.from(".ld-hero-sub", { opacity: 0, y: 20, duration: 0.8, ease: "power2.out", delay: 0.45 });
      gsap.from(".ld-hero-cta", { opacity: 0, y: 20, duration: 0.8, stagger: 0.1, ease: "power2.out", delay: 0.65 });
      gsap.from(".ld-hero-panel", {
        opacity: 0,
        x: 48,
        duration: 0.95,
        ease: "power3.out",
        delay: 0.2,
      });
      gsap.to(".ld-hero-panel", {
        y: -10,
        duration: 2.6,
        repeat: -1,
        yoyo: true,
        ease: "sine.inOut",
      });
      gsap.utils.toArray<HTMLElement>(".ld-highlight-card").forEach((card, i) => {
        gsap.from(card, {
          opacity: 0,
          y: 36,
          duration: 0.7,
          delay: i * 0.08,
          ease: "power2.out",
          scrollTrigger: { trigger: card, start: "top 86%" },
        });
      });
      gsap.from(".ld-services-block", {
        opacity: 0,
        y: 36,
        duration: 0.8,
        ease: "power2.out",
        scrollTrigger: { trigger: ".ld-services-block", start: "top 84%" },
      });
      gsap.utils.toArray<HTMLElement>(".ld-service-card").forEach((card, i) => {
        gsap.from(card, {
          opacity: 0,
          y: 28,
          duration: 0.6,
          delay: i * 0.06,
          ease: "power2.out",
          scrollTrigger: { trigger: card, start: "top 90%" },
        });
      });
    }, rootRef);

    return () => ctx.revert();
  }, []);

  return (
    <main
      ref={rootRef}
      className="min-h-dvh overflow-hidden bg-[radial-gradient(circle_at_top,#f8fbff_0%,#eef6ff_40%,#ffffff_100%)] text-ink"
    >
      <div className="absolute inset-x-0 top-0 -z-10 h-[36rem] bg-[radial-gradient(circle_at_20%_20%,rgba(44,123,229,0.18),transparent_34%),radial-gradient(circle_at_82%_18%,rgba(15,76,129,0.16),transparent_30%),linear-gradient(180deg,rgba(234,241,252,0.9),rgba(255,255,255,0))]" />

      <section className="mx-auto max-w-6xl px-6 pb-20 pt-8 md:px-10 lg:px-12">
        <header className="ld-nav flex items-center justify-between rounded-full border border-white/70 bg-white/70 px-5 py-3 shadow-[0_12px_30px_rgba(44,123,229,0.08)] backdrop-blur">
          <div className="flex items-center gap-3">
            <Mascot size={40} />
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.28em] text-brand">AI Service Butler</p>
              <p className="text-base font-black text-ink">AI 智慧生活服務管家</p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => navigate("/login")}
            className="rounded-full border border-brand/15 bg-white px-4 py-2 text-sm font-bold text-brand shadow-sm transition hover:border-brand hover:bg-brand-soft"
          >
            進入系統
          </button>
        </header>

        <section className="grid items-center gap-12 pb-14 pt-16 lg:grid-cols-[1.02fr_0.98fr] lg:pt-20">
          <div>
            <p className="ld-hero-badge inline-flex rounded-full border border-info/15 bg-white/85 px-4 py-2 text-sm font-semibold text-info shadow-sm">
              Hackathon Demo · 藍白主題首頁
            </p>
            <h1 className="mt-7 max-w-3xl text-[clamp(2.8rem,6.4vw,5rem)] font-black leading-[1.02] text-slate-900">
              <span className="ld-hero-title-line block">把生活服務申請</span>
              <span className="ld-hero-title-line block">變成一段自然對話</span>
            </h1>
            <p className="ld-hero-sub mt-6 max-w-2xl text-lg leading-8 text-slate-600">
              使用者不需要先理解表單，只要把需求說清楚，AI 管家就會同步整理欄位、顯示結果，最後再由你自己確認送出。
            </p>
            <div className="mt-8 flex flex-wrap gap-4">
              <button
                type="button"
                onClick={() => navigate("/login")}
                className="ld-hero-cta rounded-full bg-brand px-7 py-4 text-base font-bold text-white shadow-[0_18px_45px_rgba(15,76,129,0.28)] transition hover:bg-brand-dark"
              >
                開始體驗
              </button>
              <button
                type="button"
                onClick={() => navigate("/home")}
                className="ld-hero-cta rounded-full border border-brand/15 bg-white px-7 py-4 text-base font-bold text-brand shadow-sm transition hover:border-brand hover:bg-brand-soft"
              >
                查看案件列表
              </button>
            </div>
          </div>

          <div className="ld-hero-panel relative">
            <div className="absolute -left-6 top-10 h-28 w-28 rounded-full bg-info/20 blur-3xl" />
            <div className="absolute -right-4 bottom-12 h-40 w-40 rounded-full bg-brand/20 blur-3xl" />
            <div className="relative rounded-[32px] border border-white/80 bg-white/88 p-6 shadow-[0_30px_80px_rgba(34,72,123,0.16)] backdrop-blur">
              <div className="rounded-[28px] border border-white/80 bg-[linear-gradient(180deg,#f4f8ff_0%,#e8f1ff_100%)] p-5">
                <div className="rounded-3xl bg-white px-5 py-4 text-base leading-7 text-ink shadow-sm">
                  我想預約下週六上午洗兩台冷氣，地址沿用上次的就好。
                </div>
                <div className="mt-4 ml-auto max-w-[85%] rounded-3xl bg-brand px-5 py-4 text-base leading-7 text-white shadow-sm">
                  已辨識為「冷氣清洗」，右側欄位也同步整理完成。你可以直接檢查內容，確認後再送件。
                </div>
              </div>

              <div className="mt-5 rounded-[28px] border border-brand/10 bg-white p-5 shadow-[inset_0_1px_0_rgba(255,255,255,0.7)]">
                <div className="flex items-center justify-between">
                  <p className="text-xs font-semibold uppercase tracking-[0.24em] text-brand">Instant Form</p>
                  <span className="rounded-full bg-brand-soft px-3 py-1 text-xs font-semibold text-brand">待確認</span>
                </div>
                <div className="mt-4 grid gap-3">
                  <div className="rounded-2xl border border-slate-100 bg-slate-50 px-4 py-3">
                    <p className="text-xs text-slate-500">服務</p>
                    <p className="mt-1 font-bold text-slate-900">冷氣清洗</p>
                  </div>
                  <div className="rounded-2xl border border-slate-100 bg-slate-50 px-4 py-3">
                    <p className="text-xs text-slate-500">希望日期</p>
                    <p className="mt-1 font-bold text-slate-900">2026-07-30</p>
                  </div>
                  <div className="rounded-2xl border border-slate-100 bg-slate-50 px-4 py-3">
                    <p className="text-xs text-slate-500">希望時段</p>
                    <p className="mt-1 font-bold text-slate-900">上午</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="mt-8 grid gap-5 md:grid-cols-3">
          {HIGHLIGHTS.map((item) => (
            <article
              key={item.title}
              className="ld-highlight-card rounded-[28px] border border-white/80 bg-white/88 p-6 shadow-[0_18px_55px_rgba(34,72,123,0.08)]"
            >
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-soft text-brand">
                <ServiceIcon type={item.icon} size={24} />
              </div>
              <h2 className="mt-4 text-xl font-black text-slate-900">{item.title}</h2>
              <p className="mt-3 leading-7 text-slate-600">{item.body}</p>
            </article>
          ))}
        </section>

        <section className="ld-services-block mt-16 rounded-[32px] border border-white/80 bg-white/90 p-8 shadow-[0_22px_65px_rgba(34,72,123,0.1)]">
          <div className="flex flex-col gap-8 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-brand">Supported Services</p>
              <h2 className="mt-3 text-3xl font-black text-slate-900">目前可用服務</h2>
              <p className="mt-3 max-w-2xl leading-7 text-slate-600">
                這份 demo 已經把服務辨識、表單 schema、MCP tool 呼叫與案件建立流程串起來，適合直接展示整體體驗。
              </p>
            </div>
            <button
              type="button"
              onClick={() => navigate("/login")}
              className="rounded-full bg-brand px-6 py-3.5 text-sm font-bold text-white shadow-[0_18px_45px_rgba(15,76,129,0.24)] transition hover:bg-brand-dark"
            >
              直接登入測試
            </button>
          </div>

          <div className="mt-8 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {SERVICES.map((service) => (
              <div
                key={service.name}
                className="ld-service-card rounded-[24px] border border-brand/10 bg-[linear-gradient(180deg,#ffffff_0%,#f5f9ff_100%)] p-5"
              >
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-soft text-brand shadow-sm">
                  <ServiceIcon type={service.icon} size={24} />
                </div>
                <p className="mt-4 text-lg font-bold text-slate-900">{service.name}</p>
              </div>
            ))}
          </div>
        </section>
      </section>
    </main>
  );
}
