import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { fetchDemoAccounts, type DemoAccount } from "../api/auth";
import { useAuth } from "../hooks/useAuth";

export function LoginPage() {
  const { login, isLoggedIn } = useAuth();
  const navigate = useNavigate();
  const [accounts, setAccounts] = useState<DemoAccount[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    if (isLoggedIn) navigate("/", { replace: true });
  }, [isLoggedIn, navigate]);

  useEffect(() => {
    fetchDemoAccounts()
      .then((response) => setAccounts(response.accounts))
      .catch(() => setError("目前無法取得測試帳號，請確認後端服務已啟動。"));
  }, []);

  return (
    <main className="mx-auto flex min-h-dvh max-w-md flex-col items-center justify-center px-6">
      <div className="mb-2 flex h-20 w-20 items-center justify-center rounded-3xl bg-pine text-4xl text-white">
        管
      </div>
      <h1 className="text-2xl font-black">AI 智慧生活服務管家</h1>
      <p className="mt-2 text-center text-gray-500">
        選一個 demo 帳號登入，開始測試服務預約流程。
      </p>

      <div className="mt-10 w-full space-y-3">
        {accounts.map((account) => (
          <button
            key={account.token}
            type="button"
            onClick={() => {
              login(account.token, account.name);
              navigate("/");
            }}
            className="w-full rounded-2xl bg-pine px-6 py-4 text-lg font-bold text-white transition hover:bg-pine-dark focus-visible:outline focus-visible:outline-2 focus-visible:outline-pine"
          >
            以 {account.name} 身分登入
          </button>
        ))}
        {error && <p className="text-center text-red-600">{error}</p>}
      </div>
      <p className="mt-6 text-center text-sm text-gray-400">
        Hackathon Demo 模式下，登入資訊由後端提供，正式版可接 Amazon Cognito。
      </p>
    </main>
  );
}
