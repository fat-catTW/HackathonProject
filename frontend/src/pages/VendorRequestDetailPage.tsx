import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ApiError } from "../api/client";
import { getVendorApiForKind } from "../api/vendorRouting";
import { vendorKindOf } from "../types/vendor";
import { useVendorAuth } from "../hooks/useVendorAuth";
import { getVendorCaseTags } from "../api/vendorTags";
import { CaseTagEditor } from "../components/CaseTagEditor";
import { ConfirmModal } from "../components/ConfirmModal";
import { ServiceIcon } from "../components/ServiceIcon";
import { StatusBadge } from "../components/StatusBadge";
import type { VendorAction, VendorRequestDetail } from "../types/vendor";

const ACTION_LABELS: Record<VendorAction, string> = {
  accept: "接單",
  reject: "婉拒",
  start: "開始服務",
  complete: "完成服務",
  verify: "核銷",
  prepare: "開始備餐",
  pickup: "外送員已取餐",
  dispatch: "開始配送",
  deliver: "送達",
  confirm: "確認訂單",
  ship: "出貨",
};

const DONE_MESSAGES: Record<VendorAction, string> = {
  accept: "已接下這張單，狀態更新為「已確認」。",
  reject: "已婉拒這張單。",
  start: "已標記開始服務。",
  complete: "已標記完成服務。",
  verify: "已完成核銷。",
  prepare: "已標記開始備餐。",
  pickup: "已標記外送員取餐。",
  dispatch: "已標記開始配送。",
  deliver: "已標記送達。",
  confirm: "已確認訂單。",
  ship: "已標記出貨。",
};

// 拒絕／婉拒類動作破壞性較高，按下前要跳確認彈窗；其餘動作直接執行。
const DESTRUCTIVE_ACTIONS: VendorAction[] = ["reject"];

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
  const { vendorId } = useVendorAuth();
  const vendorApiSet = getVendorApiForKind(vendorKindOf(vendorId));
  const [detail, setDetail] = useState<VendorRequestDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  // 送出中的動作；同時用來把兩顆按鈕都鎖住，避免連點送出兩次。
  const [acting, setActing] = useState<VendorAction | null>(null);
  const [notice, setNotice] = useState<{ tone: "ok" | "warn"; text: string } | null>(null);
  const [confirmingReject, setConfirmingReject] = useState(false);
  // 解密後的聯絡資訊（欄位 id → 完整內容）；null 代表還沒解鎖，畫面維持遮罩。
  const [contact, setContact] = useState<Record<string, string> | null>(null);
  const [revealing, setRevealing] = useState(false);
  const [contactError, setContactError] = useState("");
  // 廠商自己貼的標籤，跟案件本體分開存也分開讀（見 api/vendorTags）。
  const [tags, setTags] = useState<string[]>([]);

  const serviceFields = detail?.fields.filter((f) => !f.masked) ?? [];
  const contactFields = detail?.fields.filter((f) => f.masked) ?? [];

  useEffect(() => {
    setLoading(true);
    vendorApiSet
      .get(requestId)
      .then(setDetail)
      .catch((e) => {
        if (e instanceof ApiError && e.code === "UNAUTHORIZED") {
          navigate("/vendor/login");
          return;
        }
        setError(e instanceof ApiError ? e.message : "載入失敗，請稍後再試");
      })
      .finally(() => setLoading(false));
  }, [navigate, requestId, vendorApiSet]);

  useEffect(() => {
    // 標籤是輔助資訊：讀失敗就當作還沒貼，不要因為它讓整頁變成錯誤畫面。真的有問題
    // 時，貼標籤的動作會自己回報（CaseTagEditor 的錯誤訊息）。
    getVendorCaseTags(requestId)
      .then((result) => setTags(result.tags))
      .catch(() => setTags([]));
  }, [requestId]);

  const revealContact = () => {
    if (revealing) return;
    setRevealing(true);
    setContactError("");
    vendorApiSet
      .reveal(requestId)
      .then((result) => {
        setContact(Object.fromEntries(result.contact.map((c) => [c.id, c.value])));
        // 這次檢視也會出現在紀錄裡，直接換上後端回傳的完整清單。
        setDetail((current) =>
          current ? { ...current, contact_access_log: result.contact_access_log } : current,
        );
      })
      .catch((e) => {
        if (e instanceof ApiError && e.code === "UNAUTHORIZED") {
          navigate("/vendor/login");
          return;
        }
        setContactError(e instanceof ApiError ? e.message : "無法顯示聯絡資訊，請稍後再試");
      })
      .finally(() => setRevealing(false));
  };

  const runAction = (action: VendorAction) => {
    if (!detail || acting) return;
    setActing(action);
    setNotice(null);
    vendorApiSet
      .act(requestId, action, detail.version)
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
            {/*
              AI 需求摘要：把冗長的諮詢單濃縮成一句話，讓派工的人不必先讀完下面整段
              「服務內容」才知道這張單在講什麼。放在服務名稱正下方、欄位表格之前，
              因為它是這張單的第一眼資訊。摘要在建單當下就算好存進案件，這裡只是讀
              欄位，不會另外打 AI。
            */}
            {detail.ai_summary && (
              <p className="mt-3 flex gap-2 rounded-2xl bg-[var(--color-primary-soft)] px-4 py-3 text-base font-medium text-[var(--color-foreground)]">
                <span className="shrink-0 font-black text-[var(--color-primary)]">AI 摘要</span>
                <span className="min-w-0">{detail.ai_summary}</span>
              </p>
            )}
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

          {/*
            標籤放在案件摘要正下方：派工的人開單第一件事就是判斷「這張要不要插隊、
            要不要先報價」，標籤既是這個判斷的結果、也是下次在清單上快速挑出它的依據。
          */}
          <CaseTagEditor requestId={requestId} tags={tags} onTagsChange={setTags} />

          <section className="mt-5 rounded-[28px] bg-[var(--color-surface)] p-6 shadow-sm">
            <h2 className="text-lg font-black text-[var(--color-foreground)]">服務內容</h2>
            <dl className="mt-4 divide-y divide-[var(--color-border)]">
              {serviceFields.map((field) => (
                <div key={field.id} className="flex flex-wrap gap-x-4 gap-y-1 py-3">
                  <dt className="w-28 shrink-0 text-[var(--color-muted-foreground)]">{field.label}</dt>
                  <dd className="min-w-0 flex-1 font-medium text-[var(--color-foreground)]">{field.value}</dd>
                </div>
              ))}
              {serviceFields.length === 0 && (
                <p className="py-3 text-[var(--color-muted-foreground)]">這筆案件沒有填寫內容。</p>
              )}
            </dl>
          </section>

          {contactFields.length > 0 && (
            <section className="mt-5 rounded-[28px] bg-[var(--color-surface)] p-6 shadow-sm">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h2 className="text-lg font-black text-[var(--color-foreground)]">聯絡資訊</h2>
                <span className="rounded-full bg-[var(--color-primary-soft)] px-3 py-1 text-sm font-bold text-[var(--color-primary)]">
                  {contact ? "已解密顯示" : "已加密保護"}
                </span>
              </div>
              <dl className="mt-4 divide-y divide-[var(--color-border)]">
                {contactFields.map((field) => (
                  <div key={field.id} className="flex flex-wrap gap-x-4 gap-y-1 py-3">
                    <dt className="w-28 shrink-0 text-[var(--color-muted-foreground)]">
                      {field.label}
                    </dt>
                    <dd
                      className={`min-w-0 flex-1 font-medium ${
                        contact
                          ? "text-[var(--color-foreground)]"
                          : "tracking-wider text-[var(--color-muted-foreground)]"
                      }`}
                    >
                      {contact?.[field.id] ?? field.value}
                    </dd>
                  </div>
                ))}
              </dl>

              {!contact && (
                <>
                  <button
                    type="button"
                    onClick={revealContact}
                    disabled={revealing}
                    className="mt-4 w-full rounded-2xl border-2 border-[var(--color-primary)] bg-[var(--color-surface)] px-6 py-3 text-base font-black text-[var(--color-primary)] transition hover:bg-[var(--color-primary-soft)] disabled:opacity-50"
                  >
                    {revealing ? "解密中…" : "顯示完整聯絡資訊"}
                  </button>
                  <p className="mt-2 text-center text-sm text-[var(--color-muted-foreground)]">
                    住戶的聯絡方式加密保存，每次檢視都會留下紀錄。
                  </p>
                </>
              )}
              {contactError && (
                <p
                  role="alert"
                  className="mt-3 text-center text-sm font-bold text-[var(--color-danger)]"
                >
                  {contactError}
                </p>
              )}

              {detail.contact_access_log.length > 0 && (
                <div className="mt-5 rounded-2xl bg-[var(--color-canvas)] p-4">
                  <h3 className="text-sm font-black text-[var(--color-muted-foreground)]">
                    存取紀錄
                  </h3>
                  <ul className="mt-2 space-y-1.5">
                    {detail.contact_access_log.map((entry) => (
                      <li
                        key={`${entry.at}-${entry.fields.join()}`}
                        className="text-sm text-[var(--color-muted-foreground)]"
                      >
                        {formatTime(entry.at)}　{entry.viewer_name} 檢視了
                        {entry.fields.join("、")}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </section>
          )}

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
              {detail.available_actions.map((action) =>
                DESTRUCTIVE_ACTIONS.includes(action) ? (
                  <button
                    key={action}
                    type="button"
                    onClick={() => setConfirmingReject(true)}
                    disabled={acting !== null}
                    className="flex-1 rounded-2xl border-2 border-[var(--color-border)] bg-[var(--color-surface)] px-6 py-4 text-lg font-bold text-[var(--color-muted-foreground)] transition hover:border-danger hover:text-danger disabled:opacity-50"
                  >
                    {acting === action ? "處理中…" : ACTION_LABELS[action]}
                  </button>
                ) : (
                  <button
                    key={action}
                    type="button"
                    onClick={() => runAction(action)}
                    disabled={acting !== null}
                    className="flex-1 rounded-2xl bg-brand px-6 py-4 text-lg font-black text-white shadow-sm transition hover:brightness-105 disabled:opacity-50"
                  >
                    {acting === action ? "處理中…" : ACTION_LABELS[action]}
                  </button>
                ),
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
