"""案件狀態的中文標籤與廠商端狀態機，住戶端與廠商後台共用。"""
from typing import NamedTuple

STATUS_LABELS = {
    "DRAFT": "草稿",
    "AWAITING_USER_CONFIRMATION": "等待使用者確認",
    "SUBMITTED": "等待廠商確認",
    "AWAITING_QUOTE": "待廠商報價",
    "PENDING_PROVIDER": "等待廠商確認",
    "CONFIRMED": "已確認",
    "IN_PROGRESS": "服務進行中",
    "COMPLETED": "已完成",
    "CANCELLED": "已取消",
    "REJECTED": "廠商已婉拒",
    "FAILED": "失敗",
    "VERIFIED": "已核銷",
}

# 廠商後台把案件分成「待處理的諮詢單」與「已接下的訂單」兩欄；未列出的狀態
# （草稿、等待使用者確認）住戶還沒送出，廠商看不到。
VENDOR_PENDING_STATUSES = ("SUBMITTED", "PENDING_PROVIDER", "AWAITING_QUOTE")
VENDOR_ORDER_STATUSES = ("CONFIRMED", "IN_PROGRESS", "COMPLETED")
# 廠商婉拒後案件就結束了，跟取消一樣不進「已接訂單」。
VENDOR_CLOSED_STATUSES = ("CANCELLED", "REJECTED", "FAILED")


class VendorTransition(NamedTuple):
    """廠商後台允許的一次狀態切換。"""

    sources: frozenset[str]
    target: str
    label: str
    # None 代表所有服務都適用；非 None 時只有列出的 service_id 能做這個動作。
    applicable_services: frozenset[str] | None = None


# 廠商端的狀態機：只有列在這裡的 (動作, 來源狀態) 組合可以切換，其餘一律 409。
# 住戶已取消、已完工、或別的廠商動作先落地時，來源狀態就對不上了。
VENDOR_TRANSITIONS: dict[str, VendorTransition] = {
    "accept": VendorTransition(frozenset(VENDOR_PENDING_STATUSES), "CONFIRMED", "接單"),
    "reject": VendorTransition(frozenset(VENDOR_PENDING_STATUSES), "REJECTED", "拒單"),
    "start": VendorTransition(frozenset({"CONFIRMED"}), "IN_PROGRESS", "開始服務"),
    "complete": VendorTransition(frozenset({"IN_PROGRESS"}), "COMPLETED", "完成服務"),
    # 核銷只有餐廳訂位有意義（現場核對已到店用餐），其餘服務完工即結案，不會變成 VERIFIED。
    "verify": VendorTransition(
        frozenset({"COMPLETED"}), "VERIFIED", "核銷", frozenset({"restaurant_reservation"})
    ),
}


def status_label(status: str) -> str:
    return STATUS_LABELS.get(status, status)
