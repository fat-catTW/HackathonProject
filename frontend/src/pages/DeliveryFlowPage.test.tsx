import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { DeliveryFlowPage } from "./DeliveryFlowPage";
import * as deliveryApi from "../api/delivery";

vi.mock("../api/delivery");

const stores = [
  {
    id: "store-1",
    name: "測試店家",
    address: "台北市大安區忠孝東路四段100號",
    cuisine: "便當",
    image: null,
  },
];

function renderPage() {
  return render(
    <MemoryRouter>
      <DeliveryFlowPage />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.mocked(deliveryApi.listDeliveryStores).mockResolvedValue(stores);
  vi.mocked(deliveryApi.getDeliveryStore).mockResolvedValue({
    ...stores[0],
    url: "https://example.com/store-1",
    menu: [],
  });
  vi.mocked(deliveryApi.submitDeliveryOrder).mockResolvedValue({
    success: true,
    request_id: "req-1",
    order_status: "01",
    total_amount: 60,
  });
  vi.mocked(deliveryApi.getDeliveryOrder).mockResolvedValue({
    request_id: "req-1",
    status: "processing",
    order_status: "01",
    order_status_label: "待接單",
    order_items: {
      user: {
        address: {
          lat: 25.033,
          lng: 121.565,
          city: "台北市",
          area: "大安區",
          street: "忠孝東路四段100號",
          remark: "",
          contact_name: "王小明",
          phone: "0912345678",
        },
      },
      goods: [],
      store: {
        id: "store-1",
        name: "測試店家",
        address: "台北市大安區忠孝東路四段100號",
        url: "https://example.com/store-1",
      },
      note: "",
    },
    original_amount: 0,
    shipping_fee_amount: 60,
    total_amount: 60,
    vendor_data: {
      delivery: null,
      order_status: null,
    },
    cancel_reason: null,
    created_at: "2026-07-30T00:00:00Z",
  });
});

describe("DeliveryFlowPage", () => {
  it("updates district options when the county changes", async () => {
    const user = userEvent.setup();
    renderPage();

    const countySelect = await screen.findByLabelText("縣市");
    const districtSelect = screen.getByLabelText("鄉鎮市區");

    expect(districtSelect).toBeDisabled();

    await user.selectOptions(countySelect, "台北市");
    expect(districtSelect).toBeEnabled();
    expect(screen.getByRole("option", { name: "大安區" })).toBeInTheDocument();

    await user.selectOptions(districtSelect, "大安區");
    expect(districtSelect).toHaveValue("大安區");

    await user.selectOptions(countySelect, "高雄市");
    expect(districtSelect).toHaveValue("");
    expect(screen.getByRole("option", { name: "前鎮區" })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: "大安區" })).not.toBeInTheDocument();
  });
});
