import { describe, expect, it } from "vitest";

import { darkTokens, lightTokens } from "./cssTokenSource";
import {
  WCAG_AA_BODY_TEXT,
  WCAG_AA_LARGE_TEXT,
  compositeOver,
  contrastRatio,
  parseCssColor,
  type Rgba,
} from "./wcagContrast";

/**
 * 對比度計算測試
 *
 * 自 `frontend/src/index.css` 讀取 Light/Dark 兩模式的實際 Token 色值（不在測試中
 * 硬編色碼），對 design.md〈Data Models〉與〈Component Visual Contracts〉列出的
 * 前景／背景 Token 配對逐一計算 WCAG 2.1 對比比值：
 *
 * - 一般內文文字（含按鈕標籤、狀態徽章文字、玻璃面板內文字）：≥ 4.5:1
 * - 大型文字與圖示（品牌圖示、Mascot、狀態圖示）：≥ 3:1
 *
 * 半透明 Token（Dark 模式的 `--color-*-soft`、兩模式的 `--color-surface-glass`）
 * 無法單獨計算對比，一律先疊合到其實際所在的不透明底色上再計算；每個半透明色塊
 * 都對所有可能的底色（background / canvas / surface）各算一次，取全部斷言而非
 * 只算最佳情況。
 *
 * 刻意排除的配對（非「扁平 Token 對 Token」的文字情境，依 design.md〈Testing
 * Strategy〉的 Pre-Delivery Checklist 以人工視覺檢查驗證）：
 * - `.bg-brand-gradient` 漸層上的白字：實際背景是 `--color-primary` →
 *   `--color-primary-accent` 的連續漸層，非單一色值，無法以單點對比代表整塊區域。
 * - `--color-mascot-accent` 對 `--color-mascot-body`：Mascot SVG 內部的裝飾性高光
 *   （眼睛／天線），屬於插圖內部細節而非「理解內容所必需的圖形物件」，不適用 3:1。
 *
 * _Requirements: 16.1, 16.2_
 */

type Mode = "light" | "dark";

const TOKENS: Record<Mode, Map<string, string>> = {
  light: lightTokens,
  dark: darkTokens,
};

const MODES: readonly Mode[] = ["light", "dark"];

/** 所有可能承載卡片／色塊的不透明底色。 */
const OPAQUE_SURFACES = ["--color-background", "--color-canvas", "--color-surface"] as const;

function readToken(mode: Mode, token: string): string {
  const value = TOKENS[mode].get(token);
  if (!value) {
    throw new Error(`${mode} 模式缺少 Token：${token}`);
  }
  return value;
}

/**
 * 取得某 Token 在指定模式下實際呈現的不透明色。
 * `bases` 為由內而外的底色 Token 串鏈，供半透明 Token 逐層疊合。
 */
function resolveOpaque(mode: Mode, token: string, bases: readonly string[] = []): Rgba {
  const color = parseCssColor(readToken(mode, token));
  if (color.a === 1) return color;

  const [nextBase, ...rest] = bases;
  if (!nextBase) {
    throw new Error(`${mode} 模式的 ${token} 為半透明色，必須指定不透明底色`);
  }
  return compositeOver(color, resolveOpaque(mode, nextBase, rest));
}

interface PairingSpec {
  /** 人類可讀的情境描述 */
  readonly scenario: string;
  readonly foreground: string;
  /** 前景為半透明色時的底色串鏈（本專案目前的文字色皆不透明，保留通用性） */
  readonly foregroundOver?: readonly string[];
  readonly background: string;
  /** 背景為半透明色時的底色串鏈（由內而外） */
  readonly backgroundOver?: readonly string[];
}

interface PairingRow extends PairingSpec {
  readonly mode: Mode;
  readonly minimum: number;
}

/** 一般內文文字配對：門檻 4.5:1（Requirement 16.1）。 */
const BODY_TEXT_PAIRINGS: readonly PairingSpec[] = [
  // 主要／次要文字對三種不透明表面
  ...OPAQUE_SURFACES.flatMap((surface) => [
    {
      scenario: `主要文字 on ${surface}`,
      foreground: "--color-foreground",
      background: surface,
    },
    {
      scenario: `次要文字 on ${surface}`,
      foreground: "--color-muted-foreground",
      background: surface,
    },
  ]),
  // 主色按鈕標籤
  {
    scenario: "按鈕標籤 on 主色",
    foreground: "--color-on-primary",
    background: "--color-primary",
  },
  {
    scenario: "按鈕標籤 on 主色 hover",
    foreground: "--color-on-primary",
    background: "--color-primary-hover",
  },
  // 淡主色色塊上的內文（例如表單「必填」標籤所在色塊）
  ...OPAQUE_SURFACES.map((surface) => ({
    scenario: `主要文字 on 淡主色色塊（疊於 ${surface}）`,
    foreground: "--color-foreground",
    background: "--color-primary-soft",
    backgroundOver: [surface],
  })),
  // 玻璃面板內文字（design.md Pre-Delivery Checklist：兩模式皆須清晰可辨）
  ...(["--color-background", "--color-canvas"] as const).flatMap((surface) => [
    {
      scenario: `主要文字 on 玻璃面板（疊於 ${surface}）`,
      foreground: "--color-foreground",
      background: "--color-surface-glass",
      backgroundOver: [surface],
    },
    {
      scenario: `次要文字 on 玻璃面板（疊於 ${surface}）`,
      foreground: "--color-muted-foreground",
      background: "--color-surface-glass",
      backgroundOver: [surface],
    },
  ]),
  // 狀態徽章：soft 背景 + 同色相文字（StatusBadge 的「顏色＋文字」雙重表達）
  ...(
    [
      ["--color-success", "--color-success-soft"],
      ["--color-warning", "--color-warning-soft"],
      ["--color-danger", "--color-danger-soft"],
      ["--color-info", "--color-info-soft"],
    ] as const
  ).flatMap(([text, soft]) =>
    OPAQUE_SURFACES.map((surface) => ({
      scenario: `狀態徽章文字 ${text} on ${soft}（疊於 ${surface}）`,
      foreground: text,
      background: soft,
      backgroundOver: [surface],
    })),
  ),
];

/** 大型文字與圖示配對：門檻 3:1（Requirement 16.2）。 */
const LARGE_TEXT_AND_ICON_PAIRINGS: readonly PairingSpec[] = [
  ...OPAQUE_SURFACES.flatMap((surface) => [
    {
      scenario: `品牌色圖示／大字 on ${surface}`,
      foreground: "--color-primary",
      background: surface,
    },
    {
      scenario: `Mascot 主體 on ${surface}`,
      foreground: "--color-mascot-body",
      background: surface,
    },
    // 淡主色圖示底（bg-brand-soft + text-brand 的服務圖示膠囊）
    {
      scenario: `品牌色圖示 on 淡主色色塊（疊於 ${surface}）`,
      foreground: "--color-primary",
      background: "--color-primary-soft",
      backgroundOver: [surface],
    },
  ]),
  // 狀態色作為圖示／大字直接置於表面上
  ...(["--color-success", "--color-warning", "--color-danger", "--color-info"] as const).flatMap(
    (status) =>
      OPAQUE_SURFACES.map((surface) => ({
        scenario: `狀態圖示 ${status} on ${surface}`,
        foreground: status,
        background: surface,
      })),
  ),
];

function buildRows(pairings: readonly PairingSpec[], minimum: number): readonly PairingRow[] {
  return MODES.flatMap((mode) => pairings.map((pairing) => ({ ...pairing, mode, minimum })));
}

function ratioOf(row: PairingRow): number {
  const foreground = resolveOpaque(row.mode, row.foreground, row.foregroundOver ?? []);
  const background = resolveOpaque(row.mode, row.background, row.backgroundOver ?? []);
  return contrastRatio(foreground, background);
}

describe("WCAG 對比比值計算工具", () => {
  it("極端色對的比值符合 WCAG 定義", () => {
    expect(contrastRatio(parseCssColor("#FFFFFF"), parseCssColor("#000000"))).toBeCloseTo(21, 5);
    expect(contrastRatio(parseCssColor("#FFFFFF"), parseCssColor("#FFFFFF"))).toBeCloseTo(1, 5);
    // WebAIM 參考值：#767676 對白底為 4.54:1（AA 內文門檻的臨界色）
    expect(contrastRatio(parseCssColor("#767676"), parseCssColor("#FFFFFF"))).toBeCloseTo(4.54, 2);
  });

  it("半透明前景疊到底色後才計算對比", () => {
    const composited = compositeOver(parseCssColor("rgba(0, 0, 0, 0.5)"), parseCssColor("#FFFFFF"));
    expect(composited.r).toBeCloseTo(127.5, 5);
    expect(composited.a).toBe(1);
    expect(() => compositeOver(parseCssColor("#FFFFFF"), parseCssColor("rgba(0,0,0,0.5)"))).toThrow();
  });

  it("解析 hex 與 rgba 兩種 Token 寫法", () => {
    expect(parseCssColor("#2563EB")).toEqual({ r: 0x25, g: 0x63, b: 0xeb, a: 1 });
    expect(parseCssColor("rgba(59, 130, 246, 0.16)")).toEqual({ r: 59, g: 130, b: 246, a: 0.16 });
    expect(() => parseCssColor("not-a-color")).toThrow();
  });
});

describe("設計 Token 對比度：一般內文文字 ≥ 4.5:1", () => {
  const rows = buildRows(BODY_TEXT_PAIRINGS, WCAG_AA_BODY_TEXT);

  it("涵蓋 Light 與 Dark 兩模式的所有內文配對", () => {
    expect(rows.length).toBe(BODY_TEXT_PAIRINGS.length * MODES.length);
    expect(rows.some((row) => row.mode === "light")).toBe(true);
    expect(rows.some((row) => row.mode === "dark")).toBe(true);
  });

  it.each(rows)("[$mode] $scenario", (row) => {
    const ratio = ratioOf(row);
    expect(
      ratio,
      `[${row.mode}] ${row.scenario} 對比僅 ${ratio.toFixed(2)}:1，未達 ${row.minimum}:1`,
    ).toBeGreaterThanOrEqual(row.minimum);
  });
});

describe("設計 Token 對比度：大型文字與圖示 ≥ 3:1", () => {
  const rows = buildRows(LARGE_TEXT_AND_ICON_PAIRINGS, WCAG_AA_LARGE_TEXT);

  it("涵蓋 Light 與 Dark 兩模式的所有圖示配對", () => {
    expect(rows.length).toBe(LARGE_TEXT_AND_ICON_PAIRINGS.length * MODES.length);
  });

  it.each(rows)("[$mode] $scenario", (row) => {
    const ratio = ratioOf(row);
    expect(
      ratio,
      `[${row.mode}] ${row.scenario} 對比僅 ${ratio.toFixed(2)}:1，未達 ${row.minimum}:1`,
    ).toBeGreaterThanOrEqual(row.minimum);
  });
});
