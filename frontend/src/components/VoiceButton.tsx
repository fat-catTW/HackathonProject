interface Props {
  listening: boolean;
  supported: boolean;
  onStart: () => void;
  onStop: () => void;
  size?: "lg" | "md";
}

/**
 * 招牌元素：大型語音按鈕，聆聽時脈動。
 *
 * 配色改用語意色 Token（Requirement 6.6）：待機為 `--color-primary`、聆聽中為
 * `--color-danger`，文字/圖示一律用 `--color-on-primary`（Dark 模式為近黑，
 * 避免提亮後的填色配白字對比不足）。聆聽狀態除了顏色，另以 aria-label 文字與
 * 脈動動畫表達（Requirement 16.5）；脈動在 prefers-reduced-motion 下由
 * index.css 的全域規則停用（Requirement 15.5）。
 */
export function VoiceButton({ listening, supported, onStart, onStop, size = "md" }: Props) {
  if (!supported) return null;
  const dims = size === "lg" ? "h-24 w-24" : "h-14 w-14";
  return (
    <button
      type="button"
      aria-label={listening ? "停止聆聽" : "點擊並說出需求"}
      onClick={listening ? onStop : onStart}
      className={`relative inline-flex ${dims} items-center justify-center rounded-full text-[var(--color-on-primary)] shadow-lg transition focus-visible:outline focus-visible:outline-4 focus-visible:outline-[var(--color-primary-soft)] ${
        listening
          ? "bg-[var(--color-danger)]"
          : "bg-[var(--color-primary)] hover:bg-[var(--color-primary-hover)]"
      }`}
    >
      {listening && (
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[var(--color-danger)] opacity-60" />
      )}
      <svg
        viewBox="0 0 24 24"
        fill="currentColor"
        className={size === "lg" ? "h-10 w-10" : "h-6 w-6"}
        aria-hidden
      >
        <path d="M12 14a3 3 0 0 0 3-3V6a3 3 0 1 0-6 0v5a3 3 0 0 0 3 3Z" />
        <path d="M5 11a1 1 0 1 1 2 0 5 5 0 0 0 10 0 1 1 0 1 1 2 0 7 7 0 0 1-6 6.93V20h2a1 1 0 1 1 0 2H9a1 1 0 1 1 0-2h2v-2.07A7 7 0 0 1 5 11Z" />
      </svg>
    </button>
  );
}
