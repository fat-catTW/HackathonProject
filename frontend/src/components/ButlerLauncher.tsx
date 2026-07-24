import { useEffect, useState } from "react";
import { ButlerPanel } from "./ButlerPanel";
import { Mascot } from "./Mascot";

interface ButlerLauncherProps {
  currentPageId: string;
  autoMessage?: string;
}

export function ButlerLauncher({ currentPageId, autoMessage }: ButlerLauncherProps) {
  const [assistantOpen, setAssistantOpen] = useState(false);

  useEffect(() => {
    if (!assistantOpen) return;

    const { body } = document;
    const previousOverflow = body.style.overflow;
    body.style.overflow = "hidden";
    return () => {
      body.style.overflow = previousOverflow;
    };
  }, [assistantOpen]);

  return (
    <>
      <div className="pointer-events-none fixed inset-x-0 bottom-6 z-40 flex justify-center px-5">
        <button
          type="button"
          onClick={() => setAssistantOpen(true)}
          className="pointer-events-auto inline-flex items-center gap-3 rounded-full bg-brand px-6 py-4 text-base font-black text-white shadow-[0_24px_60px_rgba(15,76,129,0.32)] transition hover:bg-brand-dark"
        >
          <span className="flex h-11 w-11 items-center justify-center rounded-full bg-white/14">
            <Mascot size={28} />
          </span>
          啟動 AI 管家
        </button>
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
    </>
  );
}
