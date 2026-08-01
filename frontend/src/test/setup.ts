import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";
import { Window } from "happy-dom";

// Node 22 之後 globalThis 內建了（預設停用的）localStorage / sessionStorage，
// vitest 不會用 happy-dom 的實作覆蓋既有的 node 全域，導致存取到 undefined。
// 這裡補回 happy-dom 的 Storage，讓測試在 node 20 與新版 node 上行為一致。
const storageWindow = new Window();
for (const key of ["localStorage", "sessionStorage"] as const) {
  if (typeof (globalThis as Record<string, unknown>)[key] === "undefined") {
    Object.defineProperty(globalThis, key, {
      value: storageWindow[key],
      configurable: true,
      writable: true,
    });
  }
}

afterEach(() => {
  cleanup();
});
