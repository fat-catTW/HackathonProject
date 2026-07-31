import { useEffect, useState } from "react";
import { SupportPanel } from "./SupportPanel";
import { ServiceIcon } from "./ServiceIcon";

interface SupportLauncherProps {
  currentPageId: string;
  requestId?: string;
  serviceName?: string;
}

/**
 * 右下角固定的 FAQ / 客服浮動按鈕與其抽屜遮罩。
 *
 * 配色引用語意色 Token（Requirement 6.6）：遮罩改用 `--color-scrim`（Light 50% / Dark 60%
 * 深色，落在足以隔離前景內容的區間，Requirement 16.7），取代原本固定的 slate-950/50。
 */
export function SupportLauncher({
  currentPageId,
  requestId,
  serviceName,
}: SupportLauncherProps) {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!open) return;

    const { body } = document;
    const previousOverflow = body.style.overflow;
    body.style.overflow = "hidden";
    return () => {
      body.style.overflow = previousOverflow;
    };
  }, [open]);

  return (
    <>
      <div className="fixed bottom-5 right-5 z-40 sm:bottom-6 sm:right-6">
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="flex items-center gap-3 rounded-full bg-[var(--color-primary)] px-5 py-4 text-sm font-black text-[var(--color-on-primary)] shadow-2xl transition hover:bg-[var(--color-primary-hover)]"
        >
          <span className="flex h-11 w-11 items-center justify-center rounded-full bg-[var(--color-primary-hover)]">
            <ServiceIcon type="chat" size={22} />
          </span>
          FAQ / 客服
        </button>
      </div>

      {open && (
        <div className="fixed inset-0 z-50 bg-[var(--color-scrim)] px-4 py-6 backdrop-blur-[2px] sm:px-6 sm:py-8">
          <button
            type="button"
            aria-label="關閉客服視窗"
            onClick={() => setOpen(false)}
            className="absolute inset-0"
          />
          <div className="relative flex h-full items-end justify-end">
            <SupportPanel
              currentPageId={currentPageId}
              requestId={requestId}
              serviceName={serviceName}
              onClose={() => setOpen(false)}
            />
          </div>
        </div>
      )}
    </>
  );
}
