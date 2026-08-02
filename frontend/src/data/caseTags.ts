/**
 * 廠商後台的案件標籤設定（P1 V5 案件分類與標籤）。
 *
 * 標籤本身是自由文字（後端只管長度、數量與去重），這裡的預設值只是「常用的三個」
 * 快捷鍵，讓多數情況一鍵貼完、不用每次打字；廠商想打「要帶梯子」照樣存得進去。
 */
export const CASE_TAG_PRESETS = ["急件", "大型案件", "待報價"] as const;

// 與 backend/app/services/case_tags.py 的 MAX_TAGS / MAX_TAG_LENGTH 對齊：前端先擋
// 一次，讓超量的人當場看到原因，而不是送出去被 400 退回來。
export const MAX_CASE_TAGS = 6;
export const MAX_CASE_TAG_LENGTH = 10;

/**
 * 三個常用標籤的語意色：急件是紅的、大型案件是藍的、待報價是黃的。
 *
 * 顏色只是加速掃視，標籤文字本身已經把意思說完了，因此不靠顏色單獨傳達資訊
 * （無障礙要求：不單以顏色區分狀態）。
 */
const PRESET_TONES: Record<string, string> = {
  急件: "bg-[var(--color-danger-soft)] text-[var(--color-danger)]",
  大型案件: "bg-[var(--color-info-soft)] text-[var(--color-info)]",
  待報價: "bg-[var(--color-warning-soft)] text-[var(--color-warning)]",
};

/**
 * 自訂標籤的配色盤。
 *
 * 刻意不含紅與黃：紅色在這個後台一路代表「急件／危險」，黃色代表「待處理」，
 * 讓「二樓」這種中性標籤染成紅的，等於用顏色說了一句沒人想說的話。剩下的四個
 * 色都是語意中性的品牌色，彼此夠遠、在深淺兩種主題下都有足夠對比。
 */
const CUSTOM_TONES = [
  "bg-[var(--color-success-soft)] text-[var(--color-success)]",
  "bg-[var(--color-tertiary-soft)] text-[var(--color-tertiary)]",
  "bg-[var(--color-secondary-soft)] text-[var(--color-secondary)]",
  "bg-[var(--color-primary-soft)] text-[var(--color-primary)]",
];

/** 標籤名稱 → 穩定的 32 bit 雜湊；同一個字永遠得到同一個數字。 */
function hashTag(tag: string): number {
  let hash = 0;
  for (let index = 0; index < tag.length; index += 1) {
    // `| 0` 把結果壓回 32 bit 整數，避免長標籤累積成失去精度的浮點數。
    hash = (hash * 31 + tag.charCodeAt(index)) | 0;
  }
  return Math.abs(hash);
}

/**
 * 標籤的顏色。預設標籤用固定的語意色，自訂標籤依名稱雜湊挑一個。
 *
 * 用雜湊而不是「貼上的順序」：顏色要跟著標籤本身走，同一個「要帶梯子」在清單、
 * 明細、不同案件上都得是同一色，否則顏色不但沒幫上忙，還會讓人以為是不同東西。
 * 代價是廠商不能指定「我就要綠色」——真的需要指定，再加一層每家廠商自己的色盤設定。
 */
export function caseTagTone(tag: string): string {
  return PRESET_TONES[tag] ?? CUSTOM_TONES[hashTag(tag) % CUSTOM_TONES.length];
}
