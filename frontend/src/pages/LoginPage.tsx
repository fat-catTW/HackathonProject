import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  fetchDemoAccounts,
  loginWithEmail,
  registerAccount,
  type DemoAccount,
} from "../api/auth";
import { ApiError } from "../api/client";
import { Mascot } from "../components/Mascot";
import { ServiceIcon } from "../components/ServiceIcon";
import { Toast } from "../components/Toast";
import { useAuth } from "../hooks/useAuth";

type Mode = "choices" | "loginForm" | "registerForm";

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
    <main className="mx-auto flex min-h-dvh max-w-md flex-col items-center justify-center bg-canvas px-8 py-12">
      <button
        type="button"
        onClick={() => navigate("/")}
        className="absolute left-6 top-6 flex items-center gap-1.5 text-sm font-semibold text-gray-500"
      >
        <ServiceIcon type="back" size={20} />
        上一頁
      </button>

      <Mascot size={128} />
      <h1 className="mt-3 text-center text-2xl font-black">AI 智慧生活服務管家</h1>
      <p className="mt-1.5 text-sm font-bold tracking-wide text-brand">UNI-PIC 統一資訊</p>
      <p className="mt-2.5 text-center text-gray-500">說出需求，交給 AI 管家處理</p>

      <div className="mt-11 w-full space-y-4">
        {mode === "choices" && (
          <>
            <button
              type="button"
              onClick={() => switchMode("loginForm")}
              className="w-full rounded-2xl bg-brand px-6 py-5 text-lg font-bold text-white"
            >
              登入
            </button>
            <button
              type="button"
              onClick={() => switchMode("registerForm")}
              className="w-full rounded-2xl border-2 border-brand px-6 py-5 text-lg font-bold text-brand"
            >
              註冊
            </button>
            <div className="text-center text-sm text-gray-400">或</div>
            {account && (
              <button
                type="button"
                onClick={() => {
                  login(account.token, account.name);
                  navigate("/home");
                }}
                className="flex w-full items-center justify-center gap-2.5 rounded-2xl border-2 border-dashed border-gray-300 bg-white px-6 py-5 text-lg font-bold text-brand"
              >
                <span>Demo Account 一鍵登入</span>
                <span className="rounded-full bg-brand-soft px-2.5 py-1 text-xs font-bold text-brand">
                  體驗用
                </span>
              </button>
            )}
            {error && <p className="text-center text-red-600">{error}</p>}
          </>
        )}

        {mode === "loginForm" && (
          <form
            className="flex flex-col gap-4"
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
              className="w-full rounded-2xl border-2 border-gray-200 px-4.5 py-4.5 text-lg"
            />
            <input
              type="password"
              placeholder="密碼"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-2xl border-2 border-gray-200 px-4.5 py-4.5 text-lg"
            />
            {formError && <p className="text-center text-red-600">{formError}</p>}
            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-2xl bg-brand px-6 py-5 text-lg font-bold text-white disabled:opacity-60"
            >
              {submitting ? "登入中…" : "登入"}
            </button>
            <button
              type="button"
              onClick={() => switchMode("choices")}
              className="w-full py-3.5 text-base text-gray-500"
            >
              ← 返回
            </button>
          </form>
        )}

        {mode === "registerForm" && (
          <form
            className="flex flex-col gap-4"
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
              className="w-full rounded-2xl border-2 border-gray-200 px-4.5 py-4.5 text-lg"
            />
            <input
              type="email"
              placeholder="Email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-2xl border-2 border-gray-200 px-4.5 py-4.5 text-lg"
            />
            <input
              type="password"
              placeholder="密碼（至少 8 碼）"
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-2xl border-2 border-gray-200 px-4.5 py-4.5 text-lg"
            />
            {formError && <p className="text-center text-red-600">{formError}</p>}
            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-2xl bg-brand px-6 py-5 text-lg font-bold text-white disabled:opacity-60"
            >
              {submitting ? "註冊中…" : "註冊"}
            </button>
            <button
              type="button"
              onClick={() => switchMode("choices")}
              className="w-full py-3.5 text-base text-gray-500"
            >
              ← 返回
            </button>
          </form>
        )}
      </div>

      <p className="mt-8 text-center text-sm text-gray-400">
        Hackathon Demo：正式版將接入 Amazon Cognito 登入
      </p>

      <Toast text={toastText} onHide={() => setToastText(null)} />
    </main>
  );
}
