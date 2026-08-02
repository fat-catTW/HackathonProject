import { describe, expect, it } from "vitest";
import { CASE_TAG_PRESETS, caseTagTone } from "./caseTags";

describe("caseTagTone", () => {
  it("給三個常用標籤固定的語意色", () => {
    expect(caseTagTone("急件")).toContain("--color-danger");
    expect(caseTagTone("大型案件")).toContain("--color-info");
    expect(caseTagTone("待報價")).toContain("--color-warning");
  });

  it("同一個自訂標籤永遠是同一個顏色", () => {
    expect(caseTagTone("要帶梯子")).toBe(caseTagTone("要帶梯子"));
  });

  it("不同的自訂標籤不會全部撞成同一色", () => {
    const tones = new Set(["要帶梯子", "二樓", "熟客", "先收訂"].map(caseTagTone));
    expect(tones.size).toBeGreaterThan(1);
  });

  it("自訂標籤不會染成紅或黃——那兩個顏色在這個後台已經有意思了", () => {
    for (const tag of ["要帶梯子", "二樓", "熟客", "先收訂", "老屋", "需開發票", "回頭客"]) {
      expect(caseTagTone(tag)).not.toContain("--color-danger");
      expect(caseTagTone(tag)).not.toContain("--color-warning");
    }
  });

  it("每個預設標籤都拿得到顏色，沒有漏掉的", () => {
    for (const preset of CASE_TAG_PRESETS) {
      expect(caseTagTone(preset)).toMatch(/^bg-\[var\(--color-/);
    }
  });
});
