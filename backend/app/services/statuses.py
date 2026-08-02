"""案件狀態的中文標籤與廠商端狀態機，住戶端與廠商後台共用。"""
from typing import NamedTuple

STATUS_LABELS = {
    "DRAFT": "草稿",
    "AWAITING_USER_CONFIRMATION": "等待使用者確認",
    "SUBMITTED": "等待廠商確認",
    "AWAITING_QUOTE": "待廠商報價",
    "PENDING_PROVIDER": "等待廠商確認",
    "CONFIRMED": "已確認",
    "CONTACTED": "已聯繫",
    "QUOTED": "已報價",
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
# 已聯繫／已報價是接單之後、開工之前的中間狀態，必須留在「已接訂單」這一欄——
# 漏掉的話廠商一按「已聯繫」，案件就從他自己的清單上消失了。
VENDOR_ORDER_STATUSES = ("CONFIRMED", "CONTACTED", "QUOTED", "IN_PROGRESS", "COMPLETED")
# 廠商婉拒後案件就結束了，跟取消一樣不進「已接訂單」；已核銷（餐廳訂位專屬的
# 終態）也要留在廠商看得到的範圍，否則核銷成功的當下案件就從清單消失。
VENDOR_CLOSED_STATUSES = ("CANCELLED", "REJECTED", "FAILED", "VERIFIED")

# 「先聯繫住戶約時間、報價、再施工」的到府服務：師傅得看過現場或問過狀況才知道
# 要收多少，中間這兩步是住戶最想知道進度的地方。餐廳訂位／外送／商城下單當下就
# 成交，沒有這兩步，硬塞進去只會讓進度條卡在永遠不會亮的關卡上。
QUOTING_SERVICES = frozenset(
    {
        "plumbing_repair",
        "washing_machine_cleaning",
        "air_conditioner_cleaning",
        "home_cleaning",
        "package_shipping",
    }
)


class VendorTransition(NamedTuple):
    """廠商後台允許的一次狀態切換。"""

    sources: frozenset[str]
    target: str
    label: str
    # None 代表所有服務都適用；非 None 時只有列出的 service_id 能做這個動作。
    applicable_services: frozenset[str] | None = None
    # True 代表這個動作要帶金額（目前只有報價）。
    requires_amount: bool = False


# 廠商端的狀態機：只有列在這裡的 (動作, 來源狀態) 組合可以切換，其餘一律 409。
# 住戶已取消、已完工、或別的廠商動作先落地時，來源狀態就對不上了。
#
# 這裡的排列順序就是廠商後台按鈕的排列順序（_available_actions 照著走），所以由
# 「接下來最可能按的」往後排。
#
# 動作名稱 "contacted" 而不是 "contact"：POST /requests/{id}/contact 已經被「解密
# 檢視聯絡資訊」佔走，而那條路由宣告在前面，取名 contact 會讓這個動作永遠打不到。
VENDOR_TRANSITIONS: dict[str, VendorTransition] = {
    "accept": VendorTransition(frozenset(VENDOR_PENDING_STATUSES), "CONFIRMED", "接單"),
    "reject": VendorTransition(frozenset(VENDOR_PENDING_STATUSES), "REJECTED", "拒單"),
    "contacted": VendorTransition(
        frozenset({"CONFIRMED"}), "CONTACTED", "標記已聯繫", QUOTING_SERVICES
    ),
    # 報價允許從「已確認」直接跳過來：師傅第一次打電話就在電話裡報好價是常態，
    # 不該逼他先按一次「已聯繫」再按一次「報價」。
    "quote": VendorTransition(
        frozenset({"CONFIRMED", "CONTACTED"}), "QUOTED", "報價", QUOTING_SERVICES, True
    ),
    # 開工不強制先聯繫或報價：不需要報價的服務（餐廳訂位）從已確認直接開始，需要
    # 報價的服務也可能是住戶當場口頭同意就動工。
    "start": VendorTransition(
        frozenset({"CONFIRMED", "CONTACTED", "QUOTED"}), "IN_PROGRESS", "開始服務"
    ),
    "complete": VendorTransition(frozenset({"IN_PROGRESS"}), "COMPLETED", "完成服務"),
    # 核銷只有餐廳訂位有意義（現場核對已到店用餐），其餘服務完工即結案，不會變成 VERIFIED。
    "verify": VendorTransition(
        frozenset({"COMPLETED"}), "VERIFIED", "核銷", frozenset({"restaurant_reservation"})
    ),
}

# 住戶端進度條上的關卡，依序排列。取消／婉拒／失敗不在這條線上——它們是中止，
# 會另外接在住戶走到的位置後面。
PROGRESS_CHAIN = ("SUBMITTED", "CONFIRMED", "CONTACTED", "QUOTED", "IN_PROGRESS", "COMPLETED")

# 進度條上的關卡名稱跟徽章上的狀態標籤不同：徽章講的是「現在是什麼狀態」
# （等待廠商確認），進度條講的是「這一步做完了沒」（已送出需求）。
PROGRESS_STEP_LABELS = {
    "SUBMITTED": "已送出需求",
    "CONFIRMED": "廠商已接單",
    "CONTACTED": "已聯繫",
    "QUOTED": "已報價",
    "IN_PROGRESS": "施工中",
    "COMPLETED": "已完成",
}

# 同一個關卡的別名：這些狀態在進度條上跟被指到的那一格是同一格。
PROGRESS_ALIASES = {
    "PENDING_PROVIDER": "SUBMITTED",
    "AWAITING_QUOTE": "SUBMITTED",
    "VERIFIED": "COMPLETED",
}

# 走到一半就中止的狀態；進度條會停在住戶當時走到的關卡，後面接一格中止。
PROGRESS_ABORTED_STATUSES = ("CANCELLED", "REJECTED", "FAILED")


def status_label(status: str) -> str:
    return STATUS_LABELS.get(status, status)


def progress_chain(service_id: str) -> tuple[str, ...]:
    """這個服務的進度條要畫哪幾格。"""
    if service_id in QUOTING_SERVICES:
        return PROGRESS_CHAIN
    return tuple(s for s in PROGRESS_CHAIN if s not in ("CONTACTED", "QUOTED"))


def build_progress(request: dict) -> list[dict]:
    """住戶端進度條：每一格的狀態、名稱、完成時間，以及走到了沒。

    時間戳取自 `progress_history`（廠商每按一次按鈕就補一筆）。這個欄位是這次才
    加的，之前建立的案件沒有——所以「走到了沒」不能只看有沒有時間戳，還要拿目前
    狀態在鏈上的位置回推，讓舊案件也畫得出正確的進度，只是前面幾格沒有時間可顯示。
    """
    status = request.get("status", "")
    service_id = request.get("service_id", "")
    chain = progress_chain(service_id)
    history = {
        entry.get("status"): entry.get("at", "")
        for entry in request.get("progress_history") or []
    }
    # 送出時間就是案件建立時間：住戶自己按的送出不會經過廠商端的 progress_history。
    # 還沒送出的草稿不能算走過第一格，否則畫面會說「已送出需求」但廠商根本看不到。
    if status not in ("DRAFT", "AWAITING_USER_CONFIRMATION"):
        history.setdefault("SUBMITTED", request.get("created_at", ""))

    current = PROGRESS_ALIASES.get(status, status)
    reached = chain.index(current) if current in chain else -1

    steps = [
        {
            "status": step,
            "label": PROGRESS_STEP_LABELS.get(step, status_label(step)),
            "at": history.get(step, ""),
            "done": index <= reached or step in history,
        }
        for index, step in enumerate(chain)
    ]
    if status in PROGRESS_ABORTED_STATUSES:
        steps.append(
            {
                "status": status,
                "label": status_label(status),
                "at": request.get("updated_at", ""),
                "done": True,
            }
        )
    return steps
