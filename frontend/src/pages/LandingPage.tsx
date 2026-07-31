import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { FloatingBadge } from "../components/FloatingBadge";
import { GlassPanel } from "../components/GlassPanel";
import { Mascot } from "../components/Mascot";
import { PhoneMockup } from "../components/PhoneMockup";
import { ServiceIcon } from "../components/ServiceIcon";
import elderUserPhoto from "../assets/hero/hero-elder-user.jpg";
import serviceStaffPhoto from "../assets/hero/hero-service-staff.jpg";

gsap.registerPlugin(ScrollTrigger);

/**
 * Hero 人物素材（Requirement 18.1–18.5）。
 *
 * 兩張 1:1 照片分別代表「年長使用者」與「到府服務人員」。兩個色彩模式共用同一份圖片，
 * 不套任何濾鏡、混合模式或色調調整（Requirement 18.3）—— 因此這裡不出現 `dark:` 變體。
 *
 * `src` 若為 undefined，`FloatingBadge` 會退回姓名縮寫色塊、照片卡會退回 Mascot，
 * 兩者都不會出現破圖（Requirement 18.5）。
 *
 * `avatarCrop` 用於圓形頭像的放大裁切：素材是「人物在場景中」的方形照片，
 * 直接塞進 44px 圓框臉會過小，故以 scale + origin 對齊臉部位置。
 */
const HERO_AVATARS: { name: string; caption: string; src?: string; avatarCrop?: string }[] = [
  {
    name: "陳阿姨",
    caption: "剛完成冷氣預約",
    src: elderUserPhoto,
    avatarCrop: "scale-[2.1] origin-[56%_28%]",
  },
  {
    name: "李師傅",
    caption: "到府服務中",
    src: serviceStaffPhoto,
    avatarCrop: "scale-[2.4] origin-[45%_22%]",
  },
];

/** 手機外框內的對話示意（純文字氣泡，不使用照片，Requirement 11.1）。 */
const MOCKUP_BUBBLES: { role: "user" | "butler"; text: string }[] = [
  { role: "user", text: "冷氣好像不太冷" },
  { role: "butler", text: "已幫你選好「冷氣清洗」，想約哪一天？" },
  { role: "user", text: "這週六下午" },
];

/** 導覽列連結，指向頁面內各區塊。 */
const NAV_LINKS = [
  { href: "#how", label: "運作方式" },
  { href: "#services", label: "服務項目" },
  { href: "#updates", label: "案件進度" },
];

/** hero 下方的特色標籤橫排（參考稿的小藥丸列）。 */
const FEATURE_CHIPS = [
  "說出需求就好",
  "一次只問一件事",
  "欄位自動補齊",
  "到府服務",
  "全程可追蹤",
  "家人也能代辦",
  "明確報價",
  "專人媒合",
];

const HIGHLIGHTS = [
  {
    icon: "mic" as const,
    step: "01",
    short: "說出需求",
    title: "用說的就能建立需求",
    body: "直接描述你想做的事，AI 管家會幫你辨識服務、補齊欄位，整理成可以確認的申請內容。",
  },
  {
    icon: "check" as const,
    step: "02",
    short: "確認內容",
    title: "表單同步整理完成",
    body: "需求、日期、時段與地址會同步顯示在畫面上，你可以自己核對、自己修改、自己送出。",
  },
  {
    icon: "chat" as const,
    step: "03",
    short: "送出案件",
    title: "串接真正的 AWS 服務流程",
    body: "背後接上 Bedrock、長期記憶與 DynamoDB，這個 demo 不只是聊天畫面，而是能真的把案件送出去。",
  },
];

/* icon 底色在紫、桃紅、青、藍四色間輪替：四張服務卡剛好一張一色，
   讓多種色相同時出現在同一個畫面上，而不是同一個品牌色的深淺變化。 */
const SERVICE_TONES = [
  { soft: "var(--color-primary-soft)", ink: "var(--color-primary)" },
  { soft: "var(--color-secondary-soft)", ink: "var(--color-secondary)" },
  { soft: "var(--color-tertiary-soft)", ink: "var(--color-tertiary)" },
  { soft: "var(--color-info-soft)", ink: "var(--color-info)" },
] as const;

const SERVICES = [
  { icon: "plumbing" as const, name: "水電修繕" },
  { icon: "appliance" as const, name: "洗衣機清洗" },
  { icon: "aircon" as const, name: "冷氣清洗" },
  { icon: "cleaning" as const, name: "居家清潔" },
];

/**
 * Landing 頁面各張圖片卡的圖片路徑，沿用既有的 `frontend/public/images/` 慣例
 * （該資料夾已有 elder-user-phone.jpg 等素材）。用純路徑字串、不用 import，
 * 因此檔案還沒上傳也不會讓 build 失敗。上傳同檔名的圖片就會自動蓋掉下方的流體漸層裝飾／純色底；
 * 讀取失敗（尚未上傳）時 `BentoPhoto` 會自行隱藏，保留退路，不會出現破圖。
 * 建議尺寸：step1 為橫幅（約 4:3 或 16:10），step2 為方形（約 1:1），step3 為直幅（約 3:4），
 * banner 為寬幅橫幅（約 21:9 或更寬）。
 */
const LANDING_IMAGES = {
  step1: "/images/how-it-works-voice.jpg",
  step2: "/images/how-it-works-confirm.jpg",
  step3: "/images/how-it-works-submit.jpg",
  banner: "/images/banner-updates.jpg",
  phoneWallpaper: "/images/phone-wallpaper.jpg",
} as const;

function BentoPhoto({ src, className }: { src: string; className?: string }) {
  const [failed, setFailed] = useState(false);
  if (failed) return null;
  return (
    <img
      src={src}
      alt=""
      aria-hidden
      onError={() => setFailed(true)}
      className={`pointer-events-none absolute inset-0 h-full w-full object-cover ${className ?? ""}`}
    />
  );
}

/**
 * Hero 周邊的人物照片卡：1:1 照片 + 底部說明條，外框沿用玻璃擬態。
 *
 * 整張卡 `pointer-events-none`，因此漂浮疊在版面上時不會攔截任何可互動元素
 * （Requirement 9.7）。照片不套濾鏡，兩個色彩模式共用同一份影像（Requirement 18.3）；
 * `src` 缺漏時退回 Mascot，不會出現破圖（Requirement 18.5）。
 */
function HeroPhotoCard({
  src,
  alt,
  caption,
  className,
}: {
  src?: string;
  alt: string;
  caption: string;
  className?: string;
}) {
  return (
    <GlassPanel
      className={`pointer-events-none overflow-hidden rounded-3xl p-1.5 shadow-xl ${className ?? ""}`}
    >
      <div className="relative aspect-square overflow-hidden rounded-[1.25rem] bg-[var(--color-primary-soft)]">
        {src ? (
          <img src={src} alt={alt} className="h-full w-full object-cover" />
        ) : (
          <span className="flex h-full w-full items-center justify-center">
            <Mascot size={72} tone="brand" />
          </span>
        )}
        {/* 說明條：底部深色漸層確保白字達到對比要求 */}
        <span
          aria-hidden
          className="fluid-art-scrim pointer-events-none absolute inset-x-0 bottom-0 h-1/2"
        />
        <span className="absolute inset-x-0 bottom-0 px-3 pb-2.5 text-sm font-semibold text-[var(--color-on-panel-invert)]">
          {caption}
        </span>
      </div>
    </GlassPanel>
  );
}

export function LandingPage() {
  const navigate = useNavigate();
  const rootRef = useRef<HTMLDivElement>(null);

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
      gsap.from(".ld-hero-sub", {
        opacity: 0,
        y: 16,
        duration: 0.6,
        ease: "power2.out",
        delay: 0.3,
      });
      gsap.from(".ld-hero-cta", {
        opacity: 0,
        y: 16,
        duration: 0.6,
        stagger: 0.08,
        ease: "power2.out",
        delay: 0.42,
      });
      gsap.from(".ld-hero-panel", {
        opacity: 0,
        y: 24,
        duration: 0.7,
        ease: "power2.out",
        delay: 0.2,
      });
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
    <div
      ref={rootRef}
      className="bg-hero-backdrop min-h-dvh overflow-hidden pb-16 text-[var(--color-foreground)]"
    >
      {/*
        原本頁面最上緣與卡片內部各有一層純裝飾的巨型「BUTLER」背景字（含一處誤用
        gradient-text 的寫法），使用者回饋這些裝飾字沒有必要，已整段移除；
        改用下方留白直接讓漸層背景（.bg-hero-backdrop）本身透出來當作視覺焦點。
      */}
      <div aria-hidden className="h-[clamp(3rem,8vw,8rem)]" />

      <main className="mx-auto max-w-6xl px-4 sm:px-6">
        {/* ===== 主卡片：導覽列 + Hero，以大圓角白卡浮在漸層底上 ===== */}
        <section className="hero-curve relative overflow-hidden rounded-[36px] bg-[var(--color-surface)] shadow-[0_40px_100px_-40px_var(--color-primary)]">
          <header className="ld-nav relative z-20 flex items-center justify-between gap-4 px-5 py-4 sm:px-8 sm:py-5">
            <div className="flex items-center gap-2.5">
              <Mascot size={30} tone="brand" />
              <span className="wordmark-display text-lg tracking-[0.06em] text-[var(--color-foreground)]">
                BUTLER
              </span>
            </div>

            <nav className="hidden items-center gap-1 md:flex">
              {NAV_LINKS.map((link) => (
                <a
                  key={link.href}
                  href={link.href}
                  className="flex min-h-[44px] items-center rounded-full px-4 text-base font-semibold text-[var(--color-muted-foreground)] transition hover:bg-[var(--color-primary-soft)] hover:text-[var(--color-primary)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]"
                >
                  {link.label}
                </a>
              ))}
            </nav>

            <button
              type="button"
              onClick={() => navigate("/login")}
              className="bg-brand-gradient inline-flex min-h-[44px] shrink-0 items-center gap-2 rounded-full px-5 text-base font-bold text-[var(--color-on-primary)] shadow-[0_14px_30px_-12px_var(--color-primary)] transition hover:opacity-90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]"
            >
              進入系統
              <ServiceIcon type="chevronRight" size={18} />
            </button>
          </header>

          {/* ===== Hero ===== */}
          <div className="relative px-5 pb-24 pt-4 sm:px-8 sm:pb-28">
            <div className="relative mx-auto max-w-2xl text-center">
              <h1 className="font-[family-name:var(--font-display)] text-[clamp(1.75rem,3.6vw,2.75rem)] font-black leading-[1.15]">
                <span className="ld-hero-title-line block">把生活服務申請</span>
                <span className="ld-hero-title-line block">變成一段自然對話</span>
              </h1>
              <p className="ld-hero-sub mx-auto mt-4 max-w-xl text-base leading-7 text-[var(--color-muted-foreground)]">
                說出你想做什麼，AI 管家會把服務、日期、地址都整理好，最後由你親自確認再送出。
              </p>
            </div>

            {/*
              手機外框置中，周圍環繞 4 個漂浮徽章（2 個 icon 型 + 2 個 avatar 型，
              落在 Requirement 11.3 的 3–5 個區間）。徽章由 FloatingBadge 內建
              pointer-events-none，且以絕對定位擺在手機外框之外的留白處，
              不會遮擋任何可互動元素（Requirement 9.7）。
              視窗較窄時改為隱藏，避免與手機外框重疊擠壓。
            */}
            {/*
              手機外框改用真實長寬比（見 PhoneMockup），本身已經有足夠高度可以安全容納
              左右各三個漂浮元素（上緣／垂直置中／下緣），不再需要額外撐高容器
              （先前用 min-h 撐出比手機還高的容器，反而讓徽章與手機之間空得不自然）。
              容器改窄（max-w-xl 而非撐滿整個 hero 區塊寬度），讓 left-0/right-0 落在
              手機兩側適中距離，比撐滿全寬時近，但不會緊貼／疊到手機本體。
            */}
            <div className="ld-hero-panel relative mx-auto mt-10 max-w-3xl">
              <PhoneMockup className="relative z-10">
                {/*
                  螢幕內容改用 .bg-fluid-art 當作滿版桌布（對應參考稿手機截圖的高彩度桌布質感），
                  上疊一道鎖定畫面風格的時間列，讓手機讀起來像「一張真的桌布截圖」而不是純色底卡。
                */}
                <div className="bg-fluid-art relative flex h-full flex-col gap-2.5 px-3.5 pb-3 pt-1">
                  <BentoPhoto src={LANDING_IMAGES.phoneWallpaper} />
                  {/*
                    刻意不疊 .fluid-art-scrim：使用者希望直接看到原圖桌布，不要蓋一層灰階暗化。
                    狀態列文字改靠自己的深色藥丸底維持可讀性，不依賴整層暗化。
                    只留時間，拿掉「BUTLER」字樣：跟導覽列的品牌字重複，在這麼小的狀態列裡是多餘的一行。
                  */}
                  <div className="relative flex items-center text-[0.7rem] font-bold tracking-wide text-white">
                    <span className="rounded-full bg-black/35 px-2 py-0.5">9:41</span>
                  </div>
                  {/* 對話內容置中於畫面中段，模擬鎖定畫面通知堆疊在桌布中央的比例，而不是頂到最上緣 */}
                  <div className="relative flex flex-1 flex-col justify-center gap-2.5">
                    {MOCKUP_BUBBLES.map((bubble, i) => (
                      <div key={i} className={`flex ${bubble.role === "user" ? "justify-end" : "justify-start"}`}>
                        <span
                          className={`max-w-[85%] rounded-2xl px-3 py-2 text-xs leading-relaxed shadow-lg ${
                            bubble.role === "user"
                              ? "bg-bubble-user rounded-br-sm text-[var(--color-on-primary)]"
                              : "rounded-bl-sm bg-white text-[var(--color-foreground)]"
                          }`}
                        >
                          {bubble.text}
                        </span>
                      </div>
                    ))}
                    <div className="mt-1 flex items-center gap-2 rounded-2xl bg-white px-3 py-2 shadow-lg">
                      <span className="flex h-7 w-7 items-center justify-center rounded-xl bg-[var(--color-primary-soft)] text-[var(--color-primary)]">
                        <ServiceIcon type="aircon" size={16} />
                      </span>
                      <span className="text-xs font-bold text-[var(--color-foreground)]">冷氣清洗</span>
                      <span className="ml-auto text-[0.65rem] font-semibold text-[var(--color-success)]">已帶入</span>
                    </div>
                  </div>
                </div>
              </PhoneMockup>

              {/*
                六個漂浮元素改成「上緣／垂直置中／下緣」三段式定位，左右各三個，
                取代先前用猜測的絕對 px（top-2 / top-32 / bottom-10 混用）造成
                左側三個元素互相重疊的排法。三段式定位不依賴精確的元素高度估算，
                只要容器夠高（見上方 `min-h`）就能保證彼此間有安全間距。
              */}

              {/* 左上：數據卡（對應參考稿左邊的統計卡片），刻意用青色而非紫色，讓左右兩張卡不同色相 */}
              <GlassPanel
                aria-hidden
                className="float-bob pointer-events-none absolute left-0 top-2 hidden w-52 rounded-3xl p-4 shadow-xl [--float-delay:0s] [--float-rot:-4deg] lg:block"
              >
                <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-[var(--color-tertiary-soft)] text-[var(--color-tertiary)]">
                  <ServiceIcon type="health" size={22} />
                </span>
                <p className="mt-3 font-[family-name:var(--font-display)] text-2xl font-black text-[var(--color-foreground)]">
                  140+
                </p>
                <p className="mt-1 text-sm leading-6 text-[var(--color-muted-foreground)]">
                  位長輩原本靠家人代辦，現在自己開口就能完成。
                </p>
              </GlassPanel>

              {/* 右上：特色徽章，與左上統計卡對稱，補上原本右上角空缺的一個特點描述 */}
              <FloatingBadge
                variant="icon"
                icon="clock"
                label="24 小時待命"
                caption="隨時開口就能用"
                className="float-bob absolute right-0 top-2 hidden [--float-delay:2s] [--float-rot:4deg] lg:inline-flex"
              />

              {/* 左中：語音徽章，垂直置中於上方統計卡與下方照片卡之間，不再用猜測的 px 造成重疊 */}
              <FloatingBadge
                variant="icon"
                icon="mic"
                label="說出需求"
                caption="語音直接建立"
                className="float-bob-centered absolute left-0 top-1/2 hidden [--float-delay:0.8s] [--float-rot:3deg] lg:inline-flex"
              />

              {/* 右中：表單徽章，垂直置中於右側欄的中段 */}
              <FloatingBadge
                variant="icon"
                icon="check"
                label="表單已整理"
                caption="欄位自動補齊"
                className="float-bob-centered absolute right-0 top-1/2 hidden [--float-delay:1.6s] [--float-rot:-3deg] lg:inline-flex"
              />

              {/* 左下：年長使用者照片（Requirement 18.1），貼齊底部，與右下對稱 */}
              <HeroPhotoCard
                src={HERO_AVATARS[0].src}
                alt="一位長者坐在沙發上，微笑著用手機操作服務申請"
                caption="自己說、自己確認"
                className="float-bob absolute -left-2 bottom-2 hidden w-40 [--float-delay:0.4s] [--float-rot:4deg] lg:block xl:w-44"
              />

              {/* 右下：到府服務人員照片（Requirement 18.2），貼齊底部，與左下對稱 */}
              <HeroPhotoCard
                src={HERO_AVATARS[1].src}
                alt="穿著藍色工作服的到府服務人員正在清潔櫃架"
                caption="到府服務人員"
                className="float-bob absolute -right-1 bottom-2 hidden w-40 [--float-delay:1.2s] [--float-rot:-3deg] lg:block xl:w-44"
              />
            </div>

            {/* 主要行動：置中膠囊按鈕（對應參考稿的 Pre-Subscribe Now） */}
            <div className="relative mt-10 flex flex-wrap items-center justify-center gap-3">
              <button
                type="button"
                onClick={() => navigate("/login")}
                className="ld-hero-cta inline-flex min-h-[44px] items-center gap-2 rounded-full border-2 border-[var(--color-primary)] bg-[var(--color-surface)] px-7 text-base font-bold text-[var(--color-primary)] transition hover:bg-[var(--color-primary-soft)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]"
              >
                開始體驗
                <ServiceIcon type="chevronRight" size={18} />
              </button>
              <button
                type="button"
                onClick={() => navigate("/home")}
                className="ld-hero-cta inline-flex min-h-[44px] items-center rounded-full px-5 text-base font-semibold text-[var(--color-muted-foreground)] underline-offset-4 transition hover:text-[var(--color-primary)] hover:underline"
              >
                查看案件列表
              </button>
            </div>
          </div>
        </section>

        {/* ===== 特色標籤橫排 ===== */}
        <div className="mt-7 flex snap-x gap-2.5 overflow-x-auto pb-2">
          {FEATURE_CHIPS.map((chip) => (
            <span
              key={chip}
              className="snap-start whitespace-nowrap rounded-full border border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-2 text-sm font-semibold text-[var(--color-muted-foreground)]"
            >
              {chip}
            </span>
          ))}
        </div>

        {/* ===== 運作方式：Bento 網格 ===== */}
        <section id="how" className="mt-12 scroll-mt-8">
          <h2 className="font-[family-name:var(--font-display)] text-2xl font-black">運作方式</h2>

          <div className="mt-5 grid gap-4 lg:grid-cols-12">
            {/* 大卡：流體漸層裝飾 + 標題疊在暗化層上 */}
            <article className="ld-highlight-row relative min-h-[19rem] overflow-hidden rounded-[28px] lg:col-span-6">
              <div aria-hidden className="bg-fluid-art absolute inset-0" />
              <BentoPhoto src={LANDING_IMAGES.step1} />
              <div aria-hidden className="fluid-art-scrim absolute inset-0" />
              <div className="relative flex h-full flex-col justify-end p-6">
                <p className="font-[family-name:var(--font-mono)] text-sm font-bold text-[var(--color-on-panel-invert)] opacity-80">
                  {HIGHLIGHTS[0].step}
                </p>
                <h3 className="mt-2 font-[family-name:var(--font-display)] text-2xl font-black leading-tight text-[var(--color-on-panel-invert)]">
                  {HIGHLIGHTS[0].title}
                </h3>
                <p className="mt-2 max-w-md text-sm leading-6 text-[var(--color-on-panel-invert)]">
                  {HIGHLIGHTS[0].body}
                </p>
              </div>
            </article>

            {/*
              中欄：改成跟左右兩張卡一樣的「單張圖片＋文字半透明疊在圖上」處理，
              對應參考稿「三張卡＋下方一張橫幅」的版面，不再是裝飾色塊＋另一張白卡疊起來的兩截式做法。
            */}
            <article className="ld-highlight-row relative min-h-[19rem] overflow-hidden rounded-[28px] lg:col-span-3">
              <div aria-hidden className="bg-fluid-art--alt absolute inset-0" />
              <BentoPhoto src={LANDING_IMAGES.step2} />
              <div aria-hidden className="fluid-art-scrim absolute inset-0" />
              <div className="relative flex h-full flex-col justify-end p-6">
                <p className="font-[family-name:var(--font-mono)] text-sm font-bold text-[var(--color-on-panel-invert)] opacity-80">
                  {HIGHLIGHTS[1].step}
                </p>
                <h3 className="mt-2 font-[family-name:var(--font-display)] text-lg font-black leading-tight text-[var(--color-on-panel-invert)]">
                  {HIGHLIGHTS[1].title}
                </h3>
                <p className="mt-2 text-sm leading-6 text-[var(--color-on-panel-invert)]">
                  {HIGHLIGHTS[1].body}
                </p>
              </div>
            </article>

            {/* 右欄：直排標題（對應參考稿的旋轉文字） */}
            <article className="ld-highlight-row relative min-h-[19rem] overflow-hidden rounded-[28px] lg:col-span-3">
              <div aria-hidden className="bg-fluid-art--alt absolute inset-0" />
              <BentoPhoto src={LANDING_IMAGES.step3} />
              <div aria-hidden className="fluid-art-scrim absolute inset-0" />
              <div className="relative flex h-full items-end justify-between p-6">
                <h3 className="text-vertical-rl font-[family-name:var(--font-display)] text-xl font-black leading-tight text-[var(--color-on-panel-invert)]">
                  {HIGHLIGHTS[2].title}
                </h3>
                <p className="font-[family-name:var(--font-mono)] text-sm font-bold text-[var(--color-on-panel-invert)] opacity-80">
                  {HIGHLIGHTS[2].step}
                </p>
              </div>
            </article>
          </div>
        </section>

        {/* ===== 深色寬卡：案件進度 ===== */}
        <section
          id="updates"
          className="ld-highlight-row relative mt-4 scroll-mt-8 overflow-hidden rounded-[28px] bg-[var(--color-panel-invert)] p-6 sm:p-8"
        >
          <BentoPhoto src={LANDING_IMAGES.banner} />
          {/*
            這張橫幅圖偏淡色系（粉紫漸層桌布），文字需要較強的暗化層才能維持對比，
            因此不沿用 .fluid-art-scrim（那個是為「文字只在底部」的卡片設計、由上到下漸層變暗）。
          */}
          <div aria-hidden className="absolute inset-0" style={{ background: "rgba(2,6,23,0.72)" }} />
          <div className="relative flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
            <div className="max-w-md">
              <p className="font-[family-name:var(--font-mono)] text-sm font-bold text-[var(--color-on-panel-invert)] opacity-80">
                04
              </p>
              <h2 className="mt-2 font-[family-name:var(--font-display)] text-2xl font-black text-[var(--color-on-panel-invert)]">
                隨時掌握案件進度
              </h2>
              <p className="mt-3 text-sm leading-7 text-[var(--color-on-panel-invert)]">
                送出後可以在案件列表看到目前狀態，廠商確認、施工中、完成都會同步更新，家人也能一起查看。
              </p>
            </div>

            <div className="flex flex-col gap-2.5 lg:w-80">
              {[
                { label: "已送出", tone: "var(--color-info)" },
                { label: "廠商已確認", tone: "var(--color-success)" },
                { label: "服務進行中", tone: "var(--color-warning)" },
              ].map((row) => (
                <div
                  key={row.label}
                  className="flex items-center gap-3 rounded-2xl bg-[var(--color-surface-glass)] px-4 py-3"
                >
                  {/* 狀態同時以色點與文字表達，不單靠顏色（Requirement 16.5） */}
                  <span
                    aria-hidden
                    className="h-2.5 w-2.5 shrink-0 rounded-full"
                    style={{ background: row.tone }}
                  />
                  <span className="text-base font-semibold text-[var(--color-on-panel-invert)]">
                    {row.label}
                  </span>
                  <ServiceIcon
                    type="chevronRight"
                    size={18}
                    className="ml-auto text-[var(--color-on-panel-invert)]"
                  />
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ===== 服務項目 ===== */}
        <section
          id="services"
          className="ld-services-block mt-4 scroll-mt-8 rounded-[28px] bg-[var(--color-canvas)] p-6 sm:p-8"
        >
          <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <h2 className="font-[family-name:var(--font-display)] text-2xl font-black">目前可用服務</h2>
              <p className="mt-3 max-w-2xl leading-7 text-[var(--color-muted-foreground)]">
                服務辨識、表單整理與案件建立已經串起來，適合直接展示完整體驗。
              </p>
            </div>
            <button
              type="button"
              onClick={() => navigate("/login")}
              className="bg-brand-gradient inline-flex min-h-[44px] shrink-0 items-center rounded-full px-6 text-base font-bold text-[var(--color-on-primary)] transition hover:opacity-90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]"
            >
              直接登入測試
            </button>
          </div>

          {/* 服務卡維持不透明實色（Requirement 15.2） */}
          <div className="mt-7 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {SERVICES.map((service, index) => {
              const tone = SERVICE_TONES[index % SERVICE_TONES.length];
              return (
                <div
                  key={service.name}
                  className="ld-service-card rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
                >
                  <span
                    className="flex h-12 w-12 items-center justify-center rounded-2xl"
                    style={{ background: tone.soft, color: tone.ink }}
                  >
                    <ServiceIcon type={service.icon} size={24} />
                  </span>
                  <p className="mt-4 text-lg font-bold">{service.name}</p>
                </div>
              );
            })}
          </div>
        </section>
      </main>
    </div>
  );
}
