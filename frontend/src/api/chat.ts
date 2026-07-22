import type { ChatResponse } from "../types/request";
import { api } from "./client";

export function createSession() {
  return api<{ session_id: string; created_at: string }>("/api/sessions", {
    method: "POST",
  });
}

export function sendMessage(sessionId: string, message: string) {
  return api<ChatResponse>("/api/chat", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId, message }),
  });
}

export function updateFormDraft(sessionId: string, fields: Record<string, string | number | null>) {
  return api<ChatResponse>("/api/chat/form", {
    method: "PATCH",
    body: JSON.stringify({ session_id: sessionId, fields }),
  });
}
