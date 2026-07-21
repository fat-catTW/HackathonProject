import { useCallback, useSyncExternalStore } from "react";
import { clearAuth, getToken, getUserName, setAuth } from "../api/client";

const listeners = new Set<() => void>();

function notify() {
  listeners.forEach((fn) => fn());
}

export function useAuth() {
  const token = useSyncExternalStore(
    (cb) => {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    () => getToken(),
  );

  const login = useCallback((tok: string, name: string) => {
    setAuth(tok, name);
    notify();
  }, []);

  const logout = useCallback(() => {
    clearAuth();
    notify();
  }, []);

  return { token, name: getUserName(), isLoggedIn: !!token, login, logout };
}
