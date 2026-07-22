import { useEffect, useMemo, useState } from "react";
import type { FormDraft, FormFieldSchema, FormSchema } from "../types/request";

const VALUE_LABELS: Record<string, string> = {
  MORNING: "上午",
  AFTERNOON: "下午",
  EVENING: "晚上",
  TOP_LOAD: "上掀式",
  FRONT_LOAD: "前開式",
};

interface Props {
  formSchema: FormSchema | null;
  formDraft: FormDraft | null;
  sending: boolean;
  onApply: (fields: Record<string, string | number | null>) => Promise<void>;
  onConfirm: () => Promise<void>;
}

function toFieldValue(value: string | number | null | undefined) {
  return value === null || value === undefined ? "" : String(value);
}

function normalizeFields(formSchema: FormSchema, formDraft: FormDraft) {
  return Object.fromEntries(
    formSchema.fields.map((field) => [field.id, toFieldValue(formDraft.fields[field.id])]),
  );
}

function renderPrettyValue(field: FormFieldSchema, value: string | number | null | undefined) {
  if (value === null || value === undefined || value === "") {
    return "尚未填寫";
  }
  if (field.type === "select") {
    return VALUE_LABELS[String(value)] ?? String(value);
  }
  if (field.type === "number" && typeof value === "number") {
    if (field.id === "hours") return `${value} 小時`;
    if (field.id === "quantity") return `${value} 台`;
  }
  return String(value);
}

function buildPayload(
  formSchema: FormSchema,
  draftFields: Record<string, string>,
): Record<string, string | number | null> {
  return Object.fromEntries(
    formSchema.fields.map((field) => {
      const raw = (draftFields[field.id] ?? "").trim();
      if (!raw) return [field.id, null];
      if (field.type === "number") return [field.id, Number(raw)];
      return [field.id, raw];
    }),
  );
}

export function FormSummary({ formSchema, formDraft, sending, onApply, onConfirm }: Props) {
  const [draftFields, setDraftFields] = useState<Record<string, string>>({});

  useEffect(() => {
    if (formSchema && formDraft) {
      setDraftFields(normalizeFields(formSchema, formDraft));
    } else {
      setDraftFields({});
    }
  }, [formSchema, formDraft]);

  const missingLabels = useMemo(() => {
    if (!formSchema || !formDraft) return [];
    return formSchema.fields
      .filter((field) => formDraft.missing_fields.includes(field.id))
      .map((field) => field.label);
  }, [formSchema, formDraft]);

  if (!formSchema || !formDraft) {
    return (
      <section className="rounded-[28px] border border-pine-soft bg-white/95 p-5 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-pine">Instant Form</p>
        <h2 className="mt-2 text-lg font-black text-ink">即時表單</h2>
        <p className="mt-2 text-sm leading-6 text-gray-500">
          先在左邊告訴我你要申請哪一種服務。選到服務後，右邊會立刻出現對應表單，你可以隨時查看、修改，或直接手動填寫。
        </p>
      </section>
    );
  }

  return (
    <section className="rounded-[28px] border border-pine-soft bg-white/95 p-5 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-pine">Instant Form</p>
          <h2 className="mt-2 text-lg font-black text-ink">{formSchema.service_name ?? "服務表單"}</h2>
        </div>
        <div className="rounded-full bg-sand px-3 py-1 text-xs font-semibold text-gray-600">
          {formDraft.request_id ? "已送出" : formDraft.ready_for_confirmation ? "待確認" : "填寫中"}
        </div>
      </div>

      <p className="mt-3 text-sm leading-6 text-gray-500">
        聊天內容會同步整理到這張表單。你也可以直接修改欄位，再按「更新表單」讓管家接著往下走。
      </p>

      <div className="mt-4 rounded-2xl bg-sand/70 p-4">
        <div className="space-y-3">
          {formSchema.fields.map((field) => (
            <div key={field.id} className="grid gap-2">
              <label className="flex items-center justify-between text-sm font-semibold text-ink">
                <span>{field.label}</span>
                {formDraft.active_field === field.id && (
                  <span className="rounded-full bg-white px-2 py-0.5 text-[11px] text-pine">目前欄位</span>
                )}
              </label>
              {field.type === "select" ? (
                <select
                  value={draftFields[field.id] ?? ""}
                  onChange={(event) =>
                    setDraftFields((current) => ({ ...current, [field.id]: event.target.value }))
                  }
                  className="rounded-2xl border border-pine-soft bg-white px-4 py-3 text-sm outline-none focus:border-pine"
                >
                  <option value="">請選擇</option>
                  {(field.options ?? []).map((option) => (
                    <option key={option} value={option}>
                      {VALUE_LABELS[option] ?? option}
                    </option>
                  ))}
                </select>
              ) : field.type === "date" ? (
                <input
                  type="date"
                  value={draftFields[field.id] ?? ""}
                  min="2026-07-22"
                  onChange={(event) =>
                    setDraftFields((current) => ({ ...current, [field.id]: event.target.value }))
                  }
                  className="rounded-2xl border border-pine-soft bg-white px-4 py-3 text-sm outline-none focus:border-pine"
                />
              ) : field.type === "number" ? (
                <input
                  type="number"
                  min={1}
                  value={draftFields[field.id] ?? ""}
                  onChange={(event) =>
                    setDraftFields((current) => ({ ...current, [field.id]: event.target.value }))
                  }
                  className="rounded-2xl border border-pine-soft bg-white px-4 py-3 text-sm outline-none focus:border-pine"
                />
              ) : field.id === "issue_description" ? (
                <textarea
                  rows={3}
                  value={draftFields[field.id] ?? ""}
                  onChange={(event) =>
                    setDraftFields((current) => ({ ...current, [field.id]: event.target.value }))
                  }
                  className="rounded-2xl border border-pine-soft bg-white px-4 py-3 text-sm outline-none focus:border-pine"
                />
              ) : (
                <input
                  type="text"
                  value={draftFields[field.id] ?? ""}
                  onChange={(event) =>
                    setDraftFields((current) => ({ ...current, [field.id]: event.target.value }))
                  }
                  className="rounded-2xl border border-pine-soft bg-white px-4 py-3 text-sm outline-none focus:border-pine"
                />
              )}
              <p className="text-xs text-gray-500">
                目前內容：{renderPrettyValue(field, formDraft.fields[field.id])}
              </p>
            </div>
          ))}
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-3">
        <button
          type="button"
          disabled={sending || Boolean(formDraft.request_id)}
          onClick={() => onApply(buildPayload(formSchema, draftFields))}
          className="rounded-2xl bg-pine px-4 py-3 text-sm font-bold text-white disabled:opacity-50"
        >
          更新表單
        </button>
        <button
          type="button"
          disabled={sending || !formDraft.ready_for_confirmation || Boolean(formDraft.request_id)}
          onClick={() => void onConfirm()}
          className="rounded-2xl border border-pine px-4 py-3 text-sm font-bold text-pine disabled:opacity-40"
        >
          確認送出
        </button>
      </div>

      <div className="mt-4 grid gap-2 text-sm text-gray-600">
        {missingLabels.length > 0 ? (
          <p>還缺這些欄位：{missingLabels.join("、")}</p>
        ) : (
          <p>欄位已填完整，可以直接按「確認送出」。</p>
        )}
        {formDraft.request_id && <p>案件編號：{formDraft.request_id}</p>}
      </div>
    </section>
  );
}
