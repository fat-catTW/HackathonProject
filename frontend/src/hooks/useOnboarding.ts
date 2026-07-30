import { useCallback, useEffect, useSyncExternalStore } from "react";
import { completeOnboarding, fetchOnboardingStatus, type OnboardingStatus } from "../api/onboarding";
import { getToken } from "../api/client";

/** 導引內容版本號；日後新增導引頁（例如語音輸入介紹）時提高此值，
 * 已完成舊版本的使用者會被視為「未完成」而重新看到導引（見設計書②）。 */
export const ONBOARDING_VERSION = 1;

// 本地暫存：使用者已按下「開始使用」但尚未成功同步後端的版本號。網路異常時
// 靠這個旗標避免下次登入重複彈出，之後背景重試同步（見設計書⑤異常處理）。
const PENDING_KEY = "ai-butler-onboarding-pending";

let status: OnboardingStatus | null = null; // null = 尚未取得（登出或載入中）
let forceOpen = false; // 使用者在設定中點「重新觀看」
let lastLoadedToken: string | null = null;
let retryTimer: ReturnType<typeof setTimeout> | null = null;
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

function readPendingVersion(): number | null {
  try {
    const raw = localStorage.getItem(PENDING_KEY);
    return raw ? Number(raw) : null;
  } catch {
    return null;
  }
}

function writePendingVersion(v: number) {
  try {
    localStorage.setItem(PENDING_KEY, String(v));
  } catch {
    /* 私密瀏覽模式或容量已滿時忽略，僅影響離線容錯，不影響本次操作 */
  }
}

function clearPendingVersion() {
  try {
    localStorage.removeItem(PENDING_KEY);
  } catch {
    /* ignore */
  }
}

function isEffectivelyCompleted(): boolean {
  if (status?.completed && status.version >= ONBOARDING_VERSION) return true;
  const pending = readPendingVersion();
  return pending !== null && pending >= ONBOARDING_VERSION;
}

function scheduleRetry(run: () => void) {
  if (retryTimer) clearTimeout(retryTimer);
  retryTimer = setTimeout(run, 15_000);
}

function syncPendingToBackend() {
  const pending = readPendingVersion();
  if (pending === null) return;
  completeOnboarding(pending)
    .then(() => {
      clearPendingVersion();
      status = { completed: true, version: pending };
      notify();
    })
    .catch(() => {
      scheduleRetry(syncPendingToBackend);
    });
}

function loadStatus(token: string) {
  fetchOnboardingStatus()
    .then((result) => {
      status = result;
      notify();
      syncPendingToBackend();
    })
    .catch(() => {
      // 讀取失敗時保持 status 為 null（未知），避免誤判成「未完成」而強制彈出。
      lastLoadedToken = null;
      void token;
    });
}

/** 新手導引狀態；以使用者帳號層級記錄（呼叫後端 API），並用本地暫存
 * 容錯網路異常（見 M13 設計書）。 */
export function useOnboarding() {
  const token = useSyncExternalStore(subscribe, getToken);
  useSyncExternalStore(subscribe, () => version);

  useEffect(() => {
    if (!token) {
      status = null;
      forceOpen = false;
      lastLoadedToken = null;
      return;
    }
    if (lastLoadedToken !== token) {
      // 帳號切換（例如換人登入）：先清掉舊帳號的狀態，避免短暫顯示上一位使用者的結果。
      status = null;
      lastLoadedToken = token;
      loadStatus(token);
    }
  }, [token]);

  const shouldShow = !!token && (forceOpen || (status !== null && !isEffectivelyCompleted()));

  const complete = useCallback(() => {
    forceOpen = false;
    writePendingVersion(ONBOARDING_VERSION);
    status = { completed: true, version: ONBOARDING_VERSION };
    notify();
    completeOnboarding(ONBOARDING_VERSION)
      .then(() => clearPendingVersion())
      .catch(() => scheduleRetry(syncPendingToBackend));
  }, []);

  const reopen = useCallback(() => {
    forceOpen = true;
    notify();
  }, []);

  const close = useCallback(() => {
    forceOpen = false;
    notify();
  }, []);

  return { shouldShow, complete, reopen, close };
}
