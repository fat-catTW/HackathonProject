import { describe, expect, it } from "vitest";

import {
  DARK_SELECTOR,
  css,
  darkBlock,
  darkTokens,
  extractBlock,
  lightBlock,
  lightTokens,
  parseCustomProperties,
  parseDeclarations,
} from "./cssTokenSource";

/**
 * 設計 Token 靜態斷言測試
 *
 * 直接解析 `frontend/src/index.css` 原始碼，驗證 Light/Dark 兩組語意色彩 Token
 * 的結構完整性與關鍵色值。happy-dom 不會實際套用 Tailwind 編譯後的 stylesheet，
 * Vitest 亦預設不處理 CSS 模組（`?raw` 匯入會得到空字串），因此改由檔案系統讀取
 * 原始碼並靜態解析（解析工具集中於 `cssTokenSource.ts`），取代 computed style 檢查。
 *
 * _Requirements: 6.1, 6.2, 6.3, 6.4, 7.1, 9.5, 9.6, 10.1, 10.2, 10.3, 10.4, 10.5_
 */

const REQUIRED_COLOR_TOKENS = [
  // Brand
  "--color-primary",
  "--color-primary-hover",
  "--color-primary-accent",
  "--color-on-primary",
  "--color-primary-soft",
  // Surface
  "--color-background",
  "--color-canvas",
  "--color-surface",
  "--color-surface-glass",
  "--color-border",
  "--color-glass-border",
  // Text
  "--color-foreground",
  "--color-muted-foreground",
  // Semantic status
  "--color-success",
  "--color-success-soft",
  "--color-warning",
  "--color-warning-soft",
  "--color-danger",
  "--color-danger-soft",
  "--color-info",
  "--color-info-soft",
  // Mascot
  "--color-mascot-body",
  "--color-mascot-accent",
] as const;

describe("設計 Token：Light / Dark 色彩模式區塊", () => {
  it("兩個色彩模式區塊皆存在且各自定義變數", () => {
    expect(lightTokens.size).toBeGreaterThan(0);
    expect(darkTokens.size).toBeGreaterThan(0);
  });

  it("兩區塊的變數名稱集合完全相同", () => {
    const lightNames = [...lightTokens.keys()].sort();
    const darkNames = [...darkTokens.keys()].sort();
    expect(lightNames).toEqual(darkNames);
  });

  it.each(REQUIRED_COLOR_TOKENS)("必要變數 %s 於兩模式皆有非空值", (token) => {
    expect(lightTokens.get(token)).toBeTruthy();
    expect(darkTokens.get(token)).toBeTruthy();
  });

  it("Light 模式採用目前的品牌紫色系關鍵色值", () => {
    expect(lightTokens.get("--color-primary")?.toUpperCase()).toBe("#7C3AED");
    expect(lightTokens.get("--color-primary-accent")?.toUpperCase()).toBe("#A78BFA");
    expect(lightTokens.get("--color-background")?.toUpperCase()).toBe("#FAF8FE");
    expect(lightTokens.get("--color-mascot-body")?.toUpperCase()).toBe("#7C3AED");
    expect(lightTokens.get("--color-mascot-accent")?.toUpperCase()).toBe("#06B6D4");
  });

  it("Dark 模式採用目前的霓虹紫色系關鍵色值", () => {
    expect(darkTokens.get("--color-primary")?.toUpperCase()).toBe("#C084FC");
    expect(darkTokens.get("--color-primary-accent")?.toUpperCase()).toBe("#F472B6");
    expect(darkTokens.get("--color-background")?.toUpperCase()).toBe("#0B0714");
    expect(darkTokens.get("--color-on-primary")?.toUpperCase()).toBe("#1A0B2E");
    expect(darkTokens.get("--color-mascot-body")?.toUpperCase()).toBe("#C084FC");
    expect(darkTokens.get("--color-mascot-accent")?.toUpperCase()).toBe("#22D3EE");
  });

  it("兩區塊皆宣告對應的 color-scheme", () => {
    expect(parseDeclarations(lightBlock).get("color-scheme")).toBe("light");
    expect(parseDeclarations(darkBlock).get("color-scheme")).toBe("dark");
  });
});

describe("設計 Token：字型變數", () => {
  const rootTokens = parseCustomProperties(extractBlock(css, ":root"));

  it("定義 --font-display / --font-body / --font-mono", () => {
    expect(rootTokens.has("--font-display")).toBe(true);
    expect(rootTokens.has("--font-body")).toBe(true);
    expect(rootTokens.has("--font-mono")).toBe(true);
  });

  it("字族起首與 fallback 符合規範", () => {
    expect(rootTokens.get("--font-display")).toMatch(/^"Space Grotesk"/);
    expect(rootTokens.get("--font-display")).toContain("Noto Sans TC");
    expect(rootTokens.get("--font-body")).toMatch(/^"Noto Sans TC"/);
    expect(rootTokens.get("--font-mono")).toMatch(/^"JetBrains Mono"/);
  });
});

describe("設計 Token：.glass-panel 玻璃擬態", () => {
  const glassBlock = extractBlock(css, ".glass-panel");

  it("基礎樣式使用玻璃 Token 與模糊效果", () => {
    const declarations = parseDeclarations(glassBlock);
    expect(declarations.get("background")).toBe("var(--color-surface-glass)");
    expect(declarations.get("backdrop-filter")).toBe("blur(16px)");
    expect(declarations.get("border")).toContain("var(--color-glass-border)");
  });

  it("Dark 模式加強模糊強度與內側高光", () => {
    const darkGlass = parseDeclarations(extractBlock(css, `${DARK_SELECTOR} .glass-panel`));
    expect(darkGlass.get("backdrop-filter")).toBe("blur(20px)");
    expect(darkGlass.get("box-shadow")).toContain("inset");
  });

  it("提供 @supports fallback，退回不透明 --color-surface", () => {
    const supportsBlock = extractBlock(css, "@supports not (backdrop-filter: blur(1px))");
    expect(supportsBlock).toContain(".glass-panel");
    const fallback = parseDeclarations(extractBlock(supportsBlock, ".glass-panel"));
    expect(fallback.get("background")).toBe("var(--color-surface)");
  });
});

describe("設計 Token：品牌漸層工具類別", () => {
  const gradientBlock = extractBlock(css, ".bg-brand-gradient");
  const gradientDeclarations = parseDeclarations(gradientBlock);
  const darkGradient = parseDeclarations(
    extractBlock(css, `${DARK_SELECTOR} .bg-brand-gradient`),
  );

  it("漸層由 --color-primary 走向 --color-primary-accent", () => {
    const backgroundImage = gradientDeclarations.get("background-image") ?? "";
    expect(backgroundImage).toContain("linear-gradient");
    expect(backgroundImage).toContain("var(--color-primary)");
    expect(backgroundImage).toContain("var(--color-primary-accent)");
    expect(backgroundImage.indexOf("var(--color-primary)")).toBeLessThan(
      backgroundImage.indexOf("var(--color-primary-accent)"),
    );
  });

  it("Dark 模式沿用同一組品牌變數，並額外疊深色降飽和層與 vignette", () => {
    const backgroundImage = darkGradient.get("background-image") ?? "";
    // 底層仍是同一組品牌漸層，僅由上方圖層調整觀感
    expect(backgroundImage).toContain("var(--color-primary)");
    expect(backgroundImage).toContain("var(--color-primary-accent)");
    // vignette：以 radial-gradient 由中心向外加深
    expect(backgroundImage).toContain("radial-gradient");
    // 降飽和：至少疊一層深色（--color-background 的 rgba 形式）覆蓋層
    const overlayLayers = backgroundImage.match(/rgba\(11,\s*7,\s*20,/g) ?? [];
    expect(overlayLayers.length).toBeGreaterThan(1);
    // 圖層數量多於 Light 模式，代表確實有額外疊層
    const countLayers = (value: string) => (value.match(/-gradient\(/g) ?? []).length;
    expect(countLayers(backgroundImage)).toBeGreaterThan(
      countLayers(gradientDeclarations.get("background-image") ?? ""),
    );
  });

  it("極淡漸層色帶同樣提供 Light / Dark 兩組定義", () => {
    const soft = parseDeclarations(extractBlock(css, ".bg-brand-gradient-soft"));
    expect(soft.get("background-image")).toContain("var(--color-primary-soft)");
    const darkSoft = parseDeclarations(
      extractBlock(css, `${DARK_SELECTOR} .bg-brand-gradient-soft`),
    );
    expect(darkSoft.get("background-image")).toContain("var(--color-primary-soft)");
  });
});

describe("設計 Token：背景大字紋理", () => {
  const textureBlock = extractBlock(css, ".bg-wordmark-texture");
  const textureDeclarations = parseDeclarations(textureBlock);

  it("以純 CSS 產生旋轉紋理，不依賴圖片素材", () => {
    expect(textureDeclarations.get("transform")).toContain("rotate(");
    expect(textureBlock).not.toContain("url(");
  });

  it("不可互動且位於內容層之下", () => {
    expect(textureDeclarations.get("pointer-events")).toBe("none");
    expect(Number(textureDeclarations.get("z-index"))).toBeLessThan(0);
  });

  it("Light 約 0.05、Dark 約 0.08 不透明度", () => {
    expect(Number(textureDeclarations.get("opacity"))).toBeCloseTo(0.05, 3);
    const darkTexture = parseDeclarations(
      extractBlock(css, `${DARK_SELECTOR} .bg-wordmark-texture`),
    );
    expect(Number(darkTexture.get("opacity"))).toBeCloseTo(0.08, 3);
  });
});
