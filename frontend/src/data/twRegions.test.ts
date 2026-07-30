import { describe, expect, it } from "vitest";
import { counties, getDistrictsByCountyName } from "./twRegions";

describe("twRegions", () => {
  it("includes complete districts for counties that previously had missing data", () => {
    expect(counties).toHaveLength(22);
    expect(getDistrictsByCountyName("嘉義縣")).toContain("民雄鄉");
    expect(getDistrictsByCountyName("台中市")).toContain("南屯區");
    expect(getDistrictsByCountyName("新竹市")).toEqual(["東區", "北區", "香山區"]);
  });
});
