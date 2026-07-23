import { useEffect, useRef } from "react";

interface Props {
  text: string | null;
  onHide: () => void;
  durationMs?: number;
}

/** 畫面下方置中的短暫提示訊息，經過 durationMs 後自動呼叫 onHide。 */
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
    <div className="fixed bottom-7 left-1/2 z-[60] -translate-x-1/2 rounded-full bg-brand-dark px-6 py-3.5 text-sm font-semibold text-white shadow-lg">
      {text}
    </div>
  );
}
