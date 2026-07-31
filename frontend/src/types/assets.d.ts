/**
 * 圖片素材的模組型別宣告。
 *
 * Vite 會把這類 import 轉成帶 hash 的 URL 字串，但本專案的 tsconfig 沒有納入
 * `vite/client` 型別（若改用 `types: ["vite/client"]` 會連帶排除 @types/node 與
 * vitest 的全域型別），因此在這裡補上最小必要的宣告。
 *
 * 以 import 方式引用而非放在 `public/`，好處是素材檔案若被刪除或改名，
 * 建置階段就會失敗，而不是等到執行時才 404。
 */
declare module "*.jpg" {
  const src: string;
  export default src;
}

declare module "*.jpeg" {
  const src: string;
  export default src;
}

declare module "*.png" {
  const src: string;
  export default src;
}

declare module "*.webp" {
  const src: string;
  export default src;
}

declare module "*.svg" {
  const src: string;
  export default src;
}
