"""廠商替案件貼的自訂標籤（急件／大型案件／待報價…）的正規化規則。

標籤是廠商自己打的字，不是固定選單——前端提供幾個常用的快捷選項，但廠商想打
「要帶梯子」也應該存得進去。因此這裡只管會讓清單變難用的三件事：空白、重複、
太長，其餘內容一律照收。

正規化與驗證放在 API 層之外，是為了讓「存進去的樣子」跟「回傳的樣子」由同一段
程式決定：後端存的就是去空白、去重後的清單，前端不必再猜自己送出的字串會被怎麼
處理。
"""

# 一張單掛超過幾個標籤，清單上就擠不下、也失去分類的意義了。
MAX_TAGS = 6
# 標籤是給人在清單上掃視的短詞，不是備註欄。
MAX_TAG_LENGTH = 10


class TagError(ValueError):
    """標籤內容不合規；code 給前端判斷，message 直接顯示給廠商看。"""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def normalize_tags(raw: list[str]) -> list[str]:
    """去頭尾空白、丟掉空字串、保序去重，並檢查長度與數量。

    保序而不排序：廠商按下的順序就是他心裡的優先順序，重排會讓「急件」跑到後面。
    """
    cleaned: list[str] = []
    for value in raw:
        tag = str(value).strip()
        if not tag:
            continue
        if len(tag) > MAX_TAG_LENGTH:
            raise TagError("TAG_TOO_LONG", f"標籤「{tag}」太長了，最多 {MAX_TAG_LENGTH} 個字。")
        if tag not in cleaned:
            cleaned.append(tag)
    if len(cleaned) > MAX_TAGS:
        raise TagError("TOO_MANY_TAGS", f"一張單最多只能貼 {MAX_TAGS} 個標籤。")
    return cleaned
