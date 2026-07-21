import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { cancelRequest, getRequest, simulateStatus } from "../api/requests";
import { ChatMessage } from "../components/ChatMessage";
import { StatusBadge } from "../components/StatusBadge";
import type { RequestDetail } from "../types/request";

const FIELD_LABELS: Record<string, string> = {
  quantity: "數量",
  hours: "服務時數",
  machine_type: "洗衣機類型",
  issue_description: "問題描述",
  preferred_date: "希望日期",
  preferred_time_slot: "希望時段",
  address: "服務地址",
  phone: "聯絡電話",
};
const VALUE_LABELS: Record<string, string> = {
  MORNING: "上午", AFTERNOON: "下午", EVENING: "晚上",
  TOP_LOAD: "直立式", FRONT_LOAD: "滾筒式",
};

export function RequestDetailPage() {
  const { requestId = "" } = useParams();
  const navigate = useNavigate();
  const [detail, setDetail] = useState<RequestDetail | null>(null);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    getRequest(requestId)
      .then(setDetail)
      .catch((e) => setError(e.message));
  }, [requestId]);

  useEffect(load, [load]);

  if (error) {
    return (
      <main className="mx-auto max-w-md px-5 pt-16 text-center">
        <p className="text-red-600">{error}</p>
        <Link to="/" className="mt-4 inline-block text-pine underline">
          回到首頁
        </Link>
      </main>
    );
  }
  if (!detail) {
    return <main className="mx-auto max-w-md px-5 pt-16 text-gray-400">載入中⋯</main>;
  }

  const cancellable = !["COMPLETED", "CANCELLED"].includes(detail.status);
  const nextDemo: Record<string, { to: string; label: string }> = {
    SUBMITTED: { to: "CONFIRMED", label: "（Demo）模擬廠商確認" },
    CONFIRMED: { to: "IN_PROGRESS", label: "（Demo）模擬服務開始" },
    IN_PROGRESS: { to: "COMPLETED", label: "（Demo）模擬服務完成" },
  };
  const demo = nextDemo[detail.status];

  return (
    <main className="mx-auto max-w-md px-5 pb-16 pt-6">
      <header className="flex items-center justify-between">
        <Link to="/" className="text-sm text-gray-400 hover:text-ink">
          ← 我的服務
        </Link>
        <StatusBadge status={detail.status} label={detail.status_label} />
      </header>

      <h1 className="mt-4 text-2xl font-black">{detail.service_name}</h1>
      <p className="mt-1 text-sm text-gray-500">案件編號 {detail.request_id}</p>

      <section className="mt-6 rounded-2xl border border-pine-soft bg-white p-4">
        <h2 className="font-bold text-pine">申請內容</h2>
        <dl className="mt-3 space-y-2">
          {Object.entries(detail.form_data).map(([k, v]) => (
            <div key={k} className="flex justify-between gap-3">
              <dt className="text-gray-500">{FIELD_LABELS[k] ?? k}</dt>
              <dd className="text-right font-medium">
                {VALUE_LABELS[String(v)] ?? v}
              </dd>
            </div>
          ))}
        </dl>
        <p className="mt-3 border-t border-dashed border-pine-soft pt-3 text-sm text-gray-400">
          建立於 {new Date(detail.created_at).toLocaleString("zh-TW")}
          <br />
          最後更新 {new Date(detail.updated_at).toLocaleString("zh-TW")}
        </p>
      </section>

      {detail.events.length > 0 && (
        <section className="mt-6">
          <h2 className="font-bold text-pine">對話紀錄</h2>
          <div className="mt-3 space-y-3">
            {detail.events.map((e, i) => (
              <ChatMessage key={i} event={e} />
            ))}
          </div>
        </section>
      )}

      <div className="mt-8 space-y-3">
        {demo && (
          <button
            type="button"
            onClick={() => simulateStatus(detail.request_id, demo.to).then(load)}
            className="w-full rounded-2xl border border-pine px-6 py-3.5 font-bold text-pine hover:bg-pine-soft"
          >
            {demo.label}
          </button>
        )}
        <button
          type="button"
          onClick={() => navigate("/new")}
          className="w-full rounded-2xl bg-pine px-6 py-3.5 font-bold text-white hover:bg-pine-dark"
        >
          重新申請相同服務
        </button>
        {cancellable && (
          <button
            type="button"
            onClick={() => cancelRequest(detail.request_id).then(load)}
            className="w-full rounded-2xl px-6 py-3 text-gray-400 hover:text-red-600"
          >
            取消此案件
          </button>
        )}
      </div>
    </main>
  );
}
