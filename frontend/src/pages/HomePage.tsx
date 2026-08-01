import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AllServicesModal } from "../components/AllServicesModal";
import { Mascot } from "../components/Mascot";
import { OnboardingModal } from "../components/OnboardingModal";
import { ServiceIcon } from "../components/ServiceIcon";
import { BottomNav } from "../components/BottomNav";
import { AppearanceMenu } from "../components/AppearanceMenu";
import { SupportPanel } from "../components/SupportPanel";
import { WeatherGreetingCard } from "../components/WeatherGreetingCard";
import { SERVICES } from "../data/services";
import { SERVICE_TONES } from "../utils/serviceTones";
import { useAccessibilityMode } from "../hooks/useAccessibilityMode";
import { useAuth } from "../hooks/useAuth";
import { useOnboarding } from "../hooks/useOnboarding";

const PREVIEW_COUNT = 4;

/*
 * Header 大標題第二行輪播的情境問句，直接取材自實際服務（而不是憑空造句），
 * 讓使用者一看就知道「這句話是真的在講這個 App 能做的事」，比固定一句
 * 「今天想使用什麼服務？」更容易讓人聯想到自己剛好卡住的生活小事。
 */
const GREETING_PROMPTS = [
  "水電漏水了嗎？",
  "洗衣機該洗了？",
  "冷氣該洗了嗎？",
  "想大掃除嗎？",
  "想找健康好物嗎？",
  "想訂位吃飯嗎？",
  "今天想吃點什麼？",
  "想逛街買東西嗎？",
  "有包裹要寄送嗎？",
] as const;

const GREETING_INTERVAL_MS = 5200;

export function HomePage() {
  const { name, logout } = useAuth();
  const { enabled: a11yEnabled } = useAccessibilityMode();
  const { shouldShow: showOnboarding, complete: completeOnboarding } = useOnboarding();
  const navigate = useNavigate();
  const entryServices = SERVICES.filter((service) => !service.hidden);
  const previewServices = entryServices.slice(0, PREVIEW_COUNT);
  const remainingCount = entryServices.length - previewServices.length;
  const [supportOpen, setSupportOpen] = useState(false);
  const [servicesOpen, setServicesOpen] = useState(false);
  const [greetingIndex, setGreetingIndex] = useState(0);

  useEffect(() => {
    if (!supportOpen && !servicesOpen) return;
    const { body } = document;
    const previousOverflow = body.style.overflow;
    body.style.overflow = "hidden";
    return () => {
      body.style.overflow = previousOverflow;
    };
  }, [supportOpen, servicesOpen]);

  useEffect(() => {
    const timer = setInterval(() => {
      setGreetingIndex((prev) => (prev + 1) % GREETING_PROMPTS.length);
    }, GREETING_INTERVAL_MS);
    return () => clearInterval(timer);
  }, []);

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
        <header className="relative rounded-[32px] p-5 text-[var(--color-on-primary)] shadow-[0_35px_70px_-30px_var(--color-primary)]">
          {/*
            背景漸層跟裝飾用 Mascot 都收進這層獨立的 overflow-hidden 容器，跟外面的
            AppearanceMenu／登出按鈕分開。原本 overflow-hidden 是直接放在 <header> 本身，
            結果 AppearanceMenu 展開的選單（無障礙模式、重新觀看新手導覽都在裡面）
            也是 header 的子元素，跟著被裁掉下半部，使用者看不到那兩個選項。
            現在只裁掉背景這層，選單所在的內容層不再受 overflow-hidden 限制。
          */}
          <div
            aria-hidden
            className="absolute inset-0 overflow-hidden rounded-[32px]"
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
          </div>
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
            <span key={greetingIndex} className="greeting-fade inline-block">
              {GREETING_PROMPTS[greetingIndex]}
            </span>
          </h1>
        </header>

        {/*
          AI 管家入口：改成「光暈圓形頭像」為主的入口卡，而不是文字說明＋小插圖。
          這頁真正的重點是管家本人，移到服務清單前面、緊接在 header 下方——
          頭像本身放大、疊多層模糊光暈當「靈氣」，底下只留一個最短的行動提示，
          整張卡片都是同一個按鈕，點哪裡都會進聊天室。
        */}
        <section className="mt-8">
          <button
            type="button"
            onClick={() => navigate("/new")}
            className="flex w-full flex-col items-center overflow-hidden rounded-[28px] bg-[var(--color-canvas)] px-5 py-7 text-center transition hover:-translate-y-0.5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand"
          >
            <p className="text-sm font-bold text-brand">AI 管家</p>
            <div className="relative mt-4 h-[150px] w-[150px] shrink-0">
              <span
                aria-hidden
                className="pointer-events-none absolute -inset-6 rounded-full opacity-70 blur-2xl"
                style={{ background: "var(--color-primary-accent)" }}
              />
              <span
                aria-hidden
                className="pointer-events-none absolute -inset-2 rounded-full opacity-60 blur-xl"
                style={{ background: "var(--color-primary)" }}
              />
              <div className="relative h-full w-full overflow-hidden rounded-full shadow-[0_20px_45px_-15px_var(--color-primary)] ring-1 ring-[var(--color-border)]">
                <img
                  src="/images/ai-companion.jpg"
                  alt=""
                  aria-hidden
                  className="h-full w-full object-cover"
                  style={{ objectPosition: "50% 25%" }}
                />
              </div>
            </div>
            <span className="mt-5 inline-flex min-h-[40px] items-center gap-1 rounded-full bg-brand px-4 text-sm font-bold text-[var(--color-on-primary)]">
              輕觸進入對話
              <ServiceIcon type="chevronRight" size={14} />
            </span>
          </button>
        </section>

        {/*
          服務捷徑列：份量刻意比管家小一號，只露出前 4 個服務圖示 + 「還有幾個」提示，
          整張卡是一個按鈕，點哪裡都開啟「所有服務」視窗（AllServicesModal）。
          不做成可各自導頁的獨立按鈕，是為了讓「瀏覽全部」這個動作只有一種入口、
          不會讓使用者以為小圖示跟文字連結是兩種不同功能。
        */}
        <section className="mt-6">
          <button
            type="button"
            onClick={() => setServicesOpen(true)}
            className="flex w-full flex-col gap-3 rounded-[22px] bg-[var(--color-surface)] p-4 text-left shadow-sm transition hover:-translate-y-0.5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand"
          >
            <div className="flex items-center justify-between">
              <span className="text-sm font-extrabold text-[var(--color-foreground)]">熱門服務</span>
              <span className="inline-flex items-center gap-1 text-sm font-bold text-brand">
                瀏覽全部
                <ServiceIcon type="chevronRight" size={14} />
              </span>
            </div>
            <div className="flex items-center gap-3">
              {previewServices.map((service, index) => {
                const tone = SERVICE_TONES[index % SERVICE_TONES.length];
                return (
                  <span
                    key={service.service_id}
                    className="flex h-11 w-11 items-center justify-center rounded-full"
                    style={{ background: tone.soft, color: tone.ink }}
                  >
                    <ServiceIcon type={service.icon} size={20} />
                  </span>
                );
              })}
              {remainingCount > 0 && (
                <span className="flex h-11 w-11 items-center justify-center rounded-full bg-[var(--color-canvas)] text-xs font-extrabold text-[var(--color-muted-foreground)]">
                  +{remainingCount}
                </span>
              )}
            </div>
          </button>
        </section>

        <WeatherGreetingCard userName={name} />

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
              <p className="mt-1.5 line-clamp-1 text-sm leading-6 text-[var(--color-on-secondary)] opacity-85">
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
              <p className="mt-1.5 line-clamp-1 text-sm leading-6 text-[var(--color-on-primary)] opacity-85">
                常見問題快速解答，轉真人客服
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

      {servicesOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[var(--color-scrim)] px-4 py-6 backdrop-blur-[2px] sm:px-6 sm:py-8">
          <button
            type="button"
            aria-label="關閉所有服務視窗"
            onClick={() => setServicesOpen(false)}
            className="absolute inset-0"
          />
          <div className="relative w-full max-w-md">
            <AllServicesModal onClose={() => setServicesOpen(false)} />
          </div>
        </div>
      )}

      <BottomNav />
    </>
  );
}
