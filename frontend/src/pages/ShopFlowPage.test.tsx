import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { ShopFlowPage } from "./ShopFlowPage";
import * as shopApi from "../api/shop";

vi.mock("../api/shop");

const categories = [
  { id: "cat_beverage", name: "飲品兌換" },
  { id: "cat_daily", name: "生活日用品" },
];

const products = [
  {
    id: "prod_a",
    store_id: "store_a",
    store_name: "A 店家",
    category_id: "cat_beverage",
    name: "商品 A",
    description: "描述 A",
    product_type: "SERIAL_CODE" as const,
    image: null,
    specs: [],
    skus: [{ sku_id: "sku_a", attributes: {}, unit_price: 50, unit_points: 5 }],
  },
];

function renderPage() {
  return render(
    <MemoryRouter>
      <ShopFlowPage />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.mocked(shopApi.listShopCategories).mockResolvedValue({ categories });
  vi.mocked(shopApi.listShopProducts).mockResolvedValue({ products });
  vi.mocked(shopApi.getShopPoints).mockResolvedValue({ balance: 0 });
});

describe("ShopFlowPage", () => {
  it("shows categories first, then fetches products for the selected category", async () => {
    const user = userEvent.setup();
    renderPage();

    expect(await screen.findByText("飲品兌換")).toBeInTheDocument();
    expect(screen.getByText("生活日用品")).toBeInTheDocument();
    expect(shopApi.listShopProducts).not.toHaveBeenCalled();

    await user.click(screen.getByText("飲品兌換"));

    expect(await screen.findByText("商品 A")).toBeInTheDocument();
    expect(shopApi.listShopProducts).toHaveBeenCalledWith("cat_beverage");
  });

  it("shows the vendor name on each product card", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByText("飲品兌換"));

    expect(await screen.findByText("商品 A")).toBeInTheDocument();
    expect(screen.getByText("A 店家")).toBeInTheDocument();
  });
});
