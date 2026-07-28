import { useEffect, useRef, useState } from "react";
import { useTheme } from "../hooks/useTheme";
import { Mascot } from "./Mascot";

/** 點左上角管家頭像才展開的主題色選單，平常不佔版面。 */
export function ThemeMenu() {
  const { themeId, themes, setTheme } = useTheme();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onPointerDown(e: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    }
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="true"
        aria-expanded={open}
        aria-label="更換管家顏色"
        className="flex h-14 w-14 items-center justify-center rounded-2xl bg-white shadow-sm transition hover:shadow-md focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand"
      >
        <Mascot size={36} />
      </button>

      {open && (
        <div
          role="menu"
          aria-label="選擇管家的顏色"
          className="absolute left-0 top-[calc(100%+8px)] z-30 w-[272px] rounded-[24px] border border-gray-100 bg-white p-4 shadow-xl"
        >
          <p className="mb-3 text-sm font-bold text-slate-500">選擇管家的顏色</p>
          <div className="grid grid-cols-3 gap-3">
            {themes.map((t) => {
              const active = t.id === themeId;
              return (
                <button
                  key={t.id}
                  type="button"
                  role="menuitemradio"
                  aria-checked={active}
                  aria-label={`切換為${t.name}主題`}
                  onClick={() => {
                    setTheme(t.id);
                    setOpen(false);
                  }}
                  className={`flex flex-col items-center gap-1.5 rounded-2xl border-2 p-2 transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand ${
                    active ? "border-brand bg-brand-soft" : "border-transparent hover:border-gray-200"
                  }`}
                >
                  <span
                    className="flex h-12 w-12 items-center justify-center rounded-2xl"
                    style={{ backgroundColor: t.brandSoft }}
                  >
                    <Mascot size={30} bodyColor={t.brand} highlightColor={t.mascotHighlight} />
                  </span>
                  <span className="text-xs font-bold text-slate-600">{t.name}</span>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
