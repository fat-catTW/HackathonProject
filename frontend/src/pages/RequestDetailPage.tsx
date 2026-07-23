import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { sendMessage } from "../api/chat";
import { cancelRequest, getRequest, simulateStatus } from "../api/requests";
import { ChatMessage } from "../components/ChatMessage";
import { ConfirmModal } from "../components/ConfirmModal";
import { ServiceIcon } from "../components/ServiceIcon";
import { StatusBadge } from "../components/StatusBadge";
import { Toast } from "../components/Toast";
import { fieldLabel, fieldValueLabel } from "../utils/fieldLabels";
import { serviceIconType } from "../utils/serviceIcons";
import type { RequestDetail } from "../types/request";

export function RequestDetailPage() {
  const { requestId = "" } = useParams();
  const navigate = useNavigate();
  const [detail, setDetail] = useState<RequestDetail | null>(null);
  const [error, setError] = useState("");
  const [toastText, setToastText] = useState<string | null>(null);
  const [confirmCancelOpen, setConfirmCancelOpen] = useState(false);
  const [followUp, setFollowUp] = useState("");
  const [sendingFollowUp, setSendingFollowUp] = useState(false);

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
        <button type="button" onClick={() => navigate("/home")} className="mt-4 text-brand underline">
          回到首頁
        </button>
      </main>
    );
  }
  if (!detail) {
    return <main className="mx-auto max-w-md px-5 pt-16 text-gray-400">載入中⋯</main>;
  }

  const cancellable = !["COMPLETED", "CANCELLED"].includes(detail.status);
  const nextDemo: Record<string, { to: string; label: string }> = {
    SUBMITTED: { to: "CONFIRMED", label: "（Demo）模擬廠商確認" },
    PENDING_PROVIDER: { to: "CONFIRMED", label: "（Demo）模擬廠商確認" },
    CONFIRMED: { to: "IN_PROGRESS", label: "（Demo）模擬服務開始" },
    IN_PROGRESS: { to: "COMPLETED", label: "（Demo）模擬服務完成" },
  };
  const demo = nextDemo[detail.status];

  async function submitFollowUp() {
    const message = followUp.trim();
    if (!message || !detail?.session_id || sendingFollowUp) return;
    setSendingFollowUp(true);
    try {
      const r = await sendMessage(detail.session_id, message);
      setDetail({ ...detail, events: [...detail.events, { role: "USER", content: message }, { role: "ASSISTANT", content: r.reply }] });
      setFollowUp("");
    } catch {
      setToastText("訊息傳送失敗，請再試一次");
    } finally {
      setSendingFollowUp(false);
    }
  }

  return (
    <main className="mx-auto max-w-md bg-canvas pb-16">
      <header className="flex items-center gap-3 border-b border-gray-200 bg-white px-5 py-4.5">
        <button type="button" onClick={() => navigate("/home")} className="text-gray-500">
          <ServiceIcon type="back" size={22} />
        </button>
        <div className="text-base font-black">案件詳情</div>
      </header>

      <div className="flex flex-col gap-5 p-6">
        <div className="flex items-center gap-4">
          <span className="flex h-15 w-15 flex-none items-center justify-center rounded-2xl bg-brand-soft text-brand">
            <ServiceIcon type={serviceIconType(detail.service_name)} size={30} />
          </span>
          <div>
            <div className="text-xl font-extrabold">{detail.service_name}</div>
            <div className="mt-1.5">
              <StatusBadge status={detail.status} label={detail.status_label} />
            </div>
            <div className="mt-1 font-mono text-xs text-gray-400">{detail.request_id}</div>
          </div>
        </div>

        <div className="rounded-3xl border border-gray-200 bg-white px-5">
          {Object.entries(detail.form_data).map(([k, v]) => (
            <div key={k} className="flex justify-between gap-3 border-b border-gray-100 py-3.5 last:border-b-0">
              <span className="text-gray-500">{fieldLabel(k)}</span>
              <span className="text-right font-bold">{fieldValueLabel(v)}</span>
            </div>
          ))}
          <div className="border-t border-dashed border-gray-200 py-3.5 text-sm text-gray-400">
            建立於 {new Date(detail.created_at).toLocaleString("zh-TW")}
            <br />
            最後更新 {new Date(detail.updated_at).toLocaleString("zh-TW")}
          </div>
        </div>

        {detail.events.length > 0 && (
          <div className="rounded-3xl border border-gray-200 bg-white p-5">
            <div className="mb-3.5 flex items-center gap-2 text-base font-extrabold">
              <ServiceIcon type="chat" size={18} className="text-brand" />
              對話紀錄
            </div>
            <div className="flex max-h-72 flex-col gap-2.5 overflow-y-auto">
              {detail.events.map((e, i) => (
                <ChatMessage key={i} event={e} />
              ))}
            </div>
            <form
              className="mt-3.5 flex gap-2.5"
              onSubmit={(e) => {
                e.preventDefault();
                void submitFollowUp();
              }}
            >
              <input
                value={followUp}
                onChange={(e) => setFollowUp(e.target.value)}
                placeholder="繼續詢問案件狀況⋯"
                className="min-w-0 flex-1 rounded-xl border-2 border-gray-200 px-3.5 py-2.5 text-sm outline-none focus:border-brand"
              />
              <button
                type="submit"
                disabled={sendingFollowUp || !followUp.trim()}
                className="rounded-xl bg-brand px-4 py-2.5 text-sm font-bold text-white disabled:opacity-40"
              >
                送出
              </button>
            </form>
          </div>
        )}

        <div className="flex flex-wrap gap-3">
          {cancellable && (
            <button
              type="button"
              onClick={() => setConfirmCancelOpen(true)}
              className="flex-1 rounded-2xl border-2 border-red-200 bg-white px-4.5 py-4 text-sm font-bold text-danger"
            >
              取消案件
            </button>
          )}
          <button
            type="button"
            onClick={() => setToastText("案件已送出，如需修改請先取消後重新申請")}
            className="flex-1 rounded-2xl border-2 border-brand bg-white px-4.5 py-4 text-sm font-bold text-brand"
          >
            修改資料
          </button>
          <button
            type="button"
            onClick={() => navigate("/new", { state: { autoMessage: detail.service_name } })}
            className="flex-1 rounded-2xl bg-brand px-4.5 py-4 text-sm font-bold text-white"
          >
            重新申請相同服務
          </button>
          {demo && (
            <button
              type="button"
              onClick={() => simulateStatus(detail.request_id, demo.to).then(load)}
              className="w-full rounded-2xl border-2 border-brand px-6 py-3.5 font-bold text-brand"
            >
              {demo.label}
            </button>
          )}
        </div>
      </div>

      <ConfirmModal
        open={confirmCancelOpen}
        text="確定要取消這筆服務案件嗎？"
        confirmLabel="確定取消案件"
        cancelLabel="再想想"
        onCancel={() => setConfirmCancelOpen(false)}
        onConfirm={() => {
          setConfirmCancelOpen(false);
          cancelRequest(detail.request_id)
            .then(load)
            .then(() => setToastText("案件已取消"));
        }}
      />
      <Toast text={toastText} onHide={() => setToastText(null)} />
    </main>
  );
}
