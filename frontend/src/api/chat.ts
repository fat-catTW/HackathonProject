import type { ChatResponse } from "../types/request";
import { api } from "./client";

export function createSession() {
  return api<{ session_id: string; created_at: string }>("/api/sessions", {
    method: "POST",
  });
}

export function sendMessage(sessionId: string, message: string, currentPageId?: string) {
  return api<ChatResponse>("/api/chat", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId, message, current_page_id: currentPageId ?? null }),
  });
}
