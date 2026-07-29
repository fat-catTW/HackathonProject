import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { RestaurantCard } from "./RestaurantCard";

const restaurant = {
  id: "r001",
  name: "22世紀風味館 信義旗艦店",
  brand: "22世紀風味館",
  address: "台北市信義區松高路12號3樓",
  phone: "02-2723-0022",
  cuisine: "複合式料理",
  supports_booking_api: true,
};

describe("RestaurantCard", () => {
  it("renders name, address, and phone", () => {
    render(<RestaurantCard restaurant={restaurant} selected={false} onSelect={() => {}} />);
    expect(screen.getByText(restaurant.name)).toBeInTheDocument();
    expect(screen.getByText(restaurant.address)).toBeInTheDocument();
    expect(screen.getByText(restaurant.phone)).toBeInTheDocument();
  });

  it("calls onSelect when clicked", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(<RestaurantCard restaurant={restaurant} selected={false} onSelect={onSelect} />);
    await user.click(screen.getByRole("button"));
    expect(onSelect).toHaveBeenCalledTimes(1);
  });

  it("shows a selected visual state via aria-pressed", () => {
    render(<RestaurantCard restaurant={restaurant} selected onSelect={() => {}} />);
    expect(screen.getByRole("button")).toHaveAttribute("aria-pressed", "true");
  });
});
