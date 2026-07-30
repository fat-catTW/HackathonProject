export interface SupportFaqItem {
  id: string;
  question: string;
  answer: string;
}

export const SUPPORT_FAQS: SupportFaqItem[] = [
  {
    id: "cancel-order",
    question: "如何取消訂單？",
    answer:
      "可先到「我的服務」或案件詳情頁查看目前狀態。若案件仍可取消，頁面上會提供取消按鈕；若已進入處理中，建議直接轉真人客服協助。",
  },
  {
    id: "vendor-response",
    question: "多久會有廠商回覆？",
    answer:
      "送出需求後，系統會先建立案件並通知對應服務方。你可以在「我的服務」查看最新進度；若等待時間超過預期，也可以直接建立客服諮詢單請我們協助追蹤。",
  },
  {
    id: "view-quote",
    question: "如何查看報價？",
    answer:
      "若案件已有回覆或報價，通常會顯示在案件詳情頁的最新狀態與表單內容中。若你找不到對應資訊，轉真人客服時帶上案件編號會更快協助確認。",
  },
  {
    id: "track-progress",
    question: "如何追蹤目前進度？",
    answer:
      "你可以到「我的服務」查看所有案件，或進入單筆案件詳情頁查看目前狀態、建立時間與後續互動紀錄。",
  },
];
