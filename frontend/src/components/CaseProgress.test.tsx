import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { RequestProgressStep } from "../types/request";
import { CaseProgress } from "./CaseProgress";

function step(
  status: string,
  label: string,
  done: boolean,
  at = "",
): RequestProgressStep {
  return { status, label, done, at };
}

const QUOTED_CASE: RequestProgressStep[] = [
  step("SUBMITTED", "已送出需求", true, "2026-08-01T09:00:00+08:00"),
  step("CONFIRMED", "廠商已接單", true, "2026-08-01T10:00:00+08:00"),
  step("CONTACTED", "已聯繫", true, "2026-08-01T11:00:00+08:00"),
  step("QUOTED", "已報價", true, "2026-08-01T12:00:00+08:00"),
  step("IN_PROGRESS", "施工中", false),
  step("COMPLETED", "已完成", false),
];

describe("CaseProgress", () => {
  it("把還沒走到的關卡也列出來，住戶看得到接下來還有什麼", () => {
    render(<CaseProgress steps={QUOTED_CASE} />);

    const items = screen.getAllByRole("listitem");
    expect(items.map((li) => within(li).getAllByText(/./)[0].textContent)).toEqual([
      "已送出需求",
      "廠商已接單",
      "已聯繫",
      "已報價",
      "施工中",
      "已完成",
    ]);
  });

  it("最後一個完成的關卡標成「目前進度」", () => {
    render(<CaseProgress steps={QUOTED_CASE} />);

    const marks = screen.getAllByText("目前進度");
    expect(marks).toHaveLength(1);
    // 目前進度掛在「已報價」那一格，不是最後一格
    expect(within(marks[0].closest("li")!).getByText("已報價")).toBeInTheDocument();
  });

  it("走過的關卡顯示完成時間，還沒走到的不顯示", () => {
    render(<CaseProgress steps={QUOTED_CASE} />);

    const done = screen.getByText("已聯繫").closest("li")!;
    expect(within(done).getByText(/8\/1/)).toBeInTheDocument();

    const pending = screen.getByText("施工中").closest("li")!;
    expect(within(pending).queryByText(/8\/1/)).not.toBeInTheDocument();
  });

  it("有報價時把金額寫在「已報價」那一格底下", () => {
    render(<CaseProgress steps={QUOTED_CASE} quoteAmount={3200} />);

    const quoted = screen.getByText("已報價").closest("li")!;
    expect(within(quoted).getByText("NT$3,200")).toBeInTheDocument();
  });

  it("還沒報價就不顯示金額，即使欄位帶了值", () => {
    const beforeQuote = QUOTED_CASE.map((s) =>
      s.status === "QUOTED" ? { ...s, done: false, at: "" } : s,
    );
    render(<CaseProgress steps={beforeQuote} quoteAmount={3200} />);

    expect(screen.queryByText("NT$3,200")).not.toBeInTheDocument();
  });

  it("不報價的服務不會出現已聯繫／已報價兩格", () => {
    render(
      <CaseProgress
        steps={[
          step("SUBMITTED", "已送出需求", true, "2026-08-01T09:00:00+08:00"),
          step("CONFIRMED", "廠商已接單", true, "2026-08-01T10:00:00+08:00"),
          step("IN_PROGRESS", "施工中", false),
          step("COMPLETED", "已完成", false),
        ]}
      />,
    );

    expect(screen.queryByText("已聯繫")).not.toBeInTheDocument();
    expect(screen.queryByText("已報價")).not.toBeInTheDocument();
  });

  it("中止的案件把中止那一格接在最後", () => {
    render(
      <CaseProgress
        steps={[
          step("SUBMITTED", "已送出需求", true, "2026-08-01T09:00:00+08:00"),
          step("CONFIRMED", "廠商已接單", true, "2026-08-01T10:00:00+08:00"),
          step("CONTACTED", "已聯繫", false),
          step("QUOTED", "已報價", false),
          step("IN_PROGRESS", "施工中", false),
          step("COMPLETED", "已完成", false),
          step("CANCELLED", "已取消", true, "2026-08-01T11:00:00+08:00"),
        ]}
      />,
    );

    const items = screen.getAllByRole("listitem");
    expect(within(items[items.length - 1]).getByText("已取消")).toBeInTheDocument();
    expect(within(items[items.length - 1]).getByText("目前進度")).toBeInTheDocument();
  });

  it("拿不到進度時整塊不顯示，而不是畫一個空殼", () => {
    // 部署交界期間的舊回應沒有 progress 欄位，頁面其他部分要照常運作。
    const { container } = render(<CaseProgress steps={[]} />);
    expect(container).toBeEmptyDOMElement();
  });
});
