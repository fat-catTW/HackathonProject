import { describe, expect, it } from "vitest";
import { buildFieldRows, fieldLabel, fieldValueLabel, formatFieldValue } from "./fieldLabels";

describe("fieldLabel", () => {
  it("translates known field keys", () => {
    expect(fieldLabel("quantity")).toBe("數量");
    expect(fieldLabel("cleaning_service_option")).toBe("服務方案");
    expect(fieldLabel("address")).toBe("地址");
    expect(fieldLabel("air_conditioner_type")).toBe("冷氣類型");
    expect(fieldLabel("faq_reference")).toBe("參考 FAQ");
    expect(fieldLabel("issue_details")).toBe("問題說明");
    expect(fieldLabel("pickup_method")).toBe("取件方式");
    expect(fieldLabel("clinic_name")).toBe("診所名稱");
    expect(fieldLabel("clinic_address")).toBe("診所地址");
    expect(fieldLabel("clinic_phone")).toBe("診所電話");
    expect(fieldLabel("appointment_date")).toBe("看診日期");
    expect(fieldLabel("appointment_time")).toBe("看診時間");
    expect(fieldLabel("symptom_note")).toBe("症狀描述");
  });

  it("falls back to the raw key when unknown", () => {
    expect(fieldLabel("some_new_field")).toBe("some_new_field");
  });
});

describe("fieldValueLabel", () => {
  it("translates known enum values", () => {
    expect(fieldValueLabel("MORNING")).toBe("上午");
    expect(fieldValueLabel("FRONT_LOAD")).toBe("滾筒式");
    expect(fieldValueLabel("YES")).toBe("是");
    expect(fieldValueLabel("NO")).toBe("否");
    expect(fieldValueLabel("HOME_PICKUP")).toBe("到府收件");
  });

  it("stringifies unknown values as-is", () => {
    expect(fieldValueLabel(2)).toBe("2");
    expect(fieldValueLabel("台北市信義區")).toBe("台北市信義區");
    expect(fieldValueLabel("data:image/png;base64,abc")).toBe("已上傳圖片");
  });
});

describe("buildFieldRows", () => {
  it("maps collected fields into labeled rows preserving insertion order", () => {
    const rows = buildFieldRows({ quantity: 2, preferred_time_slot: "14:00" });
    expect(rows).toEqual([
      { key: "quantity", label: "數量", value: "2" },
      { key: "preferred_time_slot", label: "希望時段", value: "14:00" },
    ]);
  });

  it("returns an empty array for no collected fields", () => {
    expect(buildFieldRows({})).toEqual([]);
  });

  it("formats a goods cart array as a readable list instead of stringifying it", () => {
    const rows = buildFieldRows({
      store_id: "store-001",
      goods: [
        { id: "item-001", title: "招牌便當", price: 110, quantity: 1 },
        { id: "item-010", title: "紅茶", price: 65, quantity: 2 },
      ],
    });
    expect(rows).toEqual([
      { key: "store_id", label: "店家", value: "store-001" },
      { key: "goods", label: "餐點內容", value: "招牌便當 x1、紅茶 x2" },
    ]);
  });

  it("formats an empty goods cart as a dash rather than an empty string", () => {
    const rows = buildFieldRows({ goods: [] });
    expect(rows).toEqual([{ key: "goods", label: "餐點內容", value: "-" }]);
  });

  it("formats an address object as one readable line", () => {
    const rows = buildFieldRows({
      address: {
        lat: 25.033,
        lng: 121.565,
        city: "台北市",
        area: "信義區",
        street: "松仁路100號",
        remark: "8樓",
        contact_name: "王小明",
      },
    });
    expect(rows).toEqual([
      { key: "address", label: "地址", value: "台北市信義區松仁路100號（8樓）" },
    ]);
  });

  it("omits the remark parentheses when there is no remark", () => {
    const rows = buildFieldRows({
      address: { city: "台北市", area: "信義區", street: "松仁路100號", remark: "" },
    });
    expect(rows).toEqual([
      { key: "address", label: "地址", value: "台北市信義區松仁路100號" },
    ]);
  });
});

describe("formatFieldValue", () => {
  it("delegates to fieldValueLabel for plain string/number values", () => {
    expect(formatFieldValue("AFTERNOON")).toBe("下午");
    expect(formatFieldValue(3)).toBe("3");
  });
});
