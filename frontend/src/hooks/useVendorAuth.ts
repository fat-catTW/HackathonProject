import { useCallback, useSyncExternalStore } from "react";
import {
  clearVendorAuth,
  getVendorId,
  getVendorName,
  getVendorToken,
  setVendorAuth,
} from "../api/client";

const listeners = new Set<() => void>();

function notify() {
  listeners.forEach((fn) => fn());
}

export function useVendorAuth() {
  const token = useSyncExternalStore(
    (cb) => {
      listeners.add(cb);
      return () => listeners.delete(cb);
    },
    () => getVendorToken(),
  );

  const login = useCallback((tok: string, name: string, vendorId: number) => {
    setVendorAuth(tok, name, vendorId);
    notify();
  }, []);

  const logout = useCallback(() => {
    clearVendorAuth();
    notify();
  }, []);

  return {
    token,
    name: getVendorName(),
    vendorId: getVendorId(),
    isLoggedIn: !!token,
    login,
    logout,
  };
}
