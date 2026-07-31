import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import type { RequestListItem } from "../types/request";
import { RequestCard } from "./RequestCard";

const BASE: RequestListItem = {
  request_id: "REQ-20260731-173CAB",
  service_name: "冷氣清洗",
  status: "SUBMITTED",
  status_label: "等待廠商確認",
  created_at: "2026-07-31T20:47:05+08:00",
  updated_at: "2026-07-31T20:47:05+08:00",
};

function renderCard(item: RequestListItem) {
  return render(
    <MemoryRouter>
      <RequestCard item={item} />
    </MemoryRouter>,
  );
}

describe("RequestCard", () => {
  it("一律顯示建立時間，住戶才認得出是哪一筆", () => {
    renderCard(BASE);
    expect(screen.getByText(/建立 7\/31 下午08:47/)).toBeInTheDocument();
  });

  it("案件還沒有進展時不顯示更新時間", () => {
    renderCard(BASE);
    expect(screen.queryByText(/更新/)).not.toBeInTheDocument();
  });

  it("廠商接單後同時看得到建立與更新時間", () => {
    // 實際踩到的情境：卡片以前只顯示 updated_at，接單後時間從 08:47 跳成 09:36，
    // 住戶照著建立時間找就以為案件消失了。
    renderCard({
      ...BASE,
      status: "CONFIRMED",
      status_label: "已確認",
      updated_at: "2026-07-31T21:36:20+08:00",
    });
    expect(screen.getByText(/建立 7\/31 下午08:47/)).toBeInTheDocument();
    expect(screen.getByText(/更新 7\/31 下午09:36/)).toBeInTheDocument();
  });
});
