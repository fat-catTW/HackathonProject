import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { TaskCardList } from "./TaskCardList";

describe("TaskCardList", () => {
  it("renders one card per task with its service name", () => {
    render(
      <TaskCardList
        cards={[
          { service_id: "quick_purchase", service_name: "快速下單" },
          { service_id: "home_cleaning", service_name: "居家清潔" },
        ]}
      />,
    );

    expect(screen.getByText("快速下單")).toBeInTheDocument();
    expect(screen.getByText("居家清潔")).toBeInTheDocument();
  });
});
