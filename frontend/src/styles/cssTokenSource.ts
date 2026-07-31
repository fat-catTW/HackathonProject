/**
 * `index.css` 原始碼靜態解析工具
 *
 * happy-dom 不會實際套用 Tailwind 編譯後的 stylesheet，Vitest 亦預設不處理 CSS 模組
 * （`?raw` 匯入會得到空字串），因此設計 Token 相關測試一律改由檔案系統讀取 `index.css`
 * 原始碼並靜態解析。此模組把解析邏輯集中一處，供 `designTokens.test.ts` 與
 * `contrast.test.ts` 共用，避免兩份測試各自維護一套解析器。
 */
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

export const LIGHT_SELECTOR = 'html[data-color-mode="light"]';
export const DARK_SELECTOR = 'html[data-color-mode="dark"]';

/** 直接自檔案系統讀取 index.css 原始碼（避開 Vite 的 CSS 轉換管線）。 */
const cssPath = resolve(dirname(fileURLToPath(import.meta.url)), "../index.css");
export const rawCss = readFileSync(cssPath, "utf-8");

/** 移除註解，避免註解文字干擾宣告解析。 */
export const css = rawCss.replace(/\/\*[\s\S]*?\*\//g, "");

function escapeForRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/** 取出某個選擇器（或 at-rule）第一個宣告區塊的內容，支援嵌套大括號。 */
export function extractBlock(source: string, selector: string): string {
  const opener = new RegExp(`${escapeForRegExp(selector)}\\s*\\{`);
  const match = opener.exec(source);
  if (!match) {
    throw new Error(`在 index.css 中找不到選擇器：${selector}`);
  }

  let depth = 1;
  const start = match.index + match[0].length;
  for (let i = start; i < source.length; i += 1) {
    const char = source[i];
    if (char === "{") depth += 1;
    else if (char === "}") {
      depth -= 1;
      if (depth === 0) return source.slice(start, i);
    }
  }
  throw new Error(`選擇器 ${selector} 的宣告區塊未正確閉合`);
}

/** 解析區塊內的 CSS 自訂屬性（僅取當層，忽略嵌套區塊）。 */
export function parseCustomProperties(block: string): Map<string, string> {
  const flat = block.replace(/\{[^{}]*\}/g, "");
  const result = new Map<string, string>();
  const pattern = /(--[\w-]+)\s*:\s*([^;]+);/g;
  let match: RegExpExecArray | null;
  while ((match = pattern.exec(flat)) !== null) {
    result.set(match[1], match[2].trim());
  }
  return result;
}

/** 解析區塊內的一般宣告（僅取當層）。 */
export function parseDeclarations(block: string): Map<string, string> {
  const flat = block.replace(/\{[^{}]*\}/g, "");
  const result = new Map<string, string>();
  for (const chunk of flat.split(";")) {
    const index = chunk.indexOf(":");
    if (index === -1) continue;
    const property = chunk.slice(0, index).trim();
    if (!property || property.startsWith("--") || !/^-?[a-zA-Z-]+$/.test(property)) continue;
    result.set(property, chunk.slice(index + 1).trim());
  }
  return result;
}

export const lightBlock = extractBlock(css, LIGHT_SELECTOR);
export const darkBlock = extractBlock(css, DARK_SELECTOR);
export const lightTokens = parseCustomProperties(lightBlock);
export const darkTokens = parseCustomProperties(darkBlock);
