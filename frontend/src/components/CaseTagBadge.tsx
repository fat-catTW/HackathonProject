import { caseTagTone } from "../data/caseTags";

/**
 * 案件標籤的唯讀樣式，清單卡片與明細頁共用同一顆膠囊，讓同一個標籤在兩處長得一樣。
 * 顏色由 caseTagTone 決定，但意思一律由文字本身傳達，不單靠顏色。
 */
export function CaseTagBadge({ tag }: { tag: string }) {
  return (
    <span
      className={`inline-flex shrink-0 items-center rounded-full px-2.5 py-0.5 text-sm font-bold ${caseTagTone(tag)}`}
    >
      {tag}
    </span>
  );
}
