import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

/**
 * Tier B 登入頁的視覺套用迴歸測試（Task 8.3）。
 *
 * 斷言重點：表單卡未套 `glass-panel`（Requirement 12.2）、Mascot 使用 tone 而非舊的
 * bodyColor/highlightColor props（Requirement 12.3）、既有欄位與版面順序仍存在
 * （Requirement 12.4）。後端 API 一律 mock，避免測試依賴真實伺服器。
 */
vi.mock("../api/auth", () => ({
  fetchDemoAccounts: vi.fn(async () => ({
    accounts: [{ token: "demo-token", name: "王小明", email: "demo@example.com" }],
  })),
  loginWithEmail: vi.fn(),
  registerAccount: vi.fn(),
}));

vi.mock("../api/vendor", () => ({
  fetchVendorDemoAccounts: vi.fn(async () => ({
    accounts: [{ name: "示範水電行", email: "vendor@example.com", password: "vendor1234" }],
  })),
  vendorLogin: vi.fn(),
}));

import { LoginPage } from "./LoginPage";
import { VendorLoginPage } from "./VendorLoginPage";

function renderWithRouter(ui: React.ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

beforeEach(() => {
  document.documentElement.setAttribute("data-color-mode", "light");
});

afterEach(() => {
  localStorage.clear();
});

describe("LoginPage 視覺套用", () => {
  it("keeps the form card opaque — no glass-panel anywhere on the page (Requirement 12.2)", async () => {
    const { container } = renderWithRouter(<LoginPage />);

    await userEvent.click(screen.getByRole("button", { name: "登入" }));

    expect(container.querySelectorAll(".glass-panel").length).toBe(0);
  });

  it("renders the large centered AI orb icon instead of the Mascot (Requirement 12.3)", () => {
    const { container } = renderWithRouter(<LoginPage />);

    const orb = container.querySelector('img[src="/images/ai-orb-icon.png"]');
    expect(orb).not.toBeNull();
    expect(orb).toHaveAttribute("aria-hidden");
  });

  it("keeps the existing fields and layout order intact (Requirement 12.4)", async () => {
    renderWithRouter(<LoginPage />);

    expect(screen.getByRole("heading", { name: "AI 智慧生活服務管家" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "登入" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "註冊" })).toBeInTheDocument();

    // Demo 帳號一鍵登入現在收在右上角「更多登入選項」選單裡，需先展開選單才會出現在 DOM 中
    await userEvent.click(screen.getByRole("button", { name: "更多登入選項" }));
    await waitFor(() => expect(screen.getByText("Demo Account 一鍵登入")).toBeInTheDocument());
    await userEvent.click(screen.getByRole("button", { name: "更多登入選項" }));

    await userEvent.click(screen.getByRole("button", { name: "註冊" }));
    const inputs = screen.getAllByRole("textbox");
    // 註冊表單欄位順序：姓名 → Email（密碼為 type=password，不屬 textbox role）
    expect(inputs[0]).toHaveAttribute("placeholder", "姓名（選填）");
    expect(inputs[1]).toHaveAttribute("placeholder", "Email");
    expect(screen.getByPlaceholderText("密碼（至少 8 碼）")).toBeInTheDocument();
  });
});

describe("VendorLoginPage 視覺套用", () => {
  it("keeps the form card opaque — no glass-panel anywhere on the page (Requirement 12.2)", async () => {
    const { container } = renderWithRouter(<VendorLoginPage />);

    await waitFor(() => expect(screen.getByText("Demo 廠商帳號")).toBeInTheDocument());
    expect(container.querySelectorAll(".glass-panel").length).toBe(0);
  });

  it("renders the subtle wordmark texture (Requirement 12.1)", () => {
    const { container } = renderWithRouter(<VendorLoginPage />);

    const texture = container.querySelector(".bg-wordmark-texture");
    expect(texture?.classList.contains("bg-wordmark-texture--subtle")).toBe(true);
  });

  it("keeps existing fields and the Demo account card structure (Requirements 12.3, 12.4)", async () => {
    renderWithRouter(<VendorLoginPage />);

    expect(screen.getByText("廠商後台")).toBeInTheDocument();
    expect(screen.getByLabelText("廠商 Email")).toBeInTheDocument();
    expect(screen.getByLabelText("密碼")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "登入" })).toBeInTheDocument();

    await waitFor(() => expect(screen.getByText("示範水電行")).toBeInTheDocument());
    expect(screen.getByText("vendor@example.com")).toBeInTheDocument();
  });
});
