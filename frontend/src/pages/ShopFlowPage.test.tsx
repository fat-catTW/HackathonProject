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
  {
    id: "prod_b",
    store_id: "store_b",
    store_name: "B 店家",
    category_id: "cat_beverage",
    name: "商品 B",
    description: "描述 B",
    product_type: "SERIAL_CODE" as const,
    image: null,
    specs: [],
    skus: [{ sku_id: "sku_b", attributes: {}, unit_price: 80, unit_points: 8 }],
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

  it("groups cart items by vendor", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByText("飲品兌換"));

    await user.click(await screen.findByText("商品 A"));
    await user.click(screen.getByText("加入購物車（NT$50）"));

    await user.click(screen.getByText("商品 B"));
    await user.click(screen.getByText("加入購物車（NT$80）"));

    await user.click(screen.getByText(/前往購物車/));

    expect(await screen.findByText("A 店家")).toBeInTheDocument();
    expect(screen.getByText("B 店家")).toBeInTheDocument();
  });
});
