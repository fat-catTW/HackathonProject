import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ApiError } from "../api/client";
import { createServiceRequest } from "../api/services";
import { ButlerLauncher } from "../components/ButlerLauncher";
import { ServiceIcon } from "../components/ServiceIcon";
import { Toast } from "../components/Toast";
import { getServiceDefinition } from "../data/services";
import type { ServiceField } from "../types/service";
import { fieldValueLabel } from "../utils/fieldLabels";

type FormValues = Record<string, string>;

function minDateIso() {
  const now = new Date();
  const local = new Date(now.getTime() - now.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 10);
}

function buildInitialValues(fields: ServiceField[]) {
  return Object.fromEntries(fields.map((field) => [field.id, ""]));
}

function groupFields(fields: ServiceField[]) {
  const groups = new Map<string, ServiceField[]>();
  for (const field of fields) {
    const title = field.sectionTitle ?? "基本資訊";
    const existing = groups.get(title) ?? [];
    existing.push(field);
    groups.set(title, existing);
  }

  return Array.from(groups.entries()).map(([title, groupFields]) => ({
    title,
    fields: groupFields,
  }));
}

export function ServiceFormPage() {
  const { serviceId = "" } = useParams();
  const navigate = useNavigate();
  const schema = useMemo(() => getServiceDefinition(serviceId), [serviceId]);
  const [values, setValues] = useState<FormValues>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [toastText, setToastText] = useState<string | null>(null);
  const [createdRequestId, setCreatedRequestId] = useState<string | null>(null);

  useEffect(() => {
    setValues(buildInitialValues(schema?.fields ?? []));
    setErrors({});
    setCreatedRequestId(null);
    setToastText(null);
  }, [schema]);

  useEffect(() => {
    if (!createdRequestId) return;
    const timer = setTimeout(() => navigate(`/requests/${createdRequestId}`), 1200);
    return () => clearTimeout(timer);
  }, [createdRequestId, navigate]);

  const groupedFields = useMemo(() => groupFields(schema?.fields ?? []), [schema]);
  const completedCount = useMemo(
    () =>
      (schema?.fields ?? []).filter((field) => {
        const value = (values[field.id] ?? "").trim();
        return value !== "";
      }).length,
    [schema, values],
  );

  function updateValue(fieldId: string, value: string) {
    setValues((prev) => ({ ...prev, [fieldId]: value }));
    setErrors((prev) => {
      if (!prev[fieldId]) return prev;
      const next = { ...prev };
      delete next[fieldId];
      return next;
    });
  }

  function validate() {
    if (!schema) return false;

    const nextErrors: Record<string, string> = {};
    for (const field of schema.fields) {
      const rawValue = (values[field.id] ?? "").trim();
      if (field.required && !rawValue) {
        nextErrors[field.id] = `請填寫${field.label}`;
        continue;
      }

      if (field.type === "number" && rawValue) {
        const parsed = Number(rawValue);
        if (!Number.isFinite(parsed) || parsed <= 0) {
          nextErrors[field.id] = `${field.label}需為大於 0 的數字`;
        }
      }
    }

    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  }

  async function handleSubmit() {
    if (!schema || submitting) return;
    if (!validate()) return;

    const payload: Record<string, string | number> = {};
    for (const field of schema.fields) {
      const rawValue = (values[field.id] ?? "").trim();
      if (!rawValue) continue;
      payload[field.id] = field.type === "number" ? Number(rawValue) : rawValue;
    }

    setSubmitting(true);
    try {
      const result = await createServiceRequest(schema.service_id, payload);
      setCreatedRequestId(result.request_id);
    } catch (error) {
      setToastText(error instanceof ApiError ? error.message : "送出失敗，請稍後再試");
    } finally {
      setSubmitting(false);
    }
  }

  function renderField(field: ServiceField) {
    const value = values[field.id] ?? "";
    const error = errors[field.id];

    return (
      <label
        key={field.id}
        className="block rounded-[24px] border border-slate-100 bg-slate-50/80 p-4"
      >
        <div className="flex items-start gap-3">
          <span className="mt-0.5 flex h-11 w-11 items-center justify-center rounded-2xl bg-white text-brand shadow-sm">
            <ServiceIcon type={field.inputIcon ?? "info"} size={20} />
          </span>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span className="text-base font-black text-slate-900">{field.label}</span>
              {field.required && (
                <span className="rounded-full bg-brand-soft px-2 py-0.5 text-[11px] font-bold text-brand">
                  必填
                </span>
              )}
            </div>
            {field.hint && <p className="mt-1 text-sm leading-6 text-slate-500">{field.hint}</p>}

            <div className="mt-3">
              {field.type === "select" ? (
                <select
                  value={value}
                  onChange={(e) => updateValue(field.id, e.target.value)}
                  className="w-full rounded-2xl border-2 border-white bg-white px-4 py-3.5 text-slate-900 outline-none transition focus:border-brand"
                >
                  <option value="">請選擇</option>
                  {(field.options ?? []).map((option) => (
                    <option key={option} value={option}>
                      {fieldValueLabel(option)}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  type={
                    field.type === "number"
                      ? "number"
                      : field.type === "date"
                        ? "date"
                        : "text"
                  }
                  min={field.type === "date" ? minDateIso() : undefined}
                  value={value}
                  onChange={(e) => updateValue(field.id, e.target.value)}
                  placeholder={
                    field.type === "text" || field.type === "number"
                      ? field.placeholder ?? `請填寫${field.label}`
                      : undefined
                  }
                  className="w-full rounded-2xl border-2 border-white bg-white px-4 py-3.5 text-slate-900 outline-none transition focus:border-brand"
                />
              )}
            </div>

            {error && <p className="mt-2 text-sm font-medium text-red-600">{error}</p>}
          </div>
        </div>
      </label>
    );
  }

  if (!schema) {
    return (
      <>
        <main className="mx-auto min-h-dvh max-w-md bg-canvas px-5 pb-32 pt-16 text-center">
          <p className="text-red-600">找不到這個服務表單。</p>
          <button
            type="button"
            onClick={() => navigate("/home")}
            className="mt-4 text-brand underline"
          >
            返回服務首頁
          </button>
        </main>
        <ButlerLauncher currentPageId="service_form" />
      </>
    );
  }

  return (
    <>
      <main className="mx-auto min-h-dvh max-w-md bg-[linear-gradient(180deg,var(--color-brand-soft)_0%,var(--color-canvas)_100%)] px-5 pb-32 pt-6">
        <header className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => navigate("/home")}
            className="flex h-11 w-11 items-center justify-center rounded-full bg-white text-gray-500 shadow-sm transition hover:text-brand"
          >
            <ServiceIcon type="back" size={20} />
          </button>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-brand">服務表單</p>
            <h1 className="truncate text-2xl font-black text-slate-900">{schema.title}</h1>
          </div>
        </header>

        <section className="mt-6 overflow-hidden rounded-[30px] bg-gradient-to-br from-brand to-brand-dark p-6 text-white shadow-[0_24px_60px_rgba(15,76,129,0.22)]">
          <div className="flex items-start gap-4">
            <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-white/12">
              <ServiceIcon type={schema.icon} size={30} />
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold tracking-wide text-white/75">到府服務需求</p>
              <h2 className="mt-1 text-2xl font-black">{schema.title}</h2>
              <p className="mt-3 text-sm leading-7 text-white/80">{schema.description}</p>
            </div>
          </div>

          <div className="mt-5 grid grid-cols-3 gap-3">
            <div className="rounded-2xl bg-white/10 px-3 py-3">
              <p className="text-[11px] font-semibold text-white/70">步驟 1</p>
              <p className="mt-1 text-sm font-bold">填寫需求</p>
            </div>
            <div className="rounded-2xl bg-white/10 px-3 py-3">
              <p className="text-[11px] font-semibold text-white/70">步驟 2</p>
              <p className="mt-1 text-sm font-bold">送出表單</p>
            </div>
            <div className="rounded-2xl bg-white/10 px-3 py-3">
              <p className="text-[11px] font-semibold text-white/70">步驟 3</p>
              <p className="mt-1 text-sm font-bold">等待確認</p>
            </div>
          </div>
        </section>

        <section className="mt-6 rounded-[28px] bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-sm font-semibold text-brand">填寫進度</p>
              <h2 className="mt-1 text-lg font-black text-slate-900">
                已完成 {completedCount} / {schema.fields.length} 項
              </h2>
            </div>
            <span className="rounded-full bg-brand-soft px-3 py-1 text-xs font-bold text-brand">
              本地表單
            </span>
          </div>
          <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-100">
            <div
              className="h-full rounded-full bg-brand transition-all"
              style={{ width: `${(completedCount / Math.max(schema.fields.length, 1)) * 100}%` }}
            />
          </div>
        </section>

        <section className="mt-6 space-y-5">
          {groupedFields.map((group) => (
            <div key={group.title} className="rounded-[28px] bg-white p-5 shadow-sm">
              <div className="mb-4">
                <p className="text-sm font-semibold text-brand">{group.title}</p>
                <h3 className="mt-1 text-lg font-black text-slate-900">請完成這一區資料</h3>
              </div>
              <div className="space-y-4">{group.fields.map(renderField)}</div>
            </div>
          ))}
        </section>

        <section className="mt-6 rounded-[28px] border border-white/80 bg-white/96 p-4 shadow-[0_24px_60px_rgba(30,41,59,0.14)]">
          <div className="mb-3">
            <p className="text-sm font-semibold text-brand">送出前提醒</p>
            <p className="mt-1 text-sm text-slate-500">
              缺漏欄位會在送出時提示，你也可以改用 AI 管家協助整理需求。
            </p>
          </div>
          <div className="flex flex-col gap-3">
            <button
              type="button"
              onClick={() => void handleSubmit()}
              disabled={submitting}
              className="w-full rounded-2xl bg-brand py-4 text-base font-bold text-white shadow-[0_16px_34px_rgba(15,76,129,0.22)] disabled:opacity-50"
            >
              {submitting ? "送出中..." : "送出服務需求"}
            </button>
            <button
              type="button"
              onClick={() => navigate("/home")}
              className="w-full rounded-2xl border-2 border-gray-200 bg-white py-4 text-base font-bold text-gray-500"
            >
              返回服務首頁
            </button>
          </div>
        </section>
      </main>

      {createdRequestId && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center bg-[rgba(8,15,30,0.55)] px-6 backdrop-blur-sm">
          <div className="w-full max-w-sm rounded-[32px] bg-white p-8 text-center shadow-[0_28px_80px_rgba(15,23,42,0.28)]">
            <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-brand shadow-[0_0_0_12px_rgba(234,241,252,0.9)]">
              <ServiceIcon type="check" size={34} className="text-white" />
            </div>
            <p className="mt-6 text-sm font-semibold uppercase tracking-[0.24em] text-brand">
              Success
            </p>
            <h2 className="mt-2 text-2xl font-black text-slate-900">需求已成功送出</h2>
            <p className="mt-3 text-sm leading-7 text-slate-500">
              我們正在為你建立案件，接下來會自動帶你前往服務詳情頁查看進度。
            </p>
          </div>
        </div>
      )}

      <Toast text={toastText} onHide={() => setToastText(null)} />
      <ButlerLauncher currentPageId="service_form" />
    </>
  );
}
