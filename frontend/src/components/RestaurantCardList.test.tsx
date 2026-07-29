import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { RestaurantCardList } from "./RestaurantCardList";

const restaurants = [
  { id: "r001", name: "餐廳一", brand: "b", address: "地址一", phone: "02-1", cuisine: "c", supports_booking_api: true },
  { id: "r002", name: "餐廳二", brand: "b", address: "地址二", phone: "02-2", cuisine: "c", supports_booking_api: true },
];

describe("RestaurantCardList", () => {
  it("renders one card per restaurant plus a 'need help' option", () => {
    render(<RestaurantCardList restaurants={restaurants} selectedId={null} onSelect={() => {}} onNeedHelp={() => {}} />);
    expect(screen.getByText("餐廳一")).toBeInTheDocument();
    expect(screen.getByText("餐廳二")).toBeInTheDocument();
    expect(screen.getByText("客服協助媒合")).toBeInTheDocument();
  });

  it("calls onSelect with the restaurant id", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(<RestaurantCardList restaurants={restaurants} selectedId={null} onSelect={onSelect} onNeedHelp={() => {}} />);
    await user.click(screen.getByText("餐廳一"));
    expect(onSelect).toHaveBeenCalledWith("r001");
  });

  it("calls onNeedHelp when the concierge option is clicked", async () => {
    const user = userEvent.setup();
    const onNeedHelp = vi.fn();
    render(<RestaurantCardList restaurants={restaurants} selectedId={null} onSelect={() => {}} onNeedHelp={onNeedHelp} />);
    await user.click(screen.getByText("客服協助媒合"));
    expect(onNeedHelp).toHaveBeenCalledTimes(1);
  });
});
