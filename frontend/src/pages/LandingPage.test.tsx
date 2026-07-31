import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

/**
 * GSAP 的進場動畫與 ScrollTrigger 在 happy-dom 下沒有真正的 layout / scroll 可依附，
 * 且動畫本身不屬於本測試涵蓋的行為語意，因此整組 mock 掉，只保留 LandingPage 的 DOM 結構斷言。
 */
vi.mock("gsap", () => {
  const context = vi.fn(() => ({ revert: vi.fn() }));
  return {
    default: {
      registerPlugin: vi.fn(),
      context,
      from: vi.fn(),
      utils: { toArray: () => [] },
    },
  };
});

vi.mock("gsap/ScrollTrigger", () => ({ ScrollTrigger: {} }));

import { LandingPage } from "./LandingPage";

function renderPage() {
  return render(
    <MemoryRouter>
      <LandingPage />
    </MemoryRouter>,
  );
}

describe("LandingPage", () => {
  it("renders a PhoneMockup at the center of the hero (Requirement 11.1)", () => {
    renderPage();

    expect(screen.getByTestId("phone-mockup")).toBeInTheDocument();
  });

  it("uses no iframe or external image for the hero mockup (Requirement 9.1)", () => {
    const { container } = renderPage();

    expect(container.querySelector("iframe")).toBeNull();
  });

  it("surrounds the mockup with a small set of icon-type FloatingBadges", () => {
    renderPage();

    // 使用者回饋先前的「300+ 位長輩正在使用」大頭貼徽章沒有必要，已移除；
    // 之後又回饋右上角少了一個特點描述，補上「24 小時待命」使左右各三個元素對稱。
    const badges = screen.getAllByTestId("floating-badge");
    expect(badges.length).toBe(3);
    expect(screen.getByText("說出需求")).toBeInTheDocument();
    expect(screen.getByText("表單已整理")).toBeInTheDocument();
    expect(screen.getByText("24 小時待命")).toBeInTheDocument();
  });

  it("renders the two 1:1 hero people photos with descriptive alt text (Requirements 18.1, 18.2)", () => {
    renderPage();

    const elder = screen.getByAltText(/長者.*手機/);
    const staff = screen.getByAltText(/到府服務人員/);

    expect(elder).toBeInTheDocument();
    expect(staff).toBeInTheDocument();
    expect(elder.getAttribute("src")).toMatch(/hero-elder-user/);
    expect(staff.getAttribute("src")).toMatch(/hero-service-staff/);
  });

  it("shares one untouched image across both color modes — no filter or dark: variant (Requirement 18.3)", () => {
    const { container } = renderPage();

    for (const img of container.querySelectorAll("img")) {
      expect(img.className).not.toMatch(/\bdark:/);
      expect(img.className).not.toMatch(/\b(grayscale|sepia|invert|brightness-|contrast-|saturate-|mix-blend-)/);
      expect(img.getAttribute("style")).toBeNull();
    }
  });

  it("no longer renders the removed theme color-swatch preview (Requirements 3.1, 3.3, 11.2)", () => {
    const { container } = renderPage();

    expect(screen.queryByText("配色")).toBeNull();
    expect(screen.queryByRole("radiogroup")).toBeNull();
    // 舊版色塊預覽以 aria-label「主題」開頭的按鈕呈現，改版後應完全消失
    expect(container.querySelector('[aria-label*="主題"]')).toBeNull();
  });

  it("keeps the Highlights and Services sections intact (Requirement 11.4)", () => {
    renderPage();

    expect(screen.getByText("用說的就能建立需求")).toBeInTheDocument();
    expect(screen.getByText("表單同步整理完成")).toBeInTheDocument();
    expect(screen.getByText("串接真正的 AWS 服務流程")).toBeInTheDocument();

    expect(screen.getByText("目前可用服務")).toBeInTheDocument();
    expect(screen.getByText("水電修繕")).toBeInTheDocument();
    // 「冷氣清洗」同時出現在手機外框的對話示意與服務卡，故用 getAllByText
    expect(screen.getAllByText("冷氣清洗").length).toBeGreaterThanOrEqual(1);
  });
});
