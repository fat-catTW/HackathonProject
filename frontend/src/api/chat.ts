import type { ChatResponse, FormContext } from "../types/request";
import { api } from "./client";

export function createSession() {
  return api<{ session_id: string; created_at: string }>("/api/sessions", {
    method: "POST",
  });
}

/** 使用者裝置上的今天（YYYY-MM-DD，本地時區）。 */
function clientDate() {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${now.getFullYear()}-${month}-${day}`;
}

export function sendMessage(
  sessionId: string,
  message: string,
  currentPageId?: string,
  formContext?: FormContext | null,
) {
  return api<ChatResponse>("/api/chat", {
    method: "POST",
    body: JSON.stringify({
      session_id: sessionId,
      message,
      current_page_id: currentPageId ?? null,
      form_context: formContext ?? null,
      // 「這禮拜三」要用使用者當下的日期換算，不是伺服器的日期
      client_date: clientDate(),
    }),
  });
}
