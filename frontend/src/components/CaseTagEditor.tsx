import { useState } from "react";
import { ApiError } from "../api/client";
import { saveVendorCaseTags } from "../api/vendorTags";
import {
  CASE_TAG_PRESETS,
  MAX_CASE_TAGS,
  MAX_CASE_TAG_LENGTH,
  caseTagTone,
} from "../data/caseTags";

interface Props {
  requestId: string;
  tags: string[];
  /** 存檔成功後把後端回傳的標籤交還給呼叫端；畫面上的標籤一律以這份為準。 */
  onTagsChange: (tags: string[]) => void;
}

/**
 * 案件標籤編輯器（P1 V5）：常用標籤一鍵貼上，另外可以自己打。
 *
 * 每次增刪都直接送出整份清單並存檔——標籤是隨手貼的註記，多一個「儲存」按鈕只會
 * 讓人貼完就走、下次回來發現沒存到。存檔失敗時畫面不會自己改樣子：這裡不做樂觀
 * 更新，標籤一律等後端回傳的版本，看到的就是存進去的。
 */
export function CaseTagEditor({ requestId, tags, onTagsChange }: Props) {
  const [input, setInput] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const commit = (next: string[]) => {
    if (saving) return;
    setSaving(true);
    setError("");
    saveVendorCaseTags(requestId, next)
      .then((result) => {
        onTagsChange(result.tags);
        setInput("");
      })
      .catch((e) => setError(e instanceof ApiError ? e.message : "標籤沒有存成功，請稍後再試"))
      .finally(() => setSaving(false));
  };

  const addTag = (raw: string) => {
    const tag = raw.trim();
    if (!tag) {
      setError("請先輸入標籤文字。");
      return;
    }
    if (tag.length > MAX_CASE_TAG_LENGTH) {
      setError(`標籤最多 ${MAX_CASE_TAG_LENGTH} 個字。`);
      return;
    }
    if (tags.includes(tag)) {
      setError(`「${tag}」已經貼上了。`);
      return;
    }
    if (tags.length >= MAX_CASE_TAGS) {
      setError(`一張單最多只能貼 ${MAX_CASE_TAGS} 個標籤，先移掉一個再貼。`);
      return;
    }
    commit([...tags, tag]);
  };

  // 已經貼上的預設標籤不再出現在快捷區，避免按下去只換來一句「已經貼上了」。
  const quickPicks = CASE_TAG_PRESETS.filter((preset) => !tags.includes(preset));

  return (
    <section className="mt-5 rounded-[28px] bg-[var(--color-surface)] p-6 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-black text-[var(--color-foreground)]">案件標籤</h2>
        {saving && <span className="text-sm text-[var(--color-muted-foreground)]">儲存中…</span>}
      </div>
      <p className="mt-1 text-sm text-[var(--color-muted-foreground)]">
        只有你們公司看得到，住戶端不會顯示。
      </p>

      <div role="group" aria-label="已貼上的標籤" className="mt-4 flex flex-wrap gap-2">
        {tags.map((tag) => (
          <span
            key={tag}
            className={`inline-flex min-h-[44px] items-center gap-1 rounded-full py-1 pl-4 pr-1 text-base font-bold ${caseTagTone(tag)}`}
          >
            {tag}
            <button
              type="button"
              onClick={() => commit(tags.filter((t) => t !== tag))}
              disabled={saving}
              aria-label={`移除標籤「${tag}」`}
              className="flex h-11 w-11 items-center justify-center rounded-full text-xl leading-none transition hover:bg-[var(--color-surface-glass)] disabled:opacity-50"
            >
              ×
            </button>
          </span>
        ))}
        {tags.length === 0 && (
          <p className="text-base text-[var(--color-muted-foreground)]">還沒有貼標籤。</p>
        )}
      </div>

      {quickPicks.length > 0 && (
        <div role="group" aria-label="常用標籤" className="mt-4 flex flex-wrap gap-2">
          {quickPicks.map((preset) => (
            <button
              key={preset}
              type="button"
              onClick={() => addTag(preset)}
              disabled={saving}
              className="min-h-[44px] rounded-full border-2 border-dashed border-[var(--color-border)] px-4 text-base font-bold text-[var(--color-muted-foreground)] transition hover:border-brand hover:text-brand disabled:opacity-50"
            >
              ＋ {preset}
            </button>
          ))}
        </div>
      )}

      <form
        className="mt-4 flex flex-wrap gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          addTag(input);
        }}
      >
        <input
          type="text"
          aria-label="自定義標籤"
          value={input}
          maxLength={MAX_CASE_TAG_LENGTH}
          onChange={(event) => {
            setInput(event.target.value);
            setError("");
          }}
          placeholder={`自定義標籤，最多 ${MAX_CASE_TAG_LENGTH} 個字`}
          className="min-h-[44px] flex-1 rounded-2xl border-2 border-[var(--color-border)] px-4 text-base text-[var(--color-foreground)] placeholder:text-[var(--color-muted-foreground)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]"
        />
        <button
          type="submit"
          disabled={saving}
          className="min-h-[44px] rounded-2xl bg-brand px-6 text-base font-black text-white shadow-sm transition hover:brightness-105 disabled:opacity-50"
        >
          新增標籤
        </button>
      </form>

      {error && (
        <p role="alert" className="mt-3 text-sm font-bold text-[var(--color-danger)]">
          {error}
        </p>
      )}
    </section>
  );
}
