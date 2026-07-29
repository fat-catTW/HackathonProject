import { useNavigate } from "react-router-dom";
import { ButlerLauncher } from "../components/ButlerLauncher";
import { Mascot } from "../components/Mascot";
import { ServiceIcon } from "../components/ServiceIcon";
import { ThemeMenu } from "../components/ThemeMenu";
import { SERVICES } from "../data/services";
import { useAccessibilityMode } from "../hooks/useAccessibilityMode";
import { useAuth } from "../hooks/useAuth";

export function HomePage() {
  const { name, logout } = useAuth();
  const { enabled: a11yEnabled } = useAccessibilityMode();
  const navigate = useNavigate();

  return (
    <>
      <main className="mx-auto min-h-dvh max-w-md bg-brand-soft px-5 pb-32 pt-8">
        <header className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-3">
            <ThemeMenu />
            <div>
              <p className="text-sm font-semibold text-brand">你好，{name}</p>
              <h1 className="mt-0.5 text-2xl font-black text-slate-900">今天想使用什麼服務？</h1>
            </div>
          </div>
          <button
            type="button"
            onClick={() => {
              logout();
              navigate("/login");
            }}
            aria-label="登出"
            className="rounded-full bg-white px-4 py-2 text-sm font-bold text-gray-500 shadow-sm transition hover:text-brand focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand"
          >
            登出
          </button>
        </header>

        <section className="relative mt-8 overflow-hidden rounded-[32px] bg-gradient-to-br from-brand to-brand-dark p-6 text-white shadow-[0_24px_60px_rgba(15,76,129,0.22)]">
          <Mascot
            size={180}
            className="pointer-events-none absolute -bottom-8 -right-8 opacity-[0.12]"
            bodyColor="#FFFFFF"
            highlightColor="#FFFFFF"
          />
          <p className="relative text-sm font-semibold tracking-wide text-white/75">服務首頁</p>
          <h2 className="relative mt-2 text-2xl font-black">選擇你需要的到府服務</h2>
          <p className="relative mt-3 text-sm leading-7 text-white/78">
            目前提供水電修繕、洗衣機清洗、冷氣清洗與居家清潔。你可以直接點選卡片填單，也可以用下方
            AI 管家協助整理需求。
          </p>
        </section>

        <section className="mt-8">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-xl font-black text-slate-900">目前所有服務</h2>
            <span className="text-sm font-medium text-slate-500">展示中</span>
          </div>
          <div className="grid grid-cols-2 gap-3">
            {SERVICES.map((service, index) => (
              <button
                key={service.service_id}
                type="button"
                onClick={() => navigate(`/services/${service.service_id}`)}
                style={{ "--i": index } as React.CSSProperties}
                className="stagger-item group rounded-[24px] border border-white bg-white p-4 text-left shadow-sm transition hover:-translate-y-0.5 hover:shadow-md active:translate-y-0 active:shadow-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand"
              >
                <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-soft text-brand transition-colors group-hover:bg-brand group-hover:text-white">
                  <ServiceIcon type={service.icon} size={24} />
                </span>
                <p className="mt-4 text-lg font-black text-slate-900">{service.title}</p>
                <p className="mt-1 text-sm leading-6 text-slate-500">{service.subtitle}</p>
              </button>
            ))}
          </div>
        </section>

        <section className="mt-8">
          <button
            type="button"
            onClick={() => navigate("/my-services")}
            className="flex w-full items-center justify-between rounded-[28px] border border-white bg-white px-5 py-5 text-left shadow-sm transition hover:border-brand/15 active:shadow-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand"
          >
            <div className="flex items-center gap-4">
              <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-soft text-brand">
                <ServiceIcon type="chat" size={24} />
              </span>
              <div>
                <p className="text-lg font-black text-slate-900">我的服務</p>
                <p className="mt-1 text-sm text-slate-500">查看已建立的服務需求與案件進度</p>
              </div>
            </div>
            <ServiceIcon type="chevronRight" size={20} className="text-slate-400" />
          </button>
        </section>

        {a11yEnabled && (
          <a
            href="tel:0800000000"
            className="mt-8 flex items-center justify-center gap-3 rounded-2xl bg-brand py-6 text-xl font-black text-white shadow-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
          >
            <ServiceIcon type="phone" size={28} />
            撥打客服專線 0800-000-000
          </a>
        )}
      </main>

      <ButlerLauncher currentPageId="home" />
    </>
  );
}
