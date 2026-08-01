import { useId } from "react";
import { ServiceIcon } from "./ServiceIcon";

export interface CategoryOption {
  id: string;
  label: string;
  count: number;
}

interface Props {
  searchValue: string;
  onSearchChange: (value: string) => void;
  searchLabel: string;
  searchPlaceholder: string;
  /** 分類 chip 群組的 aria-label，讓螢幕閱讀器與測試都能把這排按鈕跟頁面上其他按鈕區分開。 */
  categoryGroupLabel: string;
  categories: CategoryOption[];
  activeCategory: string;
  onCategoryChange: (id: string) => void;
}

/**
 * 搜尋框＋分類 chip 列，供「我的服務」與「廠商後台」共用同一套篩選互動。
 * 分類清單由呼叫端動態算出（僅列出目前資料中實際出現的分類），本元件只負責呈現與互動。
 */
export function SearchAndCategoryFilter({
  searchValue,
  onSearchChange,
  searchLabel,
  searchPlaceholder,
  categoryGroupLabel,
  categories,
  activeCategory,
  onCategoryChange,
}: Props) {
  const searchId = useId();

  return (
    <div className="flex flex-col gap-3">
      <div className="relative">
        <label htmlFor={searchId} className="sr-only">
          {searchLabel}
        </label>
        <span className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-[var(--color-muted-foreground)]">
          <ServiceIcon type="zoom" size={18} />
        </span>
        <input
          id={searchId}
          type="search"
          value={searchValue}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder={searchPlaceholder}
          className="min-h-[44px] w-full rounded-full border border-[var(--color-border)] bg-[var(--color-surface)] py-2.5 pl-11 pr-4 text-base text-[var(--color-foreground)] placeholder:text-[var(--color-muted-foreground)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]"
        />
      </div>

      {categories.length > 0 && (
        <div
          role="group"
          aria-label={categoryGroupLabel}
          className="-mx-5 flex gap-2 overflow-x-auto px-5 pb-1"
        >
          {categories.map((category) => {
            const isActive = category.id === activeCategory;
            return (
              <button
                key={category.id}
                type="button"
                onClick={() => onCategoryChange(category.id)}
                aria-pressed={isActive}
                className={`flex min-h-[44px] shrink-0 items-center gap-1.5 whitespace-nowrap rounded-full px-4 text-base font-bold transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)] ${
                  isActive
                    ? "bg-[var(--color-primary)] text-[var(--color-on-primary)]"
                    : "bg-[var(--color-surface)] text-[var(--color-muted-foreground)] hover:text-[var(--color-primary)]"
                }`}
              >
                {category.label}
                <span
                  className={`rounded-full px-2 py-0.5 text-sm ${
                    isActive
                      ? "bg-[var(--color-surface-glass)]"
                      : "bg-[var(--color-canvas)] text-[var(--color-muted-foreground)]"
                  }`}
                >
                  {category.count}
                </span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
