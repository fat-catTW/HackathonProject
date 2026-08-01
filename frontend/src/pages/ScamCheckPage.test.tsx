import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { ScamCheckPage } from "./ScamCheckPage";
import * as scamApi from "../api/scamCheck";

describe("ScamCheckPage", () => {
  it("submits the pasted message and shows the classification result", async () => {
    vi.spyOn(scamApi, "checkScamMessage").mockResolvedValue({
      category: "投資詐騙",
      explanation: "請勿匯款，先跟家人確認。",
    });

    render(
      <MemoryRouter>
        <ScamCheckPage />
      </MemoryRouter>,
    );

    fireEvent.change(screen.getByLabelText("貼上可疑訊息"), { target: { value: "老師說穩賺不賠" } });
    fireEvent.click(screen.getByRole("button", { name: "幫我看看" }));

    await waitFor(() => expect(screen.getByText("投資詐騙")).toBeInTheDocument());
    expect(screen.getByText("請勿匯款，先跟家人確認。")).toBeInTheDocument();
  });
});
