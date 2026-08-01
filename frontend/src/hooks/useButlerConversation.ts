import { useSyncExternalStore } from "react";
import { createSession } from "../api/chat";
import { getToken } from "../api/client";
import type { ChatEvent } from "../types/request";
import type { CollectedFieldValue } from "../utils/fieldLabels";

/**
 * AI 管家的對話狀態，存在模組層而不是元件 state。
 *
 * 代操表單時面板會關掉（不然整張表單被蓋住），表單頁與 AI 管家頁又各自掛載自己的
 * ButlerPanel。若每次掛載都開新 session，使用者重新打開管家接著說「時間改成下午三點」
 * 就會變成一段沒有上下文的新對話。
 *
 * 跨元件共享狀態沿用 useColorMode / useAccessibilityMode 那套 useSyncExternalStore +
 * listeners 的既有慣例，讓「唯一真相」只有一份，不必在每個更新點手動同步兩次。
 */
export interface ButlerConversation {
  /** 這段對話屬於哪個登入者；換人登入一定要整段丟掉（裡面有電話、地址等個資）。 */
  token: string | null;
  sessionId: string | null;
  events: ChatEvent[];
  serviceName: string | null;
  collected: Record<string, CollectedFieldValue>;
  missing: string[];
  status: string;
}

export const GREETING: ChatEvent = {
  role: "ASSISTANT",
  content:
    "您好，我是 AI 管家。請直接告訴我您想申請什麼服務，例如冷氣清洗、居家清潔或水電修繕；" +
    "如果您已經在服務表單頁，也可以說「幫我填」，我會直接幫您把表單填好。",
};

function emptyConversation(): ButlerConversation {
  return {
    token: getToken(),
    sessionId: null,
    events: [GREETING],
    serviceName: null,
    collected: {},
    missing: [],
    status: "COLLECTING_INFORMATION",
  };
}

const listeners = new Set<() => void>();
let conversation: ButlerConversation = emptyConversation();
/** 建立中的 session；面板短時間內掛載兩次（StrictMode、換頁）時共用同一個請求。 */
let sessionRequest: Promise<string> | null = null;

function notify() {
  listeners.forEach((fn) => fn());
}

function update(patch: Partial<ButlerConversation>) {
  conversation = { ...conversation, ...patch };
  notify();
}

export function getButlerConversation(): ButlerConversation {
  return conversation;
}

/** 案件送出後（或換人登入時）重來一段乾淨的對話。 */
export function resetButlerConversation() {
  sessionRequest = null;
  conversation = emptyConversation();
  notify();
}

export function appendButlerEvent(event: ChatEvent) {
  update({ events: [...conversation.events, event] });
}

export function saveButlerTurn(patch: Partial<ButlerConversation>) {
  update(patch);
}

/**
 * 取得（必要時建立）這段對話的 session id。
 * 登入者換人時先把整段對話丟掉，不讓下一位看到上一位的對話與聯絡資訊。
 */
export function ensureButlerSession(): Promise<string> {
  const token = getToken();
  if (conversation.token !== token) {
    resetButlerConversation();
  }
  if (conversation.sessionId) return Promise.resolve(conversation.sessionId);
  if (!sessionRequest) {
    sessionRequest = createSession()
      .then((r) => {
        update({ sessionId: r.session_id });
        return r.session_id;
      })
      .catch((error) => {
        sessionRequest = null;
        throw error;
      });
  }
  return sessionRequest;
}

export function useButlerConversation(): ButlerConversation {
  return useSyncExternalStore(
    (cb) => {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    getButlerConversation,
  );
}
