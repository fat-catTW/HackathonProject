export interface SupportPrefillContext {
  currentPageId: string;
  requestId?: string;
  serviceName?: string;
  faqQuestion?: string;
}

const PAGE_LABELS: Record<string, string> = {
  home: "首頁",
  my_services: "我的服務",
  request_detail: "案件詳情",
  reservation_flow: "餐廳訂位",
  delivery_flow: "外送訂單",
  service_form: "服務表單",
  assistant: "AI 助手",
};

export function pageLabelForSupport(currentPageId: string) {
  return PAGE_LABELS[currentPageId] ?? "目前頁面";
}

export function buildSupportRequestPrefill({
  currentPageId,
  requestId,
  serviceName,
  faqQuestion,
}: SupportPrefillContext) {
  return {
    faq_reference: faqQuestion ?? "",
    current_page_id: currentPageId,
    current_page_label: pageLabelForSupport(currentPageId),
    related_request_id: requestId ?? "",
    related_service_name: serviceName ?? "",
    issue_summary: faqQuestion ? `${faqQuestion}，想請客服進一步協助` : "",
  };
}
