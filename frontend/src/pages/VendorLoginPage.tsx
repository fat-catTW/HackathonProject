import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError } from "../api/client";
import { fetchVendorDemoAccounts, vendorLogin } from "../api/vendor";
import { useVendorAuth } from "../hooks/useVendorAuth";
import type { VendorDemoAccount } from "../types/vendor";

export function VendorLoginPage() {
  const { login, isLoggedIn } = useVendorAuth();
  const navigate = useNavigate();
  const [demoAccounts, setDemoAccounts] = useState<VendorDemoAccount[]>([]);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [formError, setFormError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (isLoggedIn) navigate("/vendor/requests", { replace: true });
  }, [isLoggedIn, navigate]);

  useEffect(() => {
    fetchVendorDemoAccounts()
      .then((r) => setDemoAccounts(r.accounts))
      .catch(() => setDemoAccounts([]));
  }, []);

  async function submit(withEmail: string, withPassword: string) {
    if (!withEmail.trim() || !withPassword) {
      setFormError("請輸入 Email 和密碼");
      return;
    }
    setSubmitting(true);
    setFormError("");
    try {
      const r = await vendorLogin(withEmail.trim(), withPassword);
      login(r.token, r.name, r.vendor_id);
      navigate("/vendor/requests");
    } catch (e) {
      setFormError(e instanceof ApiError ? e.message : "登入失敗，請稍後再試");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="flex min-h-dvh flex-col items-center justify-center bg-canvas px-6 py-12">
      <div className="w-full max-w-md">
        <p className="text-sm font-bold tracking-wide text-brand">UNI-PIC 統一資訊</p>
        <h1 className="mt-1 text-3xl font-black text-slate-900">廠商後台</h1>
        <p className="mt-2 text-gray-500">登入後可查看貴公司承接的諮詢單與訂單。</p>

        <form
          className="mt-8 flex flex-col gap-4 rounded-[28px] bg-white p-6 shadow-sm"
          onSubmit={(e) => {
            e.preventDefault();
            void submit(email, password);
          }}
        >
          <label className="text-sm font-bold text-slate-700" htmlFor="vendor-email">
            廠商 Email
          </label>
          <input
            id="vendor-email"
            type="email"
            autoComplete="username"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded-2xl border-2 border-gray-200 px-4.5 py-4 text-lg"
          />
          <label className="text-sm font-bold text-slate-700" htmlFor="vendor-password">
            密碼
          </label>
          <input
            id="vendor-password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-2xl border-2 border-gray-200 px-4.5 py-4 text-lg"
          />
          {formError && <p className="text-center text-red-600">{formError}</p>}
          <button
            type="submit"
            disabled={submitting}
            className="mt-2 w-full rounded-2xl bg-brand px-6 py-4.5 text-lg font-bold text-white disabled:opacity-60"
          >
            {submitting ? "登入中…" : "登入"}
          </button>
        </form>

        {demoAccounts.length > 0 && (
          <section className="mt-6 rounded-[28px] border-2 border-dashed border-gray-300 bg-white p-5">
            <p className="text-sm font-bold text-slate-700">Demo 廠商帳號</p>
            <div className="mt-3 space-y-2.5">
              {demoAccounts.map((account) => (
                <button
                  key={account.email}
                  type="button"
                  disabled={submitting}
                  onClick={() => void submit(account.email, account.password)}
                  className="flex w-full items-center justify-between gap-3 rounded-2xl bg-brand-soft px-4 py-3.5 text-left transition hover:bg-brand hover:text-white disabled:opacity-60"
                >
                  <span className="font-bold">{account.name}</span>
                  <span className="truncate text-sm opacity-70">{account.email}</span>
                </button>
              ))}
            </div>
          </section>
        )}

        <button
          type="button"
          onClick={() => navigate("/")}
          className="mt-6 w-full py-3 text-base text-gray-500"
        >
          ← 回到住戶端
        </button>
      </div>
    </main>
  );
}
