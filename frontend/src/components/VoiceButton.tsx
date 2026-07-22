interface Props {
  listening: boolean;
  supported: boolean;
  onStart: () => void;
  onStop: () => void;
  size?: "lg" | "md";
}

export function VoiceButton({ listening, supported, onStart, onStop, size = "md" }: Props) {
  if (!supported) return null;
  const dims = size === "lg" ? "h-24 w-24" : "h-14 w-14";
  return (
    <button
      type="button"
      aria-label={listening ? "停止錄音" : "開始語音輸入"}
      onClick={listening ? onStop : onStart}
      className={`relative inline-flex ${dims} items-center justify-center rounded-full text-white shadow-lg transition focus-visible:outline focus-visible:outline-4 focus-visible:outline-pine-soft ${
        listening ? "bg-red-500" : "bg-pine hover:bg-pine-dark"
      }`}
    >
      {listening && (
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-400 opacity-60" />
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
