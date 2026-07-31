import { useEffect, useRef } from "react";

interface Props {
  text: string | null;
  onHide: () => void;
  durationMs?: number;
}

/**
 * 畫面下方置中的短暫提示訊息，經過 durationMs 後自動呼叫 onHide。
 *
 * 配色引用語意色 Token（Requirement 6.6），Light/Dark 共用同一份 className：
 * `--color-surface` 底 + `--color-border` 邊框讓膠囊在兩模式下都有明確邊界，
 * 文字用 `--color-foreground`（該配對已由 styles/contrast.test.ts 驗證達 AAA）。
 */
export function Toast({ text, onHide, durationMs = 3200 }: Props) {
  const onHideRef = useRef(onHide);
  onHideRef.current = onHide;

  useEffect(() => {
    if (!text) return;
    const timer = setTimeout(() => onHideRef.current(), durationMs);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [text, durationMs]);

  if (!text) return null;

  return (
    <div className="fixed bottom-7 left-1/2 z-[60] -translate-x-1/2 rounded-full border border-[var(--color-border)] bg-[var(--color-surface)] px-6 py-3.5 text-sm font-semibold text-[var(--color-foreground)] shadow-lg">
      {text}
    </div>
  );
}
