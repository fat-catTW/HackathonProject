import { api } from "./client";

export interface ScamCheckResult {
  category: string;
  explanation: string;
}

export function checkScamMessage(message: string) {
  return api<ScamCheckResult>("/api/scam-check", {
    method: "POST",
    body: JSON.stringify({ message }),
  });
}
