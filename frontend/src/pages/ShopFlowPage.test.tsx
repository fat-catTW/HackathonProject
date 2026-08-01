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
    compare_group_id: null,
    name: "商品 A",
    description: "描述 A",
    product_type: "SERIAL_CODE" as const,
    image: null,
    specs: [],
    skus: [{ sku_id: "sku_a", attributes: {}, unit_price: 50, unit_points: 5 }],
    rating_avg: 4.5,
    rating_count: 10,
  },
  {
    id: "prod_b",
    store_id: "store_b",
    store_name: "B 店家",
    category_id: "cat_beverage",
    compare_group_id: null,
    name: "商品 B",
    description: "描述 B",
    product_type: "SERIAL_CODE" as const,
    image: null,
    specs: [],
    skus: [{ sku_id: "sku_b", attributes: {}, unit_price: 80, unit_points: 8 }],
    rating_avg: 4.0,
    rating_count: 5,
  },
];

const dailyProducts = [
  {
    id: "prod_c",
    store_id: "store_c",
    store_name: "C 店家",
    category_id: "cat_daily",
    compare_group_id: null,
    name: "商品 C",
    description: "描述 C",
    product_type: "PHYSICAL" as const,
    image: null,
    specs: [],
    skus: [{ sku_id: "sku_c", attributes: {}, unit_price: 100, unit_points: 10 }],
    rating_avg: 4.8,
    rating_count: 20,
  },
];

function renderPage() {
  return render(
    <MemoryRouter>
      <ShopFlowPage />
    </MemoryRouter>,
  );
}

function renderPageAtRoute(route: string) {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <ShopFlowPage />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(shopApi.listShopCategories).mockResolvedValue({ categories });
  vi.mocked(shopApi.listShopProducts).mockResolvedValue({ products });
  vi.mocked(shopApi.getShopPoints).mockResolvedValue({ balance: 0 });
  vi.mocked(shopApi.getShopProductReviews).mockResolvedValue({ reviews: [] });
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

  it("clears the stale product detail panel when switching to a different category", async () => {
    const user = userEvent.setup();
    vi.mocked(shopApi.listShopProducts)
      .mockResolvedValueOnce({ products })
      .mockResolvedValueOnce({ products: dailyProducts });
    renderPage();

    await user.click(await screen.findByText("飲品兌換"));
    await user.click(await screen.findByText("商品 A"));
    expect(await screen.findByText("加入購物車（NT$50）")).toBeInTheDocument();

    await user.click(screen.getByText("返回選品類"));
    await user.click(await screen.findByText("生活日用品"));

    expect(await screen.findByText("商品 C")).toBeInTheDocument();
    expect(screen.queryByText(/加入購物車/)).not.toBeInTheDocument();
  });

  const comparableProducts = [
    {
      id: "prod_x1",
      store_id: "store_x1",
      store_name: "X1 店家",
      category_id: "cat_daily",
      compare_group_id: "cmp_x",
      name: "比價商品",
      description: "描述 X",
      product_type: "PHYSICAL" as const,
      image: null,
      specs: [],
      skus: [{ sku_id: "sku_x1", attributes: {}, unit_price: 100, unit_points: 10 }],
      rating_avg: 3.5,
      rating_count: 8,
    },
    {
      id: "prod_x2",
      store_id: "store_x2",
      store_name: "X2 店家",
      category_id: "cat_daily",
      compare_group_id: "cmp_x",
      name: "比價商品",
      description: "描述 X",
      product_type: "PHYSICAL" as const,
      image: null,
      specs: [],
      skus: [{ sku_id: "sku_x2", attributes: {}, unit_price: 80, unit_points: 8 }],
      rating_avg: 4.9,
      rating_count: 30,
    },
  ];

  const sortableProducts = [
    {
      id: "prod_low",
      store_id: "store_low",
      store_name: "Low 店家",
      category_id: "cat_daily",
      compare_group_id: null,
      name: "評分較低商品",
      description: "描述 Low",
      product_type: "SERIAL_CODE" as const,
      image: null,
      specs: [],
      skus: [{ sku_id: "sku_low", attributes: {}, unit_price: 50, unit_points: 5 }],
      rating_avg: 3.0,
      rating_count: 4,
    },
    {
      id: "prod_high",
      store_id: "store_high",
      store_name: "High 店家",
      category_id: "cat_daily",
      compare_group_id: null,
      name: "評分較高商品",
      description: "描述 High",
      product_type: "SERIAL_CODE" as const,
      image: null,
      specs: [],
      skus: [{ sku_id: "sku_high", attributes: {}, unit_price: 60, unit_points: 6 }],
      rating_avg: 4.9,
      rating_count: 40,
    },
  ];

  it("combines identical products from different vendors into one comparison card", async () => {
    const user = userEvent.setup();
    vi.mocked(shopApi.listShopProducts).mockResolvedValue({ products: comparableProducts });
    renderPage();

    await user.click(await screen.findByText("飲品兌換"));

    expect(await screen.findByText("比價商品")).toBeInTheDocument();
    expect(screen.getByText("NT$80~100")).toBeInTheDocument();
    expect(screen.getByText("共 2 家店販售")).toBeInTheDocument();
    expect(screen.queryByText("X1 店家")).not.toBeInTheDocument();
  });

  it("opens a per-vendor price list when a comparison card is clicked, cheapest offer first", async () => {
    const user = userEvent.setup();
    vi.mocked(shopApi.listShopProducts).mockResolvedValue({ products: comparableProducts });
    renderPage();

    await user.click(await screen.findByText("飲品兌換"));
    await user.click(await screen.findByText("比價商品"));

    const offerRows = await screen.findAllByText(/店家/);
    expect(offerRows.length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText("X2 店家")).toBeInTheDocument();
    expect(screen.getByText("X1 店家")).toBeInTheDocument();
    expect(screen.getByText("最便宜")).toBeInTheDocument();
  });

  it("selecting a vendor from the comparison list opens the normal add-to-cart panel", async () => {
    const user = userEvent.setup();
    vi.mocked(shopApi.listShopProducts).mockResolvedValue({ products: comparableProducts });
    renderPage();

    await user.click(await screen.findByText("飲品兌換"));
    await user.click(await screen.findByText("比價商品"));

    const selectButtons = await screen.findAllByText("選這家");
    await user.click(selectButtons[0]);

    expect(await screen.findByText("加入購物車（NT$80）")).toBeInTheDocument();
  });

  it("opens directly to the comparison list when the URL has a compare param", async () => {
    vi.mocked(shopApi.getShopCompareGroup).mockResolvedValue({
      group_id: "cmp_x",
      category_id: "cat_daily",
      offers: comparableProducts.map((p) => ({ ...p, min_unit_price: p.skus[0].unit_price })),
    });
    vi.mocked(shopApi.listShopProducts).mockResolvedValue({ products: comparableProducts });

    renderPageAtRoute("/services/shop_purchase?compare=cmp_x");

    expect(await screen.findByText("X2 店家")).toBeInTheDocument();
    expect(screen.getByText("X1 店家")).toBeInTheDocument();
    expect(screen.getByText("最便宜")).toBeInTheDocument();
    expect(screen.queryByText("請選擇商品類型")).not.toBeInTheDocument();
  });

  it("shows a toast and doesn't crash when the compare deep link fails to load", async () => {
    vi.mocked(shopApi.getShopCompareGroup).mockRejectedValue(new Error("network error"));

    renderPageAtRoute("/services/shop_purchase?compare=cmp_x");

    expect(await screen.findByText("比價資料載入失敗")).toBeInTheDocument();
  });

  it("shows the rating on each product card", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByText("飲品兌換"));

    expect(await screen.findByText(/4\.5/)).toBeInTheDocument();
  });

  it("sorts product cards by rating, highest first, when the sort toggle is on", async () => {
    const user = userEvent.setup();
    vi.mocked(shopApi.listShopProducts).mockResolvedValue({ products: sortableProducts });
    renderPage();

    await user.click(await screen.findByText("飲品兌換"));
    await screen.findByText("評分較低商品");

    const beforeOrder = screen.getAllByText(/評分較(低|高)商品/).map((el) => el.textContent);
    expect(beforeOrder).toEqual(["評分較低商品", "評分較高商品"]); // default order matches API response order

    await user.click(screen.getByText("依評分排序"));

    const afterOrder = screen.getAllByText(/評分較(低|高)商品/).map((el) => el.textContent);
    expect(afterOrder).toEqual(["評分較高商品", "評分較低商品"]); // now sorted highest-rated first
  });

  it("shows reviews when the review panel is expanded", async () => {
    const user = userEvent.setup();
    vi.mocked(shopApi.getShopProductReviews).mockResolvedValue({
      reviews: [
        {
          review_id: "rev_1",
          author: "小明",
          rating: 5,
          comment: "很好用！",
          created_at: "2026-05-01",
          verified_purchase: true,
        },
      ],
    });
    renderPage();

    await user.click(await screen.findByText("飲品兌換"));
    await user.click(await screen.findByText("商品 A"));
    await user.click(screen.getByText("查看評價"));

    expect(await screen.findByText("很好用！")).toBeInTheDocument();
    expect(screen.getByText("小明")).toBeInTheDocument();
    expect(shopApi.getShopProductReviews).toHaveBeenCalledWith("prod_a");
  });

  it("does not fetch reviews until the review panel is opened", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByText("飲品兌換"));
    await user.click(await screen.findByText("商品 A"));

    expect(shopApi.getShopProductReviews).not.toHaveBeenCalled();
  });

  it("opens directly to the product list for a category when the URL has a category_id param", async () => {
    vi.mocked(shopApi.listShopProducts).mockResolvedValue({ products: dailyProducts });

    renderPageAtRoute("/services/shop_purchase?category_id=cat_daily");

    expect(await screen.findByText("商品 C")).toBeInTheDocument();
    expect(shopApi.listShopProducts).toHaveBeenCalledWith("cat_daily");
    expect(screen.queryByText("請選擇商品類型")).not.toBeInTheDocument();
  });
});
