import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ApiError } from "../api/client";
import { actOnVendorRequest, getVendorRequest } from "../api/vendor";
import { ConfirmModal } from "../components/ConfirmModal";
import { ServiceIcon } from "../components/ServiceIcon";
import { StatusBadge } from "../components/StatusBadge";
import type { VendorAction, VendorRequestDetail } from "../types/vendor";

const ACTION_LABELS: Record<VendorAction, string> = {
  accept: "接單",
  reject: "婉拒",
};

const DONE_MESSAGES: Record<VendorAction, string> = {
  accept: "已接下這張單，狀態更新為「已確認」。",
  reject: "已婉拒這張單。",
};

// 案件現況也會隨 409 一起回來，直接拿來更新畫面就不必再打一次 API。
function conflictDetail(error: ApiError): VendorRequestDetail | null {
  return error.data.request_id ? (error.data as unknown as VendorRequestDetail) : null;
}

function formatTime(value: string) {
  if (!value) return "";
  return new Date(value).toLocaleString("zh-TW", {
    year: "numeric",
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function VendorRequestDetailPage() {
  const { requestId = "" } = useParams();
  const navigate = useNavigate();
  const [detail, setDetail] = useState<VendorRequestDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  // 送出中的動作；同時用來把兩顆按鈕都鎖住，避免連點送出兩次。
  const [acting, setActing] = useState<VendorAction | null>(null);
  const [notice, setNotice] = useState<{ tone: "ok" | "warn"; text: string } | null>(null);
  const [confirmingReject, setConfirmingReject] = useState(false);

  useEffect(() => {
    setLoading(true);
    getVendorRequest(requestId)
      .then(setDetail)
      .catch((e) => {
        if (e instanceof ApiError && e.code === "UNAUTHORIZED") {
          navigate("/vendor/login");
          return;
        }
        setError(e instanceof ApiError ? e.message : "載入失敗，請稍後再試");
      })
      .finally(() => setLoading(false));
  }, [navigate, requestId]);

  const runAction = (action: VendorAction) => {
    if (!detail || acting) return;
    setActing(action);
    setNotice(null);
    actOnVendorRequest(requestId, action, detail.version)
      .then((result) => {
        setDetail(result);
        setNotice({ tone: "ok", text: DONE_MESSAGES[action] });
      })
      .catch((e) => {
        if (e instanceof ApiError && e.code === "UNAUTHORIZED") {
          navigate("/vendor/login");
          return;
        }
        if (e instanceof ApiError) {
          // 狀態機或樂觀鎖擋下來：把畫面換成案件現在的樣子，按鈕也跟著收掉。
          const current = conflictDetail(e);
          if (current) setDetail(current);
          setNotice({ tone: "warn", text: e.message });
          return;
        }
        setNotice({ tone: "warn", text: "操作失敗，請稍後再試" });
      })
      .finally(() => setActing(null));
  };

  return (
    <main className="mx-auto min-h-dvh max-w-3xl bg-canvas px-5 pb-16 pt-8 sm:px-8">
      <header className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => navigate("/vendor/requests")}
          className="flex h-11 w-11 items-center justify-center rounded-full bg-[var(--color-surface)] text-[var(--color-muted-foreground)] shadow-sm transition hover:text-brand"
          aria-label="返回案件清單"
        >
          <ServiceIcon type="back" size={20} />
        </button>
        <div>
          <p className="text-sm font-semibold text-brand">案件明細</p>
          {/* 案件編號屬資料型文字，用 --font-mono 讓編號等寬易掃視（Requirement 7.3） */}
          <h1 className="font-[family-name:var(--font-mono)] text-2xl font-black text-[var(--color-foreground)]">
            {requestId}
          </h1>
        </div>
      </header>

      {loading && (
        <p className="mt-8 rounded-2xl bg-[var(--color-surface)] p-6 text-center text-[var(--color-muted-foreground)] shadow-sm">
          正在載入案件…
        </p>
      )}
      {!loading && error && (
        <p className="mt-8 rounded-2xl bg-[var(--color-surface)] p-6 text-center text-danger shadow-sm">{error}</p>
      )}

      {!loading && detail && (
        <>
          <section className="mt-7 rounded-[28px] bg-[var(--color-surface)] p-6 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-xl font-black text-[var(--color-foreground)]">{detail.service_name}</h2>
              <StatusBadge status={detail.status} label={detail.status_label} />
            </div>
            <dl className="mt-4 grid gap-x-6 gap-y-2 text-base sm:grid-cols-2">
              <div className="flex gap-2">
                <dt className="shrink-0 text-[var(--color-muted-foreground)]">客戶</dt>
                <dd className="font-bold text-[var(--color-foreground)]">{detail.customer_name}</dd>
              </div>
              <div className="flex gap-2">
                <dt className="shrink-0 text-[var(--color-muted-foreground)]">建立時間</dt>
                <dd className="text-[var(--color-foreground)]">{formatTime(detail.created_at)}</dd>
              </div>
              <div className="flex gap-2">
                <dt className="shrink-0 text-[var(--color-muted-foreground)]">最近更新</dt>
                <dd className="text-[var(--color-foreground)]">{formatTime(detail.updated_at)}</dd>
              </div>
              {detail.estimated_fee_min !== undefined && (
                <div className="flex gap-2">
                  <dt className="shrink-0 text-[var(--color-muted-foreground)]">系統預估運費</dt>
                  <dd className="font-bold text-[var(--color-foreground)]">
                    NT${detail.estimated_fee_min}–{detail.estimated_fee_max}
                  </dd>
                </div>
              )}
            </dl>
          </section>

          <section className="mt-5 rounded-[28px] bg-[var(--color-surface)] p-6 shadow-sm">
            <h2 className="text-lg font-black text-[var(--color-foreground)]">服務內容</h2>
            <dl className="mt-4 divide-y divide-[var(--color-border)]">
              {detail.fields.map((field) => (
                <div key={field.id} className="flex flex-wrap gap-x-4 gap-y-1 py-3">
                  <dt className="w-28 shrink-0 text-[var(--color-muted-foreground)]">{field.label}</dt>
                  <dd className="min-w-0 flex-1 font-medium text-[var(--color-foreground)]">{field.value}</dd>
                </div>
              ))}
              {detail.fields.length === 0 && (
                <p className="py-3 text-[var(--color-muted-foreground)]">這筆案件沒有填寫內容。</p>
              )}
            </dl>
          </section>

          {notice && (
            <p
              role="status"
              className={`mt-5 rounded-2xl p-4 text-center text-base font-bold ${
                notice.tone === "ok"
                  ? "bg-success-soft text-success"
                  : "bg-accent-soft text-accent"
              }`}
            >
              {notice.text}
            </p>
          )}

          {detail.available_actions.length > 0 ? (
            <section className="mt-5 flex flex-col gap-3 sm:flex-row">
              {detail.available_actions.includes("accept") && (
                <button
                  type="button"
                  onClick={() => runAction("accept")}
                  disabled={acting !== null}
                  className="flex-1 rounded-2xl bg-brand px-6 py-4 text-lg font-black text-white shadow-sm transition hover:brightness-105 disabled:opacity-50"
                >
                  {acting === "accept" ? "處理中…" : "接下這張單"}
                </button>
              )}
              {detail.available_actions.includes("reject") && (
                <button
                  type="button"
                  onClick={() => setConfirmingReject(true)}
                  disabled={acting !== null}
                  className="flex-1 rounded-2xl border-2 border-[var(--color-border)] bg-[var(--color-surface)] px-6 py-4 text-lg font-bold text-[var(--color-muted-foreground)] transition hover:border-danger hover:text-danger disabled:opacity-50"
                >
                  {acting === "reject" ? "處理中…" : "婉拒這張單"}
                </button>
              )}
            </section>
          ) : (
            <p className="mt-5 text-center text-sm text-[var(--color-muted-foreground)]">
              這張單目前是「{detail.status_label}」，沒有可以執行的動作。
            </p>
          )}
        </>
      )}

      <ConfirmModal
        open={confirmingReject}
        text={`確定要婉拒「${detail?.service_name ?? "這張單"}」嗎？婉拒後就不能再接單了。`}
        confirmLabel={ACTION_LABELS.reject}
        cancelLabel="再想想"
        onConfirm={() => {
          setConfirmingReject(false);
          runAction("reject");
        }}
        onCancel={() => setConfirmingReject(false)}
      />
    </main>
  );
}
