import type { CaseTagMap, VendorCaseTags } from "../types/vendor";
import { vendorApi } from "./client";

/**
 * 廠商案件標籤。三種後台（一般服務／外送／商城）共用這一組端點——貼標籤對三邊
 * 是同一件事，後端靠 VENDOR# 索引確認案件歸屬，不分服務線。
 */

/** 這家廠商所有案件的標籤：`{案件編號: [標籤…]}`，沒貼過的案件不會出現。 */
export function listVendorCaseTags() {
  return vendorApi<{ tags: CaseTagMap }>("/api/vendor/case-tags");
}

export function getVendorCaseTags(requestId: string) {
  return vendorApi<VendorCaseTags>(`/api/vendor/case-tags/${requestId}`);
}

/**
 * 整組覆寫這張單的標籤，回傳後端實際存下來的樣子（已去空白、去重）。
 *
 * 標籤存在廠商自己的分區，不寫進案件本體：貼標籤不會推進案件版本，也就不會讓
 * 後台另一個分頁按接單時被樂觀鎖擋下。
 */
export function saveVendorCaseTags(requestId: string, tags: string[]) {
  return vendorApi<{ success: true } & VendorCaseTags>(`/api/vendor/case-tags/${requestId}`, {
    method: "PUT",
    body: JSON.stringify({ tags }),
  });
}
