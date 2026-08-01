import { describe, expect, it } from "vitest";
import { splitTwAddress } from "./twAddress";

describe("splitTwAddress", () => {
  it("splits a full address into the form's three controls", () => {
    expect(splitTwAddress("台南市東區大學路一段 168 號")).toEqual({
      county: "台南市",
      district: "東區",
      detail: "大學路一段 168 號",
    });
  });

  it("accepts the 臺 spelling for counties", () => {
    expect(splitTwAddress("臺北市大安區忠孝東路四段 1 號")).toEqual({
      county: "台北市",
      district: "大安區",
      detail: "忠孝東路四段 1 號",
    });
  });

  it("prefers the longest matching district so 東勢區 does not lose to 東區", () => {
    expect(splitTwAddress("台中市東勢區豐勢路 100 號").district).toBe("東勢區");
  });

  it("keeps the whole string as detail when the county cannot be recognised", () => {
    expect(splitTwAddress("忠孝東路四段 1 號")).toEqual({
      county: "",
      district: "",
      detail: "忠孝東路四段 1 號",
    });
  });

  it("keeps the rest as detail when only the county is recognised", () => {
    expect(splitTwAddress("台南市不存在區某某路 1 號")).toEqual({
      county: "台南市",
      district: "",
      detail: "不存在區某某路 1 號",
    });
  });

  it("returns empty parts for an empty address", () => {
    expect(splitTwAddress("")).toEqual({ county: "", district: "", detail: "" });
  });
});
