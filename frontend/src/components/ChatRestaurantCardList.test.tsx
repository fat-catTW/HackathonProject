import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ChatRestaurantCardList } from "./ChatRestaurantCardList";

const RESTAURANTS = [
  { id: "r001", name: "22世紀風味館 信義旗艦店", address: "台北市信義區松高路12號3樓", phone: "02-2723-0022" },
  { id: "ChIJ-fake", name: "台中好料理", address: "台中市西區某路1號", phone: "", reason: "評價很高" },
];

describe("ChatRestaurantCardList", () => {
  it("renders one card per restaurant with name and address", () => {
    render(<ChatRestaurantCardList restaurants={RESTAURANTS} onSelect={() => {}} />);

    expect(screen.getByText("22世紀風味館 信義旗艦店")).toBeInTheDocument();
    expect(screen.getByText("台中好料理")).toBeInTheDocument();
    expect(screen.getByText("台北市信義區松高路12號3樓")).toBeInTheDocument();
    expect(screen.getByText("評價很高")).toBeInTheDocument();
  });

  it("calls onSelect with the restaurant's name when its card is tapped", () => {
    const onSelect = vi.fn();
    render(<ChatRestaurantCardList restaurants={RESTAURANTS} onSelect={onSelect} />);

    fireEvent.click(screen.getByText("台中好料理"));

    expect(onSelect).toHaveBeenCalledWith("台中好料理");
  });

  it("does not render a phone row when phone is empty", () => {
    render(<ChatRestaurantCardList restaurants={[RESTAURANTS[1]]} onSelect={() => {}} />);
    expect(screen.queryByText("02-2723-0022")).not.toBeInTheDocument();
  });
});
