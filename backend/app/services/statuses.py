"""案件狀態的中文標籤，住戶端與廠商後台共用。"""

STATUS_LABELS = {
    "DRAFT": "草稿",
    "AWAITING_USER_CONFIRMATION": "等待使用者確認",
    "SUBMITTED": "等待廠商確認",
    "PENDING_PROVIDER": "等待廠商確認",
    "CONFIRMED": "已確認",
    "IN_PROGRESS": "服務進行中",
    "COMPLETED": "已完成",
    "CANCELLED": "已取消",
    "FAILED": "失敗",
}

# 廠商後台把案件分成「待處理的諮詢單」與「已接下的訂單」兩欄；未列出的狀態
# （草稿、等待使用者確認）住戶還沒送出，廠商看不到。
VENDOR_PENDING_STATUSES = ("SUBMITTED", "PENDING_PROVIDER")
VENDOR_ORDER_STATUSES = ("CONFIRMED", "IN_PROGRESS", "COMPLETED")


def status_label(status: str) -> str:
    return STATUS_LABELS.get(status, status)
