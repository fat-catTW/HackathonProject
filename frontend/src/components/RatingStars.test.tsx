import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RatingStars } from "./RatingStars";

describe("RatingStars", () => {
  it("renders the numeric rating and review count", () => {
    render(<RatingStars rating={4.6} count={128} />);
    expect(screen.getByText(/4\.6/)).toBeInTheDocument();
    expect(screen.getByText(/128/)).toBeInTheDocument();
  });

  it("renders without a count when count is omitted", () => {
    render(<RatingStars rating={5} />);
    expect(screen.getByText(/5\.0/)).toBeInTheDocument();
    expect(screen.queryByText(/（/)).not.toBeInTheDocument();
  });

  it("renders without a count when count is zero", () => {
    render(<RatingStars rating={0} count={0} />);
    expect(screen.queryByText(/（/)).not.toBeInTheDocument();
  });
});
