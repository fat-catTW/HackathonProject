import { useCallback, useEffect, useSyncExternalStore } from "react";
import { listRequests } from "../api/requests";
import type { RequestListItem, RequestStatus } from "../types/request";
import { useAuth } from "./useAuth";

/**
 * 廠商在後台按下接單／婉拒後，住戶端要主動跳出來告訴他，而不是等他自己想到
 * 去「我的服務」翻一次。
 *
 * 產品規格上這是推播；Demo 版沒有 Web Push，改成住戶端每 POLL_INTERVAL_MS 打一次
 * 案件清單，比對上次看到的狀態，發現有案件往前走了就彈一張卡（跟每日問候卡同一套
 * 「推播管道是假的，但卡片上寫的每一句都是真的」的做法，見 useDailyGreeting）。
 */
export const POLL_INTERVAL_MS = 10_000;

/**
 * 上次看到的每張案件狀態（request_id → status）。
 *
 * 放 sessionStorage 而非 localStorage：登入 token 本來就存在 sessionStorage，
 * 快照跟著登入階段一起生一起滅，換人登入或關掉分頁後不會拿舊帳號的殘影來比對。
 */
const SEEN_KEY = "ai-butler-case-status-seen";

export type CaseUpdateStatus =
  | "CONFIRMED"
  | "CONTACTED"
  | "QUOTED"
  | "REJECTED"
  | "IN_PROGRESS"
  | "COMPLETED";

export interface CaseUpdateCopy {
  badge: string;
  title: string;
  /** amount 只有報價通知用得到；其餘狀態的文案忽略它。 */
  message: (serviceName: string, amount?: number | null) => string;
  /** 對應語意色 Token 的字首，例如 success → --color-success / --color-success-soft。 */
  tone: "success" | "warning" | "info";
}

/**
 * 哪些狀態值得打斷使用者，以及要跟他說什麼。
 *
 * 只列「別人替你動了手」的狀態：DRAFT／SUBMITTED 這些是住戶自己剛做完的事，
 * 再彈一張卡告訴他「你剛剛送出了一張單」只會惹人厭。CANCELLED 同理（住戶自己按的取消）。
 */
export const CASE_UPDATE_COPY: Record<CaseUpdateStatus, CaseUpdateCopy> = {
  CONFIRMED: {
    badge: "已接單",
    title: "有人接下你的服務了",
    message: (name) => `你的「${name}」已經有服務人員接下，會依約定的時間為你服務。`,
    tone: "success",
  },
  CONTACTED: {
    badge: "已聯繫",
    title: "服務人員聯繫過你了",
    message: (name) => `「${name}」的服務人員已經跟你聯繫過，接下來會安排報價或到府時間。`,
    tone: "info",
  },
  QUOTED: {
    badge: "已報價",
    title: "報價來了",
    // 金額直接寫在卡片上：報價通知最重要的資訊就是那個數字，讓人再點兩層才看得到
    // 等於這則通知只講了一半。
    message: (name, amount) =>
      amount != null
        ? `「${name}」的服務人員報價 NT$${amount.toLocaleString("zh-TW")}，可以點進案件看細節。`
        : `「${name}」的服務人員已經報價，可以點進案件看金額與細節。`,
    tone: "warning",
  },
  REJECTED: {
    badge: "已婉拒",
    title: "這張單被婉拒了",
    message: (name) =>
      `「${name}」目前沒有服務人員可以承接。可以換個時段再送一次，或直接請管家幫你找別家。`,
    tone: "warning",
  },
  IN_PROGRESS: {
    badge: "服務中",
    title: "服務開始進行了",
    message: (name) => `「${name}」的服務人員已經開始作業，有問題可以直接聯絡他。`,
    tone: "info",
  },
  COMPLETED: {
    badge: "已完成",
    title: "服務完成了",
    message: (name) => `「${name}」已經完成，方便的話去看看結果，也可以分享給家人。`,
    tone: "success",
  },
};

export interface CaseUpdate {
  requestId: string;
  serviceName: string;
  status: CaseUpdateStatus;
  /** 報價通知要在卡片上直接寫出金額；其他狀態是 null。 */
  quoteAmount?: number | null;
}

function isNotifiable(status: RequestStatus): status is CaseUpdateStatus {
  return status in CASE_UPDATE_COPY;
}

function readSeen(): Record<string, RequestStatus> {
  try {
    const raw = sessionStorage.getItem(SEEN_KEY);
    return raw ? (JSON.parse(raw) as Record<string, RequestStatus>) : {};
  } catch {
    return {};
  }
}

function writeSeen(next: Record<string, RequestStatus>) {
  try {
    sessionStorage.setItem(SEEN_KEY, JSON.stringify(next));
  } catch {
    /* 私密瀏覽模式或容量已滿；只影響重新整理後會不會漏掉一次通知，不擋操作 */
  }
}

let seen = readSeen();
let queue: CaseUpdate[] = [];
let lastToken: string | null = null;
let polling = false;
let version = 0; // useSyncExternalStore 的變更計數器

const listeners = new Set<() => void>();

function notify() {
  version += 1;
  listeners.forEach((fn) => fn());
}

function subscribe(cb: () => void) {
  listeners.add(cb);
  return () => listeners.delete(cb);
}

/**
 * 把這次拿到的清單跟上次的快照比對，挑出「狀態往前走了」的案件排進彈窗佇列。
 *
 * 第一次看到的案件只記下現況、不彈窗：剛送出的單、或住戶自己一路走完的即時訂單
 * （例如商城下單當下就是已確認），都不該回頭再通知他一次他自己剛做過的事。
 */
function ingest(items: RequestListItem[]) {
  // 從空的開始重建，讓已經消失的案件自然掉出快照，不會無限長大。
  const next: Record<string, RequestStatus> = {};
  const fresh: CaseUpdate[] = [];

  for (const item of items) {
    next[item.request_id] = item.status;
    const previous = seen[item.request_id];
    if (previous === undefined || previous === item.status) continue;
    if (!isNotifiable(item.status)) continue;
    fresh.push({
      requestId: item.request_id,
      serviceName: item.service_name,
      status: item.status,
      quoteAmount: item.quote_amount,
    });
  }

  seen = next;
  writeSeen(next);
  // 沒有新消息就不要 notify：每 10 秒叫醒一次整棵樹沒有意義。
  if (fresh.length === 0) return;
  queue = [...queue, ...fresh];
  notify();
}

function poll() {
  if (polling) return; // 上一次還沒回來（例如網路很慢）就跳過這一輪，不要疊請求
  polling = true;
  listRequests()
    .then((result) => ingest(result.items))
    .catch(() => {
      // 通知是加分的貼心，不是必要功能：拿不到清單就安靜地跳過這一輪，
      // 不要在使用者正在做別的事情時跳出一張「載入失敗」的卡。
    })
    .finally(() => {
      polling = false;
    });
}

/**
 * 目前該跳的那一則案件通知（一次只跳一張，其餘排隊）與關掉它的方法。
 *
 * 只該由一個地方掛載（App 的 Protected），佇列放在 module 層而不是元件 state：
 * 住戶在彈窗還開著的時候換頁，Protected 會重新掛載，state 版本會讓通知消失。
 */
export function useCaseUpdates() {
  const { token } = useAuth();
  useSyncExternalStore(subscribe, () => version);

  useEffect(() => {
    if (!token) {
      queue = [];
      lastToken = null;
      return;
    }
    if (lastToken !== token) {
      // 換帳號登入：上一位使用者的快照與待跳通知都不算數。
      queue = [];
      seen = {};
      writeSeen(seen);
      lastToken = token;
    }
    poll();
    const timer = setInterval(poll, POLL_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [token]);

  const dismiss = useCallback(() => {
    queue = queue.slice(1);
    notify();
  }, []);

  return { update: queue[0] ?? null, dismiss };
}
