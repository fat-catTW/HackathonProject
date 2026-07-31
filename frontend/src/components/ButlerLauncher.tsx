import { useEffect, useState } from "react";
import { ButlerPanel } from "./ButlerPanel";
import { Mascot } from "./Mascot";
import { ServiceIcon } from "./ServiceIcon";
import { SupportPanel } from "./SupportPanel";

interface ButlerLauncherProps {
  currentPageId: string;
  autoMessage?: string;
  requestId?: string;
  serviceName?: string;
}

export function ButlerLauncher({
  currentPageId,
  autoMessage,
  requestId,
  serviceName,
}: ButlerLauncherProps) {
  const [assistantOpen, setAssistantOpen] = useState(false);
  const [supportOpen, setSupportOpen] = useState(false);

  useEffect(() => {
    if (!assistantOpen && !supportOpen) return;

    const { body } = document;
    const previousOverflow = body.style.overflow;
    body.style.overflow = "hidden";
    return () => {
      body.style.overflow = previousOverflow;
    };
  }, [assistantOpen, supportOpen]);

  return (
    <>
      <div className="pointer-events-none fixed inset-x-0 bottom-6 z-40 flex justify-center px-5">
        <div className="pointer-events-auto relative">
          <button
            type="button"
            onClick={() => setAssistantOpen(true)}
            className="bg-brand-gradient inline-flex items-center gap-3 rounded-full px-6 py-4 text-base font-black text-[var(--color-on-primary)] shadow-[0_24px_60px_-18px_var(--color-primary)] transition hover:opacity-90"
          >
            <span className="flex h-11 w-11 items-center justify-center rounded-full bg-[var(--color-surface-glass)]">
              {/* 漂浮按鈕底為品牌漸層，Mascot 用 inverted 白色系維持對比 */}
              <Mascot size={28} tone="inverted" />
            </span>
            AI 管家
          </button>

          <button
            type="button"
            aria-label="開啟客服中心"
            title="客服中心"
            onClick={() => setSupportOpen(true)}
            className="absolute left-full top-1/2 ml-3 flex h-12 w-12 -translate-y-1/2 items-center justify-center rounded-full bg-[var(--color-surface)] text-[var(--color-primary)] shadow-lg ring-1 ring-[var(--color-border)] transition hover:bg-[var(--color-primary-soft)]"
          >
            <ServiceIcon type="chat" size={18} />
          </button>
        </div>
      </div>

      {assistantOpen && (
        // 遮罩改用 --color-scrim（兩模式各 50% / 60% 深色，Requirement 16.7）
        <div className="fixed inset-0 z-50 bg-[var(--color-scrim)] backdrop-blur-[3px]">
          <button
            type="button"
            aria-label="關閉 AI 管家"
            onClick={() => setAssistantOpen(false)}
            className="absolute inset-0"
          />
          <div className="relative flex min-h-dvh justify-center">
            <ButlerPanel
              overlay
              autoMessage={autoMessage}
              currentPageId={currentPageId}
              onClose={() => setAssistantOpen(false)}
            />
          </div>
        </div>
      )}

      {supportOpen && (
        <div className="fixed inset-0 z-50 bg-[var(--color-scrim)] px-4 py-6 backdrop-blur-[2px] sm:px-6 sm:py-8">
          <button
            type="button"
            aria-label="關閉客服視窗"
            onClick={() => setSupportOpen(false)}
            className="absolute inset-0"
          />
          <div className="relative flex h-full items-end justify-end">
            <SupportPanel
              currentPageId={currentPageId}
              requestId={requestId}
              serviceName={serviceName}
              onClose={() => setSupportOpen(false)}
            />
          </div>
        </div>
      )}
    </>
  );
}
