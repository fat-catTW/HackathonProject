import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Mascot } from "../components/Mascot";
import { OnboardingModal } from "../components/OnboardingModal";
import { ServiceIcon } from "../components/ServiceIcon";
import { BottomNav } from "../components/BottomNav";
import { AppearanceMenu } from "../components/AppearanceMenu";
import { SupportPanel } from "../components/SupportPanel";
import { SERVICES } from "../data/services";
import { useAccessibilityMode } from "../hooks/useAccessibilityMode";
import { useAuth } from "../hooks/useAuth";
import { useOnboarding } from "../hooks/useOnboarding";

/* icon／卡片底色在紫、桃紅、青、藍四色間輪替，刻意讓多種色相同時出現在同一個畫面，
   不是只有單一品牌色的深淺變化。 */
const SERVICE_TONES = [
  { soft: "var(--color-primary-soft)", ink: "var(--color-primary)" },
  { soft: "var(--color-secondary-soft)", ink: "var(--color-secondary)" },
  { soft: "var(--color-tertiary-soft)", ink: "var(--color-tertiary)" },
  { soft: "var(--color-info-soft)", ink: "var(--color-info)" },
] as const;

export function HomePage() {
  const { name, logout } = useAuth();
  const { enabled: a11yEnabled } = useAccessibilityMode();
  const { shouldShow: showOnboarding, complete: completeOnboarding } = useOnboarding();
  const navigate = useNavigate();
  const entryServices = SERVICES.filter((service) => !service.hidden);
  const serviceRailRef = useRef<HTMLDivElement>(null);
  const [supportOpen, setSupportOpen] = useState(false);

  function scrollServiceRail(direction: "prev" | "next") {
    const el = serviceRailRef.current;
    if (!el) return;
    const amount = el.clientWidth * 0.7 * (direction === "next" ? 1 : -1);
    el.scrollBy({ left: amount, behavior: "smooth" });
  }

  useEffect(() => {
    if (!supportOpen) return;
    const { body } = document;
    const previousOverflow = body.style.overflow;
    body.style.overflow = "hidden";
    return () => {
      body.style.overflow = previousOverflow;
    };
  }, [supportOpen]);

  return (
    <>
      {showOnboarding && <OnboardingModal onComplete={completeOnboarding} />}

      <main className="mx-auto min-h-dvh max-w-md bg-brand-soft px-5 pb-32 pt-8">
        {/*
          參考稿的漸層卡其實四個角都是圓的、卡片本身跟畫面邊緣還是留了一點距離，
          不是撐滿到邊界——上一版把它改成貼邊、只留底部圓角，方向反而錯了。
          真正的差異在漸層「質感」：參考稿是好幾層柔和、邊界模糊的光暈疊在一起，
          看起來像會發光的雲霧，不是一刀切的線性漸層。這裡改用多層 radial-gradient，
          每層都用大範圍、淡出到 transparent 的柔和光斑疊出那種發光感，
          四角圓角、留白邊界都改回一般卡片的樣子。
        */}
        <header
          className="relative overflow-hidden rounded-[32px] p-5 text-[var(--color-on-primary)] shadow-[0_35px_70px_-30px_var(--color-primary)]"
          style={{
            // 整體調淺一階：底層漸層改用 primary-accent（淺紫）到 primary（原本是 primary→primary-hover，
            // 兩者都偏深），文字改加一圈柔和陰影確保在最淺的區域仍然讀得清楚，
            // 不用把底色壓深來換取對比。
            backgroundImage: `
              radial-gradient(55% 45% at 82% 8%, rgba(255,255,255,0.55) 0%, transparent 70%),
              radial-gradient(70% 60% at 10% 105%, var(--color-secondary) 0%, transparent 70%),
              radial-gradient(90% 85% at 65% -15%, var(--color-primary-accent) 0%, transparent 66%),
              linear-gradient(165deg, var(--color-primary-accent) 0%, var(--color-primary) 100%)
            `,
          }}
        >
          <Mascot
            size={150}
            tone="inverted"
            className="pointer-events-none absolute -bottom-8 -right-8 opacity-[0.14]"
          />
          <div className="relative flex items-center justify-between gap-4">
            <AppearanceMenu />
            <button
              type="button"
              onClick={() => {
                logout();
                navigate("/login");
              }}
              aria-label="登出"
              className="rounded-full bg-white/25 px-4 py-2 text-sm font-bold text-[var(--color-on-primary)] shadow-sm transition hover:bg-white/35 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-on-primary)]"
            >
              登出
            </button>
          </div>
          <p
            className="relative mt-5 text-sm font-semibold opacity-90"
            style={{ textShadow: "0 2px 10px rgba(76,29,149,0.45)" }}
          >
            你好，{name}
          </p>
          <h1
            className="relative mt-1 text-3xl font-black leading-tight"
            style={{ textShadow: "0 2px 14px rgba(76,29,149,0.45)" }}
          >
            今天想使用
            <br />
            什麼服務？
          </h1>
        </header>

        {/*
          服務項目改成可橫向滑動的卡片列（服務有 9 種，直接攤開成 2 欄格子會拉得很長）。
          原生 overflow-x-auto + snap 支援觸控滑動；箭頭按鈕另外提供滑鼠使用者一個明確的
          「還有更多、點一下看下一批」入口，兩種操作方式並存。
        */}
        <section className="mt-8">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-xl font-black text-[var(--color-foreground)]">目前所有服務</h2>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => scrollServiceRail("prev")}
                aria-label="上一批服務"
                className="flex h-9 w-9 items-center justify-center rounded-full bg-[var(--color-surface)] text-[var(--color-muted-foreground)] shadow-sm transition hover:text-brand focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand"
              >
                <ServiceIcon type="back" size={16} />
              </button>
              <button
                type="button"
                onClick={() => scrollServiceRail("next")}
                aria-label="下一批服務"
                className="flex h-9 w-9 items-center justify-center rounded-full bg-[var(--color-surface)] text-[var(--color-muted-foreground)] shadow-sm transition hover:text-brand focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand"
              >
                <ServiceIcon type="chevronRight" size={16} />
              </button>
            </div>
          </div>
          <div
            ref={serviceRailRef}
            className="-mx-5 flex snap-x snap-mandatory gap-3 overflow-x-auto scroll-smooth px-5 pb-2 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
          >
            {entryServices.map((service, index) => {
              const tone = SERVICE_TONES[index % SERVICE_TONES.length];
              return (
                <button
                  key={service.service_id}
                  type="button"
                  onClick={() => navigate(`/services/${service.service_id}`)}
                  style={{ "--i": index, background: tone.soft } as React.CSSProperties}
                  className="stagger-item group w-40 shrink-0 snap-start rounded-[24px] p-4 text-left transition hover:-translate-y-0.5 active:translate-y-0 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand"
                >
                  {/*
                    icon 底座改成「有光澤感的圓角方塊」：白面到色調底的斜向漸層 + 內側高光陰影，
                    讓圖示容器本身有點立體感，取代單純的實色方塊；線條圖示本身也加粗
                    （strokeWidth 2）搭配較大尺寸，避免圖示在底座裡看起來單薄、空洞。
                  */}
                  <span
                    className="flex h-16 w-16 items-center justify-center rounded-2xl transition-transform duration-200 group-hover:scale-105"
                    style={{
                      backgroundImage: `linear-gradient(145deg, var(--color-surface) 0%, ${tone.soft} 100%)`,
                      boxShadow: `inset 0 1px 1px rgba(255,255,255,0.8), inset 0 -6px 10px -7px rgba(0,0,0,0.12), 0 10px 18px -12px ${tone.ink}`,
                      color: tone.ink,
                    }}
                  >
                    <ServiceIcon type={service.icon} size={32} strokeWidth={2} />
                  </span>
                  {/*
                    標題與副標題都鎖定單行（line-clamp-1）：只要有任何一張卡的文字換成兩行，
                    後面所有內容的起始高度就會跟著錯開，卡片列橫向排開時看起來高低不齊。
                    鎖兩者都只有一行，才能保證每張卡片高度完全一致；超出的文字用省略號截斷。
                  */}
                  <p className="mt-4 line-clamp-1 text-base font-black leading-snug text-[var(--color-foreground)]">{service.title}</p>
                  <p className="mt-1 line-clamp-1 text-xs leading-5 text-[var(--color-muted-foreground)]">{service.subtitle}</p>
                </button>
              );
            })}
          </div>
        </section>

        {/*
          機器人插圖卡：原本是自動播放的影片，改成靜態插圖（使用者提供），拿掉影片檔案。
          整寬色塊卡，左邊放文字介紹＋進入對話的行動點，右邊放直式相框，相框角落加一顆
          模糊色塊當光暈，多一點層次感。
        */}
        <section className="mt-8 overflow-hidden rounded-[28px] bg-[var(--color-canvas)] p-5">
          <div className="flex items-center gap-4">
            <div className="min-w-0 flex-1">
              <p className="text-sm font-bold text-brand">AI 管家</p>
              <h2 className="mt-1 text-lg font-black leading-snug text-[var(--color-foreground)]">
                隨時都在，陪你把事情說清楚
              </h2>
              <p className="mt-2 text-sm leading-6 text-[var(--color-muted-foreground)]">
                有任何生活雜事，直接開口跟管家說就好。
              </p>
              <button
                type="button"
                onClick={() => navigate("/new")}
                className="mt-4 inline-flex min-h-[40px] items-center gap-1 rounded-full bg-brand px-4 text-sm font-bold text-[var(--color-on-primary)] transition hover:opacity-90"
              >
                開始對話
                <ServiceIcon type="chevronRight" size={14} />
              </button>
            </div>

            <div className="relative shrink-0">
              <span
                aria-hidden
                className="pointer-events-none absolute -inset-3 -z-10 rounded-full opacity-70 blur-2xl"
                style={{ background: "var(--color-secondary-soft)" }}
              />
              <div className="relative aspect-[4/5] w-28 overflow-hidden rounded-[22px] shadow-[0_20px_45px_-20px_var(--color-primary)] ring-1 ring-[var(--color-border)]">
                <img
                  src="/images/ai-companion.jpg"
                  alt=""
                  aria-hidden
                  className="h-full w-full object-cover"
                />
              </div>
            </div>
          </div>
        </section>

        {/*
          「我的服務」／「客服中心」改成彩色插畫卡（參考稿：色塊卡右下角探出一隻大隻的
          可愛角色插圖 + 白色標題 + 圓角行動按鈕）。使用者提供了企鵝（透明背景 PNG，可以
          直接疊在色塊上）跟貓咪（JPG，本身帶淺藍漸層背景，无法乾淨去背——用圓形相框裁切，
          當成「貼紙」放在角落，而不是硬去背留下鋸齒）。底色用單一色相的漸層＋高光/陰影
          疊層（跟 Header 同一種手法），文字固定用該色相配對好的 on-* Token，兩個模式都
          保證對比安全。
        */}
        <section className="mt-8 grid gap-4">
          <button
            type="button"
            onClick={() => navigate("/my-services")}
            className="relative flex w-full items-center overflow-hidden rounded-[28px] p-6 text-left shadow-[0_25px_55px_-28px_var(--color-secondary)] transition hover:-translate-y-0.5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand"
            style={{
              backgroundImage:
                "radial-gradient(45% 42% at 96% 102%, var(--color-primary-accent) 0%, transparent 62%), radial-gradient(55% 50% at 85% -8%, rgba(255,255,255,0.4) 0%, transparent 70%), radial-gradient(50% 45% at 4% 108%, rgba(0,0,0,0.18) 0%, transparent 65%), linear-gradient(150deg, var(--color-secondary) 0%, var(--color-secondary) 100%)",
            }}
          >
            <div className="relative z-10 max-w-[62%]">
              <p className="text-lg font-black text-[var(--color-on-secondary)]">我的服務</p>
              <p className="mt-1.5 text-sm leading-6 text-[var(--color-on-secondary)] opacity-85">
                查看已建立的服務需求與案件進度
              </p>
              <span className="mt-4 inline-flex items-center gap-1 rounded-full bg-[var(--color-surface)] px-4 py-2 text-sm font-bold text-[var(--color-secondary)]">
                查看
                <ServiceIcon type="chevronRight" size={14} />
              </span>
            </div>
            <img
              src="/images/companion-penguin.png"
              alt=""
              aria-hidden
              className="pointer-events-none absolute -bottom-4 -right-2 h-32 w-32 object-contain drop-shadow-[0_16px_30px_rgba(0,0,0,0.25)]"
            />
          </button>

          {/*
            客服中心：FAQ 快速解答 + 轉真人客服的入口。之前的浮動按鈕版本（SupportLauncher）
            沒有掛在任何頁面上，改版後這裡完全沒有入口——補回一張跟「我的服務」同樣份量的
            插畫卡，點擊開啟同一份 SupportPanel 抽屜，不新增浮動按鈕跟底部導覽列搶位置。
          */}
          <button
            type="button"
            onClick={() => setSupportOpen(true)}
            className="relative flex w-full items-center overflow-hidden rounded-[28px] p-6 text-left shadow-[0_25px_55px_-28px_var(--color-primary)] transition hover:-translate-y-0.5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand"
            style={{
              backgroundImage:
                "radial-gradient(45% 42% at 96% 102%, var(--color-tertiary) 0%, transparent 62%), radial-gradient(55% 50% at 85% -8%, rgba(255,255,255,0.4) 0%, transparent 70%), radial-gradient(50% 45% at 4% 108%, rgba(0,0,0,0.18) 0%, transparent 65%), linear-gradient(150deg, var(--color-primary) 0%, var(--color-primary) 100%)",
            }}
          >
            <div className="relative z-10 max-w-[62%]">
              <p className="text-lg font-black text-[var(--color-on-primary)]">客服中心</p>
              <p className="mt-1.5 text-sm leading-6 text-[var(--color-on-primary)] opacity-85">
                常見問題快速解答，需要時轉真人客服
              </p>
              <span className="mt-4 inline-flex items-center gap-1 rounded-full bg-[var(--color-surface)] px-4 py-2 text-sm font-bold text-[var(--color-primary)]">
                洽詢
                <ServiceIcon type="chevronRight" size={14} />
              </span>
            </div>
            {/*
              圓形相框原本用負邊距讓它探出卡片右下角，但卡片本身是 overflow-hidden，
              超出邊界的部分（剛好是貓爪所在的角落）就被裁掉了。改成正邊距、完全收在
              卡片內側，貓爪才不會被卡片邊界吃掉。
            */}
            <div
              aria-hidden
              className="pointer-events-none absolute bottom-3 right-3 h-28 w-28 overflow-hidden rounded-full shadow-xl ring-4 ring-white/70"
            >
              <img src="/images/companion-cat.jpg" alt="" className="h-full w-full object-cover" />
            </div>
          </button>
        </section>

        {a11yEnabled && (
          <a
            href="tel:0800000000"
            className="mt-8 flex items-center justify-center gap-3 rounded-2xl bg-brand py-6 text-xl font-black text-[var(--color-on-primary)] shadow-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-on-primary)]"
          >
            <ServiceIcon type="phone" size={28} />
            撥打客服專線 0800-000-000
          </a>
        )}
      </main>

      {supportOpen && (
        <div className="fixed inset-0 z-50 bg-[var(--color-scrim)] px-4 py-6 backdrop-blur-[2px] sm:px-6 sm:py-8">
          <button
            type="button"
            aria-label="關閉客服視窗"
            onClick={() => setSupportOpen(false)}
            className="absolute inset-0"
          />
          <div className="relative flex h-full items-end justify-end">
            <SupportPanel currentPageId="home" onClose={() => setSupportOpen(false)} />
          </div>
        </div>
      )}

      <BottomNav />
    </>
  );
}
