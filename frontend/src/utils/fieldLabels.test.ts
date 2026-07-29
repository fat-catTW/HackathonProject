import { describe, expect, it } from "vitest";
import { buildFieldRows, fieldLabel, fieldValueLabel, formatFieldValue } from "./fieldLabels";

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

  it("translates food_delivery field keys", () => {
    expect(fieldLabel("store_id")).toBe("店家");
    expect(fieldLabel("goods")).toBe("餐點");
    expect(fieldLabel("note")).toBe("備註需求");
  });

  it("formats a goods cart array as a readable list instead of stringifying it", () => {
    const rows = buildFieldRows({
      store_id: "store-001",
      goods: [
        { id: "item-001", title: "招牌雞腿便當", price: 110, quantity: 1 },
        { id: "item-010", title: "珍珠奶茶（大）", price: 65, quantity: 2 },
      ],
    });
    expect(rows).toEqual([
      { key: "store_id", label: "店家", value: "store-001" },
      { key: "goods", label: "餐點", value: "招牌雞腿便當 x1、珍珠奶茶（大） x2" },
    ]);
  });

  it("formats an empty goods cart as a dash rather than an empty string", () => {
    const rows = buildFieldRows({ goods: [] });
    expect(rows).toEqual([{ key: "goods", label: "餐點", value: "—" }]);
  });

  it("formats a food_delivery address object as one readable line, not [object Object]", () => {
    const rows = buildFieldRows({
      address: {
        lat: 25.033,
        lng: 121.565,
        city: "台北市",
        area: "大安區",
        street: "忠孝東路四段100號",
        remark: "8樓之2",
        contact_name: "王小明",
      },
    });
    expect(rows).toEqual([
      { key: "address", label: "服務地址", value: "台北市大安區忠孝東路四段100號（8樓之2）" },
    ]);
  });

  it("omits the remark parentheses when there is no remark", () => {
    const rows = buildFieldRows({
      address: { city: "台北市", area: "大安區", street: "忠孝東路四段100號", remark: "" },
    });
    expect(rows).toEqual([
      { key: "address", label: "服務地址", value: "台北市大安區忠孝東路四段100號" },
    ]);
  });
});

describe("formatFieldValue", () => {
  it("delegates to fieldValueLabel for plain string/number values", () => {
    expect(formatFieldValue("AFTERNOON")).toBe("下午");
    expect(formatFieldValue(3)).toBe("3");
  });
});
