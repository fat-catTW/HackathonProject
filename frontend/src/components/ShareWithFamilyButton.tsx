import { useState } from "react";
import { ServiceIcon } from "./ServiceIcon";
import { Toast } from "./Toast";

interface Props {
  text: string;
}

export function ShareWithFamilyButton({ text }: Props) {
  const [toastText, setToastText] = useState<string | null>(null);

  async function handleShare() {
    if (typeof navigator.share === "function") {
      try {
        await navigator.share({ title: "AI 管家任務完成通知", text });
      } catch {
        // 使用者取消分享選單不是錯誤，不用顯示任何提示。
      }
      return;
    }

    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      setToastText("已複製訊息，請貼到 LINE 傳給家人");
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={() => void handleShare()}
        className="mt-3 inline-flex min-h-[44px] w-full items-center justify-center gap-2 rounded-2xl bg-[var(--color-primary)] px-4 py-2.5 text-base font-bold text-[var(--color-on-primary)]"
      >
        <ServiceIcon type="chat" size={18} />
        分享給家人
      </button>
      <Toast text={toastText} onHide={() => setToastText(null)} />
    </>
  );
}
