import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { CaseUpdateModal } from "./CaseUpdateModal";
import type { CaseUpdate } from "../hooks/useCaseUpdates";

const navigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return { ...actual, useNavigate: () => navigate };
});

const CONFIRMED: CaseUpdate = {
  requestId: "REQ-1",
  serviceName: "冷氣清潔",
  status: "CONFIRMED",
};

function renderModal(update: CaseUpdate = CONFIRMED) {
  navigate.mockClear();
  const onDismiss = vi.fn();
  render(
    <MemoryRouter>
      <CaseUpdateModal update={update} onDismiss={onDismiss} />
    </MemoryRouter>,
  );
  return { onDismiss };
}

describe("CaseUpdateModal", () => {
  it("tells the resident their case was picked up, and by which service", () => {
    renderModal();

    expect(screen.getByRole("dialog", { name: "案件進度通知" })).toBeInTheDocument();
    expect(screen.getByText("有人接下你的服務了")).toBeInTheDocument();
    expect(screen.getByText("已接單")).toBeInTheDocument();
    expect(screen.getByText(/「冷氣清潔」已經有服務人員接下/)).toBeInTheDocument();
  });

  it("uses different wording when the vendor turned the case down", () => {
    renderModal({ requestId: "REQ-2", serviceName: "水電維修", status: "REJECTED" });

    expect(screen.getByText("這張單被婉拒了")).toBeInTheDocument();
    // 婉拒不能只說「被拒絕了」就沒下文，要告訴住戶下一步能做什麼。
    expect(screen.getByText(/換個時段再送一次/)).toBeInTheDocument();
  });

  it("opens the case when the resident wants to see it", async () => {
    const { onDismiss } = renderModal();

    await userEvent.click(screen.getByRole("button", { name: "查看案件" }));

    expect(navigate).toHaveBeenCalledWith("/requests/REQ-1");
    // 導頁前先關掉，否則回到案件頁時同一張卡還蓋在上面。
    expect(onDismiss).toHaveBeenCalled();
  });

  it("closes without navigating when the resident just acknowledges it", async () => {
    const { onDismiss } = renderModal();

    await userEvent.click(screen.getByRole("button", { name: "知道了" }));

    expect(onDismiss).toHaveBeenCalled();
    expect(navigate).not.toHaveBeenCalled();
  });

  it("closes when the scrim behind the card is tapped", async () => {
    const { onDismiss } = renderModal();

    await userEvent.click(screen.getByRole("button", { name: "關閉通知" }));

    expect(onDismiss).toHaveBeenCalled();
  });
});
