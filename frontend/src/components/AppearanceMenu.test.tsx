import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

// `useOnboarding` 會打 API 並持有模組層級狀態，這裡只關心「重看導覽」入口是否
// 仍呼叫 reopen()，因此改以 spy 取代整個 hook。
const { reopenSpy } = vi.hoisted(() => ({ reopenSpy: vi.fn() }));

vi.mock("../hooks/useOnboarding", () => ({
  useOnboarding: () => ({
    shouldShow: false,
    complete: vi.fn(),
    reopen: reopenSpy,
    close: vi.fn(),
  }),
}));

/**
 * `useColorMode` / `useAccessibilityMode` 以模組層級狀態實作，測試間必須重新載入
 * 模組（比照 `useColorMode.test.ts` 的 vi.resetModules 寫法）才能取得乾淨初始值。
 */
async function renderMenu() {
  vi.resetModules();
  const { AppearanceMenu } = await import("./AppearanceMenu");
  const user = userEvent.setup();
  const view = render(<AppearanceMenu />);
  return { user, ...view };
}

/** 展開選單並回傳 popup 容器。 */
async function openMenu() {
  const { user, ...view } = await renderMenu();
  await user.click(screen.getByRole("button", { name: "開啟外觀設定" }));
  const menu = screen.getByRole("menu", { name: "外觀設定" });
  return { user, menu, ...view };
}

beforeEach(() => {
  reopenSpy.mockClear();
  localStorage.clear();
  document.documentElement.removeAttribute("data-color-mode");
  document.documentElement.removeAttribute("data-a11y");
});

describe("AppearanceMenu", () => {
  it("keeps the menu collapsed until the mascot trigger is pressed", async () => {
    const { user } = await renderMenu();

    const trigger = screen.getByRole("button", { name: "開啟外觀設定" });
    expect(trigger).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();

    await user.click(trigger);

    expect(trigger).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("menu", { name: "外觀設定" })).toBeInTheDocument();
  });

  it("offers exactly the light and dark options with readable text labels", async () => {
    const { menu } = await openMenu();

    const options = screen.getAllByRole("menuitemradio");
    expect(options).toHaveLength(2);
    expect(screen.getByRole("menuitemradio", { name: "切換為淺色模式" })).toBeInTheDocument();
    expect(screen.getByRole("menuitemradio", { name: "切換為深色模式" })).toBeInTheDocument();
    expect(menu).toHaveTextContent("淺色");
    expect(menu).toHaveTextContent("深色");
  });

  it("does not render a colour-swatch picker UI", async () => {
    const { menu } = await openMenu();

    // 舊 ThemeMenu 以 5 個色塊選色，改版後選單內僅剩 4 個可互動元素：
    // 兩個模式選項 + 無障礙開關 + 重看導覽。
    expect(menu.querySelectorAll("button")).toHaveLength(4);
    expect(screen.queryByRole("menuitemradio", { name: /主題|顏色|色系/ })).not.toBeInTheDocument();
    // 色塊選色會以 inline background 色碼呈現；新選單不應存在任何硬編碼色塊。
    const swatches = Array.from(menu.querySelectorAll<HTMLElement>("[style]")).filter((el) =>
      /background/i.test(el.getAttribute("style") ?? ""),
    );
    expect(swatches).toHaveLength(0);
  });

  it("marks the active mode as checked and the other option as unchecked", async () => {
    await openMenu();

    expect(screen.getByRole("menuitemradio", { name: "切換為淺色模式" })).toHaveAttribute(
      "aria-checked",
      "true",
    );
    expect(screen.getByRole("menuitemradio", { name: "切換為深色模式" })).toHaveAttribute(
      "aria-checked",
      "false",
    );
    expect(screen.getByRole("menuitemradio", { name: "切換為淺色模式" })).toHaveTextContent(
      "淺色：使用中",
    );
  });

  it("applies and persists the chosen mode, updating data-color-mode", async () => {
    const { user } = await openMenu();
    expect(document.documentElement.getAttribute("data-color-mode")).toBe("light");

    await user.click(screen.getByRole("menuitemradio", { name: "切換為深色模式" }));

    expect(document.documentElement.getAttribute("data-color-mode")).toBe("dark");
    expect(localStorage.getItem("ai-butler-color-mode")).toBe("dark");
    // 選擇後選單收合。
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "開啟外觀設定" }));

    expect(screen.getByRole("menuitemradio", { name: "切換為深色模式" })).toHaveAttribute(
      "aria-checked",
      "true",
    );
    expect(screen.getByRole("menuitemradio", { name: "切換為淺色模式" })).toHaveAttribute(
      "aria-checked",
      "false",
    );

    await user.click(screen.getByRole("menuitemradio", { name: "切換為淺色模式" }));

    expect(document.documentElement.getAttribute("data-color-mode")).toBe("light");
    expect(localStorage.getItem("ai-butler-color-mode")).toBe("light");
  });

  it("keeps the accessibility toggle behaviour unchanged", async () => {
    const { user } = await openMenu();

    const toggle = screen.getByRole("menuitemcheckbox", { name: "切換無障礙模式" });
    expect(toggle).toHaveAttribute("aria-checked", "false");
    expect(toggle).toHaveTextContent("無障礙模式：已關閉");

    await user.click(toggle);

    expect(toggle).toHaveAttribute("aria-checked", "true");
    expect(toggle).toHaveTextContent("無障礙模式：已開啟");
    expect(document.documentElement.getAttribute("data-a11y")).toBe("true");
    expect(localStorage.getItem("ai-butler-a11y")).toBe("true");
    // 無障礙開關不影響色彩模式，且選單維持展開讓使用者確認效果。
    expect(document.documentElement.getAttribute("data-color-mode")).toBe("light");
    expect(screen.getByRole("menu", { name: "外觀設定" })).toBeInTheDocument();

    await user.click(toggle);

    expect(toggle).toHaveAttribute("aria-checked", "false");
    expect(document.documentElement.getAttribute("data-a11y")).toBe("false");
  });

  it("keeps the replay-onboarding entry behaviour unchanged", async () => {
    const { user } = await openMenu();

    await user.click(screen.getByRole("button", { name: "重新觀看新手導覽" }));

    expect(reopenSpy).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });
});
