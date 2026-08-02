import { useCallback, useEffect, useSyncExternalStore } from "react";
import { fetchDailyGreeting, type DailyGreeting } from "../api/greeting";
import { getToken } from "../api/client";

/** 已經看過哪一天的問候卡（YYYY-MM-DD）。一天只跳一次，就像一天只推播一次。 */
const SEEN_KEY = "ai-butler-daily-greeting-seen";

/**
 * 使用者裝置當地的 YYYY-MM-DD。
 *
 * 不能用 `toISOString()`：那會先轉成 UTC，台灣時間半夜 0–8 點會退回前一天，
 * 「今天的行程」整批算錯。
 */
export function localDateString(now: Date = new Date()): string {
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${now.getFullYear()}-${month}-${day}`;
}

function readSeenDate(): string | null {
  try {
    return localStorage.getItem(SEEN_KEY);
  } catch {
    return null;
  }
}

let card: DailyGreeting | null = null;
// localStorage 的記憶體副本：私密瀏覽模式寫入會丟例外，至少讓同一次瀏覽不重複跳卡。
let seenDate: string | null = readSeenDate();
let forceOpen = false; // 使用者在外觀設定點「重看今日問候」
let lastLoadedToken: string | null = null;
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

function markSeen(date: string) {
  seenDate = date;
  try {
    localStorage.setItem(SEEN_KEY, date);
  } catch {
    /* 私密瀏覽模式或容量已滿；只影響「下次開 App 會不會再跳一次」，不擋操作 */
  }
}

function loadCard(token: string) {
  fetchDailyGreeting(localDateString())
    .then((result) => {
      card = result;
      notify();
    })
    .catch(() => {
      // 問候卡是加分的貼心，不是必要功能：拿不到就安靜地不跳，不要擋在首頁前面。
      lastLoadedToken = null;
      void token;
    });
}

/**
 * 每日問候卡。規格上這是「早上 7 點自動推播」，Demo 版把「送到眼前」的時機
 * 改成進首頁時自動彈出，但一天只彈一次——推播一天也只會來一次，不會每次
 * 回到首頁都糊使用者一臉。想再看一次可以從外觀設定的「重看今日問候」進來。
 */
export function useDailyGreeting() {
  const token = useSyncExternalStore(subscribe, getToken);
  useSyncExternalStore(subscribe, () => version);

  useEffect(() => {
    if (!token) {
      card = null;
      forceOpen = false;
      lastLoadedToken = null;
      return;
    }
    if (lastLoadedToken !== token) {
      // 換帳號登入：先清掉上一位使用者的卡片，免得短暫顯示別人的行程。
      card = null;
      lastLoadedToken = token;
      loadCard(token);
    }
  }, [token]);

  const shouldShow = !!token && card !== null && (forceOpen || seenDate !== card.date);

  const dismiss = useCallback(() => {
    forceOpen = false;
    if (card) markSeen(card.date);
    notify();
  }, []);

  const reopen = useCallback(() => {
    forceOpen = true;
    notify();
  }, []);

  return { card, shouldShow, dismiss, reopen };
}
