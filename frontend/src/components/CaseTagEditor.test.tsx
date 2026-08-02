import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../api/client";

vi.mock("../api/vendorTags", () => ({
  saveVendorCaseTags: vi.fn(),
  getVendorCaseTags: vi.fn(),
  listVendorCaseTags: vi.fn(),
}));

import { CaseTagEditor } from "./CaseTagEditor";
import { saveVendorCaseTags } from "../api/vendorTags";

const REQUEST_ID = "REQ-20260802-001";

/** 標籤的真實來源是後端回傳值，用一個持有 state 的殼模擬明細頁的用法。 */
function Host({ initial = [] as string[] }) {
  const [tags, setTags] = useState(initial);
  return <CaseTagEditor requestId={REQUEST_ID} tags={tags} onTagsChange={setTags} />;
}

/** 讓存檔照單全收，回傳送進來的那份清單。 */
function acceptSave() {
  vi.mocked(saveVendorCaseTags).mockImplementation(async (requestId, tags) => ({
    success: true as const,
    request_id: requestId,
    tags,
  }));
}

beforeEach(() => {
  vi.mocked(saveVendorCaseTags).mockReset();
  acceptSave();
});

describe("CaseTagEditor", () => {
  it("貼上常用標籤時送出整份清單，並顯示後端存下來的結果", async () => {
    const user = userEvent.setup();
    render(<Host initial={["待報價"]} />);

    await user.click(screen.getByRole("button", { name: "＋ 急件" }));

    expect(saveVendorCaseTags).toHaveBeenCalledWith(REQUEST_ID, ["待報價", "急件"]);
    expect(await screen.findByRole("button", { name: "移除標籤「急件」" })).toBeInTheDocument();
    // 貼過的預設標籤不再出現在快捷區。
    expect(screen.queryByRole("button", { name: "＋ 急件" })).not.toBeInTheDocument();
  });

  it("移除標籤時送出剩下的清單", async () => {
    const user = userEvent.setup();
    render(<Host initial={["急件", "待報價"]} />);

    await user.click(screen.getByRole("button", { name: "移除標籤「急件」" }));

    expect(saveVendorCaseTags).toHaveBeenCalledWith(REQUEST_ID, ["待報價"]);
    expect(await screen.findByRole("button", { name: "＋ 急件" })).toBeInTheDocument();
  });

  it("可以自己打一個標籤，送出前先去掉前後空白", async () => {
    const user = userEvent.setup();
    render(<Host />);

    await user.type(screen.getByLabelText("自定義標籤"), "  要帶梯子 ");
    await user.click(screen.getByRole("button", { name: "新增標籤" }));

    expect(saveVendorCaseTags).toHaveBeenCalledWith(REQUEST_ID, ["要帶梯子"]);
    expect(await screen.findByRole("button", { name: "移除標籤「要帶梯子」" })).toBeInTheDocument();
  });

  it("重複的標籤不送出，直接告訴使用者已經貼過了", async () => {
    const user = userEvent.setup();
    render(<Host initial={["急件"]} />);

    await user.type(screen.getByLabelText("自定義標籤"), "急件");
    await user.click(screen.getByRole("button", { name: "新增標籤" }));

    expect(saveVendorCaseTags).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent("已經貼上了");
  });

  it("貼滿之後擋下再貼，不用等後端退回來", async () => {
    const user = userEvent.setup();
    render(<Host initial={["一", "二", "三", "四", "五", "六"]} />);

    await user.type(screen.getByLabelText("自定義標籤"), "七");
    await user.click(screen.getByRole("button", { name: "新增標籤" }));

    expect(saveVendorCaseTags).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent("最多只能貼 6 個標籤");
  });

  it("存檔失敗時顯示後端的訊息，畫面上的標籤維持原樣", async () => {
    const user = userEvent.setup();
    vi.mocked(saveVendorCaseTags).mockRejectedValue(
      new ApiError("TAG_TOO_LONG", "標籤「這個標籤有夠長」太長了，最多 10 個字。"),
    );
    render(<Host initial={["急件"]} />);

    await user.click(screen.getByRole("button", { name: "移除標籤「急件」" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("太長了");
    expect(screen.getByRole("button", { name: "移除標籤「急件」" })).toBeInTheDocument();
  });
});
