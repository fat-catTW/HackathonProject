import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  fetchDemoAccounts,
  loginWithEmail,
  registerAccount,
  type DemoAccount,
} from "../api/auth";
import { ApiError } from "../api/client";
import { ServiceIcon } from "../components/ServiceIcon";
import { Toast } from "../components/Toast";
import { useAuth } from "../hooks/useAuth";

type Mode = "choices" | "loginForm" | "registerForm";

/**
 * 中央大圖示（使用者提供的可愛 AI orb 圖示，放在 `frontend/public/images/`）。
 * 圖示本身已內建光暈邊框，外面再疊一層模糊色塊當作發光背景，呼應參考稿
 * 「柔和漸層光暈中飄浮一顆會發光的圓球」的效果。
 */
const ORB_ICON = "/images/ai-orb-icon.png";

/**
 * 登入頁配色一律引用語意色 Token（Requirement 6.6）。依 Requirement 12.2，表單區塊維持
 * 不透明 `--color-surface`，不套玻璃擬態；輸入框明確指定文字與 placeholder 色，
 * 確保 Dark 模式下輸入內容可讀。版面結構與欄位順序不變（Requirement 12.4）。
 */
const FIELD =
  "w-full rounded-2xl border-2 border-[var(--color-border)] bg-[var(--color-surface)] px-4.5 py-4.5 text-lg text-[var(--color-foreground)] placeholder:text-[var(--color-muted-foreground)] outline-none focus:border-[var(--color-primary)]";

/** 表單容器：不透明實色卡片（Requirement 12.2） */
const FORM_CARD =
  "flex flex-col gap-4 rounded-[28px] border border-[var(--color-border)] bg-[var(--color-surface)] p-6 shadow-sm";

/**
 * App 螢幕感的外層卡片：固定手機 App 比例的尺寸（`aspect-[9/17.5]`，並用 `max-h` 在較矮的
 * 視窗上封頂），不會因為切換「選擇／登入表單／註冊表單」而跟著內容多寡忽大忽小——
 * 這樣才是「手機 App 大小」的框，而不是一個會呼吸的內容容器。內容改放進下面可捲動的
 * 內層區塊，超出固定高度時用內部捲動處理，不撐大外框。
 */
const SCREEN_CARD =
  "relative flex aspect-[9/17.5] w-full max-w-md max-h-[min(760px,88dvh)] flex-col overflow-hidden rounded-[40px] border border-[var(--color-border)] bg-[var(--color-surface)] shadow-[0_40px_90px_-30px_rgba(0,0,0,0.35)]";

interface MoreOptionsMenuProps {
  account: DemoAccount | null;
  onDemoLogin: () => void;
  onVendorLogin: () => void;
}

/**
 * 右上角「更多選項」小選單：收納 Demo 帳號一鍵登入與廠商登入入口，
 * 讓主畫面把版面留給大圖示和登入／註冊兩個核心動作，不用整排塞在下方。
 * 開合互動與 AppearanceMenu 一致（點外部或 Esc 關閉）。
 */
function MoreOptionsMenu({ account, onDemoLogin, onVendorLogin }: MoreOptionsMenuProps) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onPointerDown(e: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    }
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="true"
        aria-expanded={open}
        aria-label="更多登入選項"
        className="flex h-11 w-11 items-center justify-center rounded-full bg-[var(--color-surface)] text-[var(--color-muted-foreground)] shadow-sm transition hover:text-[var(--color-primary)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand"
      >
        <ServiceIcon type="more" size={20} />
      </button>

      {open && (
        <div
          role="menu"
          aria-label="更多登入選項"
          className="absolute right-0 top-[calc(100%+8px)] z-20 w-64 rounded-[24px] border border-[var(--color-border)] bg-[var(--color-surface)] p-3 shadow-xl"
        >
          {account && (
            <button
              type="button"
              role="menuitem"
              onClick={() => {
                onDemoLogin();
                setOpen(false);
              }}
              className="flex w-full items-center justify-between gap-2 rounded-2xl border-2 border-dashed border-tertiary/50 bg-[var(--color-tertiary-soft)] px-4 py-3 text-left text-sm font-bold text-[var(--color-tertiary)] transition hover:border-[var(--color-tertiary)]"
            >
              Demo Account 一鍵登入
              <span className="rounded-full bg-[var(--color-surface)] px-2 py-0.5 text-xs font-bold text-[var(--color-tertiary)]">
                體驗用
              </span>
            </button>
          )}
          <button
            type="button"
            role="menuitem"
            onClick={() => {
              onVendorLogin();
              setOpen(false);
            }}
            className={`flex w-full items-center justify-between rounded-2xl px-4 py-3 text-left text-sm font-semibold text-[var(--color-muted-foreground)] transition hover:bg-[var(--color-canvas)] hover:text-[var(--color-primary)] ${account ? "mt-2" : ""}`}
          >
            我是服務廠商，前往廠商後台
            <ServiceIcon type="chevronRight" size={16} />
          </button>
        </div>
      )}
    </div>
  );
}

export function LoginPage() {
  const { login, isLoggedIn } = useAuth();
  const navigate = useNavigate();
  const [account, setAccount] = useState<DemoAccount | null>(null);
  const [error, setError] = useState("");
  const [mode, setMode] = useState<Mode>("choices");
  const [toastText, setToastText] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [formError, setFormError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (isLoggedIn) navigate("/home", { replace: true });
  }, [isLoggedIn, navigate]);

  useEffect(() => {
    fetchDemoAccounts()
      .then((r) => setAccount(r.accounts[0] ?? null))
      .catch(() => setError("無法連線到後端，請確認伺服器已啟動。"));
  }, []);

  function switchMode(next: Mode) {
    setMode(next);
    setFormError("");
    setPassword("");
  }

  async function handleLogin() {
    if (!email.trim() || !password) {
      setFormError("請輸入 Email 和密碼");
      return;
    }
    setSubmitting(true);
    setFormError("");
    try {
      const r = await loginWithEmail(email.trim(), password);
      login(r.token, r.name);
      navigate("/home");
    } catch (e) {
      setFormError(e instanceof ApiError ? e.message : "登入失敗，請稍後再試");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleRegister() {
    if (!email.trim() || !password) {
      setFormError("請輸入 Email 和密碼");
      return;
    }
    setSubmitting(true);
    setFormError("");
    try {
      const r = await registerAccount(email.trim(), password, name.trim());
      setToastText("註冊成功，歡迎！");
      login(r.token, r.name);
      navigate("/home");
    } catch (e) {
      setFormError(e instanceof ApiError ? e.message : "註冊失敗，請稍後再試");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="bg-blob-scene relative flex min-h-dvh items-center justify-center overflow-hidden px-4 py-10 sm:px-6 sm:py-14">
      <button
        type="button"
        onClick={() => navigate("/")}
        className="absolute left-4 top-4 z-10 flex items-center gap-1.5 rounded-full bg-surface/85 px-3.5 py-2 text-sm font-semibold text-[var(--color-muted-foreground)] shadow-sm backdrop-blur sm:left-6 sm:top-6"
      >
        <ServiceIcon type="back" size={20} />
        上一頁
      </button>

      {/* App 螢幕感卡片：固定手機 App 尺寸浮在色塊背景上，對應聊天機器人 App 參考稿的版面語言 */}
      <div className={SCREEN_CARD}>
        <div className="absolute right-6 top-6 z-10 sm:right-7 sm:top-7">
          <MoreOptionsMenu
            account={account}
            onDemoLogin={() => {
              if (!account) return;
              login(account.token, account.name);
              navigate("/home");
            }}
            onVendorLogin={() => navigate("/vendor/login")}
          />
        </div>

        {/* 固定外框內的可捲動內容區：內容比框高時（例如註冊表單＋鍵盤）在這裡捲動，不撐大外框 */}
        <div className="flex h-full w-full flex-col items-center overflow-y-auto px-7 py-10 sm:px-9">

        {/* 視覺上不放標題文字，讓大圖示直接當版面焦點；保留 sr-only 標題維持語意結構 */}
        <h1 className="sr-only">AI 智慧生活服務管家</h1>

        {/*
          中央大圖示：使用者提供的可愛 AI orb PNG（本身已內建光暈邊框），外層再疊一圈
          跨紫、桃紅、青三色的模糊光暈當背景，讓圖示像參考稿一樣「浮在會發光的柔霧裡」，
          而不是單調的貼一張圖上去。
        */}
        <div className="relative mt-4 flex h-44 w-44 items-center justify-center sm:mt-6 sm:h-52 sm:w-52">
          <span
            aria-hidden
            className="pointer-events-none absolute inset-[-20%] rounded-full opacity-80 blur-2xl"
            style={{
              backgroundImage:
                "radial-gradient(60% 60% at 35% 30%, var(--color-primary-accent) 0%, transparent 70%), radial-gradient(55% 55% at 70% 65%, var(--color-secondary) 0%, transparent 70%), radial-gradient(50% 50% at 50% 90%, var(--color-tertiary) 0%, transparent 70%)",
            }}
          />
          <img
            src={ORB_ICON}
            alt=""
            aria-hidden
            className="relative h-full w-full object-contain drop-shadow-[0_20px_45px_rgba(124,58,237,0.35)]"
          />
        </div>

        <p className="mt-6 text-center text-[var(--color-muted-foreground)]">說出需求，交給 AI 管家處理</p>

        <div className="relative mt-8 w-full space-y-3">
          {mode === "choices" && (
            <>
              <button
                type="button"
                onClick={() => switchMode("loginForm")}
                className="w-full rounded-2xl bg-[var(--color-primary)] px-6 py-4 text-base font-bold text-[var(--color-on-primary)] shadow-[0_16px_32px_-16px_var(--color-primary)] transition hover:opacity-90"
              >
                登入
              </button>
              <button
                type="button"
                onClick={() => switchMode("registerForm")}
                className="w-full rounded-2xl border-2 border-[var(--color-secondary)] px-6 py-4 text-base font-bold text-[var(--color-secondary)] transition hover:bg-[var(--color-secondary-soft)]"
              >
                註冊
              </button>
              {error && <p className="text-center text-sm text-[var(--color-danger)]">{error}</p>}
            </>
          )}

        {mode === "loginForm" && (
          <form
            className={FORM_CARD}
            onSubmit={(e) => {
              e.preventDefault();
              void handleLogin();
            }}
          >
            <input
              type="email"
              placeholder="Email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className={FIELD}
            />
            <input
              type="password"
              placeholder="密碼"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className={FIELD}
            />
            {formError && <p className="text-center text-[var(--color-danger)]">{formError}</p>}
            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-2xl bg-[var(--color-primary)] px-6 py-5 text-lg font-bold text-[var(--color-on-primary)] disabled:opacity-60"
            >
              {submitting ? "登入中…" : "登入"}
            </button>
            <button
              type="button"
              onClick={() => switchMode("choices")}
              className="w-full py-3.5 text-base text-[var(--color-muted-foreground)]"
            >
              ← 返回
            </button>
          </form>
        )}

        {mode === "registerForm" && (
          <form
            className={FORM_CARD}
            onSubmit={(e) => {
              e.preventDefault();
              void handleRegister();
            }}
          >
            <input
              type="text"
              placeholder="姓名（選填）"
              autoComplete="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className={FIELD}
            />
            <input
              type="email"
              placeholder="Email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className={FIELD}
            />
            <input
              type="password"
              placeholder="密碼（至少 8 碼）"
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className={FIELD}
            />
            {formError && <p className="text-center text-[var(--color-danger)]">{formError}</p>}
            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-2xl bg-[var(--color-secondary)] px-6 py-5 text-lg font-bold text-[var(--color-on-secondary)] disabled:opacity-60"
            >
              {submitting ? "註冊中…" : "註冊"}
            </button>
            <button
              type="button"
              onClick={() => switchMode("choices")}
              className="w-full py-3.5 text-base text-[var(--color-muted-foreground)]"
            >
              ← 返回
            </button>
          </form>
        )}
        </div>

        <p className="mt-6 text-center text-xs text-[var(--color-muted-foreground)]">
          Hackathon Demo：正式版將接入 Amazon Cognito 登入
        </p>
        </div>
      </div>

      <Toast text={toastText} onHide={() => setToastText(null)} />
    </main>
  );
}
