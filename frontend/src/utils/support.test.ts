import { describe, expect, it } from "vitest";
import { buildSupportRequestPrefill, pageLabelForSupport } from "./support";

describe("pageLabelForSupport", () => {
  it("maps known page ids to readable labels", () => {
    expect(pageLabelForSupport("home")).toBe("首頁");
    expect(pageLabelForSupport("request_detail")).toBe("案件詳情");
  });

  it("falls back for unknown page ids", () => {
    expect(pageLabelForSupport("somewhere")).toBe("目前頁面");
  });
});

describe("buildSupportRequestPrefill", () => {
  it("includes FAQ, page, and request context for the support form", () => {
    expect(
      buildSupportRequestPrefill({
        currentPageId: "request_detail",
        requestId: "REQ-20260730-001",
        serviceName: "外送訂單",
        faqQuestion: "如何取消訂單？",
      }),
    ).toEqual({
      faq_reference: "如何取消訂單？",
      current_page_id: "request_detail",
      current_page_label: "案件詳情",
      related_request_id: "REQ-20260730-001",
      related_service_name: "外送訂單",
      issue_summary: "如何取消訂單？，想請客服進一步協助",
    });
  });
});
