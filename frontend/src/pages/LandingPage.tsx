import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { Mascot } from "../components/Mascot";
import { ServiceIcon } from "../components/ServiceIcon";

gsap.registerPlugin(ScrollTrigger);

const PAIN_POINTS = [
  { icon: "phone" as const, title: "電話打了又轉接", body: "找服務要一直撥打電話、等待轉接，說明需求還要重複好幾次。" },
  { icon: "warning" as const, title: "記不清楚約定內容", body: "時間、地址、需求說了一輪，卻沒有白紙黑字可以回頭確認。", highlight: true },
  { icon: "clock" as const, title: "案件進度不知道到哪了", body: "師傅到底確認了沒？什麼時候會來？只能一直等電話。" },
];

const STEPS = [
  { icon: "mic" as const, title: "說出需求", body: "用語音或文字告訴 AI，例如「我要預約明天下午洗兩台冷氣」。" },
  { icon: "chat" as const, title: "AI 建立案件", body: "AI 自動理解需求、詢問缺少的資訊，經您確認後才正式送出。" },
  { icon: "check" as const, title: "追蹤到完成", body: "案件狀態一目了然，從等待廠商確認、已確認到已完成通通看得到。" },
];

export function LandingPage() {
  const navigate = useNavigate();
  const rootRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const [videoFailed, setVideoFailed] = useState(false);

  useEffect(() => {
    const ctx = gsap.context(() => {
      gsap.from(".ld-hero-eyebrow", { opacity: 0, y: 16, duration: 0.7, ease: "power2.out" });
      gsap.from(".ld-hero-title-line", { opacity: 0, y: 34, duration: 0.9, stagger: 0.12, ease: "power3.out", delay: 0.1 });
      gsap.from(".ld-hero-sub", { opacity: 0, y: 20, duration: 0.8, delay: 0.5, ease: "power2.out" });
      gsap.from(".ld-hero-cta", { opacity: 0, y: 20, duration: 0.8, delay: 0.7, ease: "power2.out" });
      gsap.utils.toArray<HTMLElement>(".ld-pain-card").forEach((card, i) => {
        gsap.from(card, { opacity: 0, y: 40, duration: 0.7, ease: "power2.out", delay: i * 0.06, scrollTrigger: { trigger: card, start: "top 85%" } });
      });
      gsap.utils.toArray<HTMLElement>(".ld-step-card").forEach((card, i) => {
        gsap.from(card, { opacity: 0, x: i % 2 ? 40 : -40, duration: 0.7, ease: "power2.out", scrollTrigger: { trigger: card, start: "top 85%" } });
      });
      gsap.from(".ld-trust-block", { opacity: 0, y: 30, duration: 0.8, scrollTrigger: { trigger: ".ld-trust-block", start: "top 85%" } });
      gsap.from(".ld-cta-final", { opacity: 0, y: 30, duration: 0.8, scrollTrigger: { trigger: ".ld-cta-final", start: "top 88%" } });
    }, rootRef);
    return () => ctx.revert();
  }, []);

  useEffect(() => {
    const v = videoRef.current;
    if (v) {
      v.muted = true;
      v.defaultMuted = true;
    }
  }, []);

  return (
    <div
      ref={rootRef}
      className="overflow-hidden bg-gradient-to-b from-paper2 via-brand-soft to-paper2 font-sans text-ink"
    >
      <div className="sticky top-0 z-10 flex items-center justify-between border-b border-gray-200 bg-paper2/85 px-8 py-4 backdrop-blur">
        <div className="flex items-center gap-2.5">
          <Mascot size={38} />
          <span className="text-base font-bold">
            UNI-PIC <span className="font-normal text-gray-500">智慧生活服務管家</span>
          </span>
        </div>
        <button
          type="button"
          onClick={() => navigate("/login")}
          className="text-base font-bold text-brand"
        >
          登入 →
        </button>
      </div>

      <div className="relative flex min-h-[92vh] flex-col items-center justify-center overflow-hidden bg-brand-dark px-6 pb-24 pt-28 text-center text-white">
        {!videoFailed && (
          <video
            ref={videoRef}
            preload="auto"
            autoPlay
            muted
            loop
            playsInline
            onError={() => setVideoFailed(true)}
            className="absolute inset-0 h-full w-full object-cover"
            src="/videos/robot-hero.mp4"
          />
        )}
        <div className="absolute inset-0 bg-gradient-to-br from-[#C7CEFF5A] via-[#08090F1A] to-[#08080F28]" />
        <div className="relative z-[1] flex flex-col items-center">
          <span className="ld-hero-eyebrow mb-7 inline-block rounded-full bg-white/10 px-4.5 py-2 text-sm font-semibold tracking-wide">
            統一資訊 UNI-PIC 出品
          </span>
          <h1 className="max-w-3xl font-serif text-[clamp(36px,6.4vw,68px)] font-bold leading-tight">
            <span className="ld-hero-title-line block">生活大小事</span>
            <span className="ld-hero-title-line block">交給 AI 管家</span>
          </h1>
          <p className="ld-hero-sub mt-8 max-w-xl text-[clamp(17px,2.2vw,22px)] leading-relaxed text-white/80">
            冷氣清潔、水電維修、居家清潔⋯用語音或文字說出需求，AI 立刻理解、建立服務案件，並陪您追蹤到完成。
          </p>
          <button
            type="button"
            onClick={() => navigate("/login")}
            className="ld-hero-cta mt-11 rounded-full bg-white px-11 py-5 text-lg font-bold text-brand shadow-xl"
          >
            立即開始使用
          </button>
        </div>
      </div>

      <div className="mx-auto max-w-5xl px-6 py-24">
        <h2 className="mb-20 text-center font-serif text-[clamp(28px,4vw,40px)] font-bold">
          你還在為以下情境困擾嗎？
        </h2>
        <div className="flex flex-wrap justify-center gap-8">
          {PAIN_POINTS.map((p) => (
            <div
              key={p.title}
              className={`ld-pain-card max-w-[300px] flex-1 basis-[280px] rounded-[22px] p-8 shadow-md ${
                p.highlight ? "bg-brand text-white" : "border border-gray-100 bg-white"
              }`}
            >
              <div
                className={`mb-5 flex h-14 w-14 items-center justify-center rounded-full ${
                  p.highlight ? "bg-accent text-white" : "bg-brand-soft text-brand"
                }`}
              >
                <ServiceIcon type={p.icon} size={25} />
              </div>
              <div className="mb-2.5 text-lg font-bold">{p.title}</div>
              <div className={`text-base leading-relaxed ${p.highlight ? "text-white/80" : "text-gray-500"}`}>
                {p.body}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="mx-auto max-w-3xl px-6 py-24">
        <h2 className="mb-16 text-center font-serif text-[clamp(28px,4vw,40px)] font-bold">簡單三步驟！</h2>
        <div className="flex flex-col gap-7">
          {STEPS.map((s, i) => (
            <div
              key={s.title}
              className="ld-step-card flex items-center gap-7 rounded-3xl bg-white p-8 shadow-sm"
            >
              <div className="w-15 flex-none font-serif text-5xl font-bold text-gray-200">
                {String(i + 1).padStart(2, "0")}
              </div>
              <div className="flex h-14 w-14 flex-none items-center justify-center rounded-2xl bg-brand-soft text-brand">
                <ServiceIcon type={s.icon} size={26} />
              </div>
              <div>
                <div className="mb-1.5 text-xl font-bold">{s.title}</div>
                <div className="text-base leading-relaxed text-gray-500">{s.body}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="ld-trust-block mx-auto max-w-2xl px-6 py-24 text-center">
        <div className="mx-auto mb-6 flex h-21 w-19 items-center justify-center">
          <Mascot size={100} />
        </div>
        <div className="mb-3.5 text-2xl font-bold tracking-wide text-brand">UNI-PIC 統一資訊</div>
        <p className="text-lg leading-loose text-gray-500">
          統一資訊深耕零售、物流、餐飲產業的系統開發、雲端與 AI 應用，以企業級的穩定與安全，打造這款值得信賴的生活服務管家。
        </p>
      </div>

      <div className="ld-cta-final bg-gradient-to-br from-brand-dark to-[#082C4E] px-6 pb-28 pt-32 text-center text-white">
        <h2 className="mb-9 font-serif text-[clamp(30px,4.4vw,44px)] font-bold">準備好讓生活更輕鬆了嗎？</h2>
        <button
          type="button"
          onClick={() => navigate("/login")}
          className="rounded-full bg-white px-12 py-5 text-lg font-bold text-brand"
        >
          開始使用
        </button>
        <div className="mt-14 text-xs text-white/50">© 2026 President Information Corp. UNI-PIC 統一資訊</div>
      </div>
    </div>
  );
}
