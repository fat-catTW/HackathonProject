import { useEffect, useState } from "react";
import { SupportPanel } from "./SupportPanel";
import { ServiceIcon } from "./ServiceIcon";

interface SupportLauncherProps {
  currentPageId: string;
  requestId?: string;
  serviceName?: string;
}

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
          className="flex items-center gap-3 rounded-full bg-brand px-5 py-4 text-sm font-black text-white shadow-[0_22px_60px_rgba(15,76,129,0.32)] transition hover:bg-brand-dark"
        >
          <span className="flex h-11 w-11 items-center justify-center rounded-full bg-white/14">
            <ServiceIcon type="chat" size={22} />
          </span>
          FAQ / 客服
        </button>
      </div>

      {open && (
        <div className="fixed inset-0 z-50 bg-slate-950/50 px-4 py-6 backdrop-blur-[2px] sm:px-6 sm:py-8">
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
