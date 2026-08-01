import { readFileSync, readdirSync, existsSync } from "node:fs";
import { join, resolve } from "node:path";
import { describe, expect, it } from "vitest";

/**
 * 靜態掃描測試（Task 12.1–12.3）。
 *
 * 這組測試不渲染任何元件，而是直接讀取原始碼字串做斷言，用來守住三類「不該退化」的規則：
 * 1. 視覺特效邊界：資料密集區塊不得套玻璃擬態或 backdrop-filter（Requirement 15.1–15.3）
 * 2. 無硬編碼色碼：元件與頁面一律引用語意色 Token（Requirement 6.6）
 * 3. 路由/頁面清單與 api 層規範：Route 定義與頁面檔案清單是活的允許清單，新增頁面時
 *    應同步更新這份清單；api 層則不得含有樣式或色彩相關字串（Requirement 17.1–17.3）
 */
const SRC = resolve(__dirname, "..");
const COMPONENTS = join(SRC, "components");
const PAGES = join(SRC, "pages");

/**
 * 讀檔並移除註解。
 *
 * 掃描的目標是「實際生效的樣式」，而註解常常會為了說明設計決策而提到被禁用的類別名稱
 * （例如「本卡片維持不透明，不套 .glass-panel」）。若不先移除註解，這些說明文字會造成
 * 假性失敗，也會反過來逼開發者不敢寫清楚註解。
 */
function read(path: string): string {
  return readFileSync(path, "utf8")
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/(^|[^:])\/\/.*$/gm, "$1");
}

/** 列出目錄下的實作檔（排除測試檔）。 */
function sourceFiles(dir: string): string[] {
  return readdirSync(dir)
    .filter((f) => /\.tsx?$/.test(f) && !/\.test\.tsx?$/.test(f))
    .sort();
}

describe("視覺特效邊界（Task 12.1）", () => {
  const OPAQUE_ONLY = [
    join(COMPONENTS, "RequestCard.tsx"),
    join(COMPONENTS, "RestaurantCard.tsx"),
    join(COMPONENTS, "RestaurantCardList.tsx"),
    join(COMPONENTS, "ChatMessage.tsx"),
    join(COMPONENTS, "FieldPanel.tsx"),
    join(PAGES, "VendorRequestsPage.tsx"),
    join(PAGES, "VendorRequestDetailPage.tsx"),
  ];

  it.each(OPAQUE_ONLY)("%s uses no glass 擬態 or backdrop-filter", (path) => {
    const source = read(path);

    expect(source).not.toMatch(/\bglass-panel\b/);
    expect(source).not.toMatch(/\bGlassPanel\b/);
    expect(source).not.toMatch(/backdrop-filter/);
    expect(source).not.toMatch(/\bbackdrop-blur\b/);
  });

  it("ServiceFormPage keeps its form field groups opaque, glass 僅用於覆蓋層以外的重點卡片", () => {
    const source = read(join(PAGES, "ServiceFormPage.tsx"));

    // 表單頁不套玻璃擬態；頂部服務資訊卡以品牌漸層強調即可（Requirement 15.1、15.2）
    expect(source).not.toMatch(/\bglass-panel\b/);
    expect(source).not.toMatch(/\bGlassPanel\b/);
    expect(source).toMatch(/bg-brand-gradient/);
  });

  it("多步驟流程頁只在最終確認摘要卡使用 GlassPanel（Requirement 13.6）", () => {
    for (const name of ["DeliveryFlowPage.tsx", "ShopFlowPage.tsx"]) {
      const source = read(join(PAGES, name));
      const usages = source.match(/<GlassPanel/g) ?? [];
      expect(usages.length).toBe(1);
    }
  });

  it("VendorRequestsPage 只在標題區使用極淡漸層色帶（Requirement 14.1）", () => {
    const source = read(join(PAGES, "VendorRequestsPage.tsx"));

    expect(source).toMatch(/bg-brand-gradient-soft/);
    // 不得使用強度較高的實心品牌漸層
    expect(source).not.toMatch(/bg-brand-gradient(?!-soft)/);
  });
});

describe("硬編碼色碼掃描（Task 12.2）", () => {
  /**
   * 允許清單：Mascot 的造型固定色。
   * - `inverted` / `muted` tone 是設計系統定義的固定色調，不隨色彩模式變動
   * - 眼白與腮紅屬造型本身的一部分（Requirement 8.7：造型固定，僅顏色隨模式變化）
   */
  const ALLOWLIST = new Set(["Mascot.tsx"]);
  const HEX = /#[0-9A-Fa-f]{3,8}\b/g;

  const targets = [
    ...sourceFiles(COMPONENTS).map((f) => ({ dir: "components", file: f, path: join(COMPONENTS, f) })),
    ...sourceFiles(PAGES).map((f) => ({ dir: "pages", file: f, path: join(PAGES, f) })),
  ].filter((t) => !ALLOWLIST.has(t.file));

  it("covers every component and page file", () => {
    expect(targets.length).toBeGreaterThan(20);
  });

  it.each(targets.map((t) => [`${t.dir}/${t.file}`, t.path]))(
    "%s contains no hardcoded hex color",
    (_label, path) => {
      const matches = read(path as string).match(HEX) ?? [];
      expect(matches).toEqual([]);
    },
  );
});

describe("路由/頁面清單（Task 12.3）", () => {
  it("App.tsx 的 Route 定義符合目前的允許清單（Requirement 17.1）", () => {
    const source = read(join(SRC, "App.tsx"));

    /*
      這份清單會隨功能新增而更動——新增頁面/路由時要同步更新這裡，
      任何未同步更新的新增/刪除/改名才會讓本測試失敗。
      清單以 `<Route path="...">` 的字面值為準（幾個具名 /services/* 路徑各自導向專屬流程頁，
      並保留 /services/:serviceId 作為通用表單頁的 fallback，因此數量多於頁面檔案數）。
    */
    const EXPECTED_PATHS = [
      "/",
      "/login",
      "/home",
      "/calendar",
      "/my-services",
      "/services/restaurant_reservation",
      "/services/food_delivery",
      "/services/health_product_recommendation",
      "/services/clinic_appointment",
      "/services/shop_purchase",
      "/services/:serviceId",
      "/new",
      "/requests/:requestId",
      "/vendor",
      "/vendor/login",
      "/vendor/requests",
      "/vendor/requests/:requestId",
      "*",
    ];

    const actualPaths = [...source.matchAll(/<Route\s+path="([^"]+)"/g)].map((m) => m[1]);
    expect(actualPaths.sort()).toEqual([...EXPECTED_PATHS].sort());
  });

  it("api 層未被本次改版修改：不含任何樣式或色彩相關字串（Requirement 17.2）", () => {
    const apiDir = join(SRC, "api");
    for (const file of sourceFiles(apiDir)) {
      const source = read(join(apiDir, file));
      expect(source).not.toMatch(/className/);
      expect(source).not.toMatch(/--color-/);
      expect(source).not.toMatch(/#[0-9A-Fa-f]{6}\b/);
    }
  });

  it("頁面檔案清單符合目前的允許清單，新增頁面時應同步更新（Requirement 17.3）", () => {
    const EXPECTED_PAGES = [
      "CalendarPage.tsx",
      "ClinicConsultFlowPage.tsx",
      "DeliveryFlowPage.tsx",
      "HealthRecommendationPage.tsx",
      "HomePage.tsx",
      "LandingPage.tsx",
      "LoginPage.tsx",
      "MyServicesPage.tsx",
      "NewRequestPage.tsx",
      "RequestDetailPage.tsx",
      "ReservationFlowPage.tsx",
      "ServiceFormPage.tsx",
      "ShopFlowPage.tsx",
      "VendorLoginPage.tsx",
      "VendorRequestDetailPage.tsx",
      "VendorRequestsPage.tsx",
    ];

    expect(sourceFiles(PAGES)).toEqual(EXPECTED_PAGES);
  });

  it("舊主題機制的檔案已移除且無殘留引用（Requirements 3.1, 3.5）", () => {
    expect(existsSync(join(SRC, "hooks", "useTheme.ts"))).toBe(false);
    expect(existsSync(join(COMPONENTS, "ThemeMenu.tsx"))).toBe(false);

    for (const dir of [COMPONENTS, PAGES]) {
      for (const file of sourceFiles(dir)) {
        const source = read(join(dir, file));
        expect(source).not.toMatch(/useTheme|ThemeMenu|data-theme/);
      }
    }
  });
});
