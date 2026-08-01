import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { SearchAndCategoryFilter } from "./SearchAndCategoryFilter";

const CATEGORIES = [
  { id: "all", label: "全部", count: 5 },
  { id: "水電修繕", label: "水電修繕", count: 2 },
  { id: "居家清潔", label: "居家清潔", count: 3 },
];

describe("SearchAndCategoryFilter", () => {
  it("renders the search input with its accessible label and placeholder", () => {
    render(
      <SearchAndCategoryFilter
        searchValue=""
        onSearchChange={() => {}}
        searchLabel="搜尋服務名稱"
        searchPlaceholder="搜尋服務名稱"
        categoryGroupLabel="服務種類篩選"
        categories={CATEGORIES}
        activeCategory="all"
        onCategoryChange={() => {}}
      />,
    );
    expect(screen.getByLabelText("搜尋服務名稱")).toBeInTheDocument();
  });

  it("calls onSearchChange as the user types", async () => {
    const user = userEvent.setup();
    const onSearchChange = vi.fn();
    render(
      <SearchAndCategoryFilter
        searchValue=""
        onSearchChange={onSearchChange}
        searchLabel="搜尋服務名稱"
        searchPlaceholder="搜尋服務名稱"
        categoryGroupLabel="服務種類篩選"
        categories={CATEGORIES}
        activeCategory="all"
        onCategoryChange={() => {}}
      />,
    );
    await user.type(screen.getByLabelText("搜尋服務名稱"), "清");
    expect(onSearchChange).toHaveBeenCalledWith("清");
  });

  it("renders one chip per category with its count and marks the active one pressed", () => {
    render(
      <SearchAndCategoryFilter
        searchValue=""
        onSearchChange={() => {}}
        searchLabel="搜尋服務名稱"
        searchPlaceholder="搜尋服務名稱"
        categoryGroupLabel="服務種類篩選"
        categories={CATEGORIES}
        activeCategory="居家清潔"
        onCategoryChange={() => {}}
      />,
    );
    const allChip = screen.getByRole("button", { name: /全部/ });
    const cleaningChip = screen.getByRole("button", { name: /居家清潔/ });
    expect(allChip).toHaveAttribute("aria-pressed", "false");
    expect(cleaningChip).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByText("2")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("calls onCategoryChange with the clicked category id", async () => {
    const user = userEvent.setup();
    const onCategoryChange = vi.fn();
    render(
      <SearchAndCategoryFilter
        searchValue=""
        onSearchChange={() => {}}
        searchLabel="搜尋服務名稱"
        searchPlaceholder="搜尋服務名稱"
        categoryGroupLabel="服務種類篩選"
        categories={CATEGORIES}
        activeCategory="all"
        onCategoryChange={onCategoryChange}
      />,
    );
    await user.click(screen.getByRole("button", { name: /水電修繕/ }));
    expect(onCategoryChange).toHaveBeenCalledWith("水電修繕");
  });

  it("keeps every chip at an accessible minimum touch target height", () => {
    render(
      <SearchAndCategoryFilter
        searchValue=""
        onSearchChange={() => {}}
        searchLabel="搜尋服務名稱"
        searchPlaceholder="搜尋服務名稱"
        categoryGroupLabel="服務種類篩選"
        categories={CATEGORIES}
        activeCategory="all"
        onCategoryChange={() => {}}
      />,
    );
    for (const button of screen.getAllByRole("button")) {
      expect(button.className).toContain("min-h-[44px]");
    }
  });
});
