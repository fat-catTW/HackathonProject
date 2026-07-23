import { describe, expect, it } from "vitest";
import { buildFieldRows, fieldLabel, fieldValueLabel } from "./fieldLabels";

describe("fieldLabel", () => {
  it("translates known field keys", () => {
    expect(fieldLabel("quantity")).toBe("數量");
    expect(fieldLabel("address")).toBe("服務地址");
  });

  it("falls back to the raw key when unknown", () => {
    expect(fieldLabel("some_new_field")).toBe("some_new_field");
  });
});

describe("fieldValueLabel", () => {
  it("translates known enum values", () => {
    expect(fieldValueLabel("MORNING")).toBe("上午");
    expect(fieldValueLabel("FRONT_LOAD")).toBe("滾筒式");
  });

  it("stringifies unknown values as-is", () => {
    expect(fieldValueLabel(2)).toBe("2");
    expect(fieldValueLabel("台北市大安區")).toBe("台北市大安區");
  });
});

describe("buildFieldRows", () => {
  it("maps collected fields into labeled rows preserving insertion order", () => {
    const rows = buildFieldRows({ quantity: 2, preferred_time_slot: "AFTERNOON" });
    expect(rows).toEqual([
      { key: "quantity", label: "數量", value: "2" },
      { key: "preferred_time_slot", label: "希望時段", value: "下午" },
    ]);
  });

  it("returns an empty array for no collected fields", () => {
    expect(buildFieldRows({})).toEqual([]);
  });
});
