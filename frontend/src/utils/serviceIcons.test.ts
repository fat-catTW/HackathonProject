import { describe, expect, it } from "vitest";
import { serviceIconForId, serviceIconType } from "./serviceIcons";

describe("serviceIconType", () => {
  it("maps known service names to their icon type", () => {
    expect(serviceIconType("冷氣清潔")).toBe("aircon");
    expect(serviceIconType("水電維修")).toBe("plumbing");
    expect(serviceIconType("居家清潔")).toBe("cleaning");
  });

  it("falls back to chat for unknown or missing service names", () => {
    expect(serviceIconType("未知服務")).toBe("chat");
    expect(serviceIconType(null)).toBe("chat");
    expect(serviceIconType(undefined)).toBe("chat");
  });
});

describe("serviceIconForId", () => {
  it("reads the icon straight from the service catalog", () => {
    expect(serviceIconForId("air_conditioner_cleaning")).toBe("aircon");
    expect(serviceIconForId("restaurant_reservation")).toBe("restaurant");
    expect(serviceIconForId("package_shipping")).toBe("moving");
  });

  it("falls back to chat for unknown or missing service ids", () => {
    expect(serviceIconForId("not_a_service")).toBe("chat");
    expect(serviceIconForId(null)).toBe("chat");
    expect(serviceIconForId(undefined)).toBe("chat");
  });
});
