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
            className="inline-flex items-center gap-3 rounded-full bg-brand px-6 py-4 text-base font-black text-white shadow-[0_24px_60px_rgba(15,76,129,0.32)] transition hover:bg-brand-dark"
          >
            <span className="flex h-11 w-11 items-center justify-center rounded-full bg-white/14">
              <Mascot size={28} />
            </span>
            AI 管家
          </button>

          <button
            type="button"
            aria-label="開啟客服中心"
            title="客服中心"
            onClick={() => setSupportOpen(true)}
            className="absolute left-full top-1/2 ml-3 flex h-12 w-12 -translate-y-1/2 items-center justify-center rounded-full bg-white text-brand shadow-[0_18px_44px_rgba(15,76,129,0.18)] ring-1 ring-brand/12 transition hover:bg-brand-soft"
          >
            <ServiceIcon type="chat" size={18} />
          </button>
        </div>
      </div>

      {assistantOpen && (
        <div className="fixed inset-0 z-50 bg-black/68 backdrop-blur-[3px]">
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
        <div className="fixed inset-0 z-50 bg-slate-950/50 px-4 py-6 backdrop-blur-[2px] sm:px-6 sm:py-8">
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
