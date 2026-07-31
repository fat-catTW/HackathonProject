"""聯絡資訊的欄位級加密與遮罩（Milestone 15）。

住戶填的姓名／電話／地址是這個系統裡最敏感的欄位，廠商後台又非看到不可才能上門
服務。這個模組把「能不能看」和「看到什麼」拆成三層：

1. **寫入即加密**（`encrypt_form_data`）：案件存進 DynamoDB 前，`form_data` 裡的
   聯絡欄位換成 `enc:` 開頭的密文，資料庫（含鏡射給廠商的 `VENDOR#` 索引）不再
   有明文。
2. **平常只給遮罩**（`masked_form_data`）：寫入時一併算好遮罩值存在
   `form_data_masked`，廠商清單與明細直接讀它，不必解密、也就不留存取紀錄。
3. **解密要留痕**：完整內容只能走 `POST /api/vendor/requests/{id}/contact`，那條
   路徑每次都會寫一筆存取紀錄（見 `store.log_contact_access`）。

金鑰預設由 `CONTACT_ENCRYPTION_KEY` 導出（本地 AES-GCM）；設定 `CONTACT_KMS_KEY_ID`
後改用 KMS。兩種密文各有前綴，解密時依前綴挑後端，因此切換金鑰來源不會讓既有資料
變成亂碼——舊資料仍用寫它的那把鑰匙解。
"""
from __future__ import annotations

import base64
import hashlib
import logging
import os
from functools import lru_cache

from ..config import get_settings

logger = logging.getLogger(__name__)

# 住戶填的、足以直接聯絡到本人的欄位。餐廳電話（restaurant_phone）、門市地址
# （sender_store）這類公開營業資訊不在此列，加密它們只會讓廠商看不到該看的東西。
CONTACT_FIELDS: tuple[str, ...] = (
    "contact_name",
    "phone",
    "address",
    "sender_address",
    "receiver_address",
)

_LOCAL_PREFIX = "enc:v1:"
_KMS_PREFIX = "enc:kms1:"
_PREFIXES = (_LOCAL_PREFIX, _KMS_PREFIX)

# 沒設 CONTACT_ENCRYPTION_KEY 時的開發用金鑰。必須是固定值：本地 mock 儲存是一份
# JSON 檔，每次啟動換一把鑰匙會讓上次存的案件再也解不開。
_DEV_SECRET = "ai-service-assistant/dev-contact-key"

MASKED_PLACEHOLDER = "***"


class ContactDecryptError(RuntimeError):
    """密文解不開（金鑰換過、資料損毀）。"""


class _LocalCipher:
    """AES-GCM，金鑰由設定值 SHA-256 導出。"""

    prefix = _LOCAL_PREFIX
    _NONCE_BYTES = 12

    def __init__(self, secret: str) -> None:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        self._aesgcm = AESGCM(hashlib.sha256(secret.encode("utf-8")).digest())

    def encrypt(self, plaintext: str) -> str:
        nonce = os.urandom(self._NONCE_BYTES)
        blob = nonce + self._aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        return self.prefix + base64.b64encode(blob).decode("ascii")

    def decrypt(self, token: str) -> str:
        blob = base64.b64decode(token[len(self.prefix) :])
        nonce, ciphertext = blob[: self._NONCE_BYTES], blob[self._NONCE_BYTES :]
        return self._aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")


class _KmsCipher:
    """KMS Encrypt／Decrypt。單一欄位遠小於 4KB 上限，不需要信封加密。"""

    prefix = _KMS_PREFIX

    def __init__(self, key_id: str) -> None:
        self._key_id = key_id

    @property
    def _client(self):
        from .aws import get_aws_client

        return get_aws_client("kms")

    def encrypt(self, plaintext: str) -> str:
        blob = self._client.encrypt(KeyId=self._key_id, Plaintext=plaintext.encode("utf-8"))
        return self.prefix + base64.b64encode(blob["CiphertextBlob"]).decode("ascii")

    def decrypt(self, token: str) -> str:
        blob = base64.b64decode(token[len(self.prefix) :])
        # KeyId 帶上去，避免用到密文裡宣告的其他金鑰。
        result = self._client.decrypt(KeyId=self._key_id, CiphertextBlob=blob)
        return result["Plaintext"].decode("utf-8")


@lru_cache(maxsize=len(_PREFIXES))
def _cipher_for(prefix: str):
    settings = get_settings()
    if prefix == _KMS_PREFIX:
        return _KmsCipher(settings.contact_kms_key_id)
    if not settings.contact_encryption_key and not settings.use_mock:
        logger.warning(
            "CONTACT_ENCRYPTION_KEY 未設定，聯絡資訊改用內建開發金鑰加密；"
            "正式環境請設定 CONTACT_ENCRYPTION_KEY 或 CONTACT_KMS_KEY_ID。"
        )
    return _LocalCipher(settings.contact_encryption_key or _DEV_SECRET)


def _writer():
    settings = get_settings()
    # KMS 只在連真實 AWS 時啟用；mock 模式不打外部服務，測試才跑得動。
    if settings.contact_kms_key_id and not settings.use_mock:
        return _cipher_for(_KMS_PREFIX)
    return _cipher_for(_LOCAL_PREFIX)


def is_encrypted(value) -> bool:
    return isinstance(value, str) and value.startswith(_PREFIXES)


def encrypt_value(value: str) -> str:
    """加密單一欄位；已經是密文就原樣回傳（重複呼叫不會疊加密）。"""
    if not isinstance(value, str) or not value or is_encrypted(value):
        return value
    return _writer().encrypt(value)


def decrypt_value(value: str) -> str:
    """解密單一欄位；明文（Milestone 15 之前的舊資料）原樣回傳。"""
    if not is_encrypted(value):
        return value
    prefix = next(p for p in _PREFIXES if value.startswith(p))
    try:
        return _cipher_for(prefix).decrypt(value)
    except Exception as exc:  # noqa: BLE001
        raise ContactDecryptError(f"聯絡資訊解密失敗：{exc}") from exc


def encrypt_form_data(form_data: dict) -> dict:
    """回傳把聯絡欄位換成密文的副本；不動原本的 dict。"""
    return {
        key: encrypt_value(value) if key in CONTACT_FIELDS else value
        for key, value in form_data.items()
    }


def decrypt_form_data(form_data: dict) -> dict:
    """回傳解密後的副本。

    解不開的欄位**保留密文**，不換成錯誤字串：呼叫端拿到案件後常常改個狀態就整包
    寫回去（例如住戶取消案件），若這裡塞了佔位字串，一次寫回就把原始資料永久蓋掉。
    保留密文則因為 `encrypt_value` 對密文是 no-op，最壞情況只是這欄暫時讀不出來。
    """
    plain = {}
    for key, value in form_data.items():
        if not is_encrypted(value):
            plain[key] = value
            continue
        try:
            plain[key] = decrypt_value(value)
        except ContactDecryptError:
            logger.warning("聯絡欄位 %s 解密失敗，保留密文。", key)
            plain[key] = value
    return plain


def is_fully_encrypted(form_data: dict) -> bool:
    """所有該加密的欄位都已經是密文（沒有聯絡欄位時也算）。"""
    return all(
        is_encrypted(value)
        for key, value in form_data.items()
        if key in CONTACT_FIELDS and isinstance(value, str) and value
    )


# ---- 遮罩 ----
_ADDRESS_HEAD = 6


def _mask_name(value: str) -> str:
    if len(value) <= 1:
        return value
    if len(value) == 2:
        return f"{value[0]}○"
    return f"{value[0]}{'○' * (len(value) - 2)}{value[-1]}"


def _mask_phone(value: str) -> str:
    digits = [c for c in value if c.isdigit()]
    if len(digits) < 7:
        # 短到遮不出東西（分機、明顯的假資料），整串蓋掉比露出一半安全。
        return MASKED_PLACEHOLDER
    return f"{value[:4]}{MASKED_PLACEHOLDER}{value[-3:]}"


def _mask_address(value: str) -> str:
    """只留到縣市區的程度，足夠廠商判斷服務範圍，但找不到門牌。"""
    head = value[:_ADDRESS_HEAD]
    return f"{head}…" if len(value) > len(head) else head


_MASKERS = {
    "contact_name": _mask_name,
    "phone": _mask_phone,
    "address": _mask_address,
    "sender_address": _mask_address,
    "receiver_address": _mask_address,
}


def mask_value(field_id: str, value) -> str:
    if not isinstance(value, str) or not value or is_encrypted(value):
        # 密文沒辦法遮罩（遮罩要看得懂內容才知道留哪幾個字），一律整串蓋掉。
        return MASKED_PLACEHOLDER if value else ""
    return _MASKERS.get(field_id, lambda v: MASKED_PLACEHOLDER)(value)


def masked_form_data(form_data: dict) -> dict:
    """聯絡欄位的遮罩值；`form_data` 需要是解密後的內容。"""
    return {
        key: mask_value(key, value)
        for key, value in form_data.items()
        if key in CONTACT_FIELDS and value not in (None, "")
    }


def mask_for_display(form_data: dict, masked: dict | None = None) -> dict:
    """把 `form_data` 的聯絡欄位換成遮罩值，供廠商清單／明細顯示。

    優先用寫入時算好的 `form_data_masked`；Milestone 15 之前存的明文案件沒有那份
    對照表，就地遮罩即可（那些案件的 form_data 本來就是明文）。
    """
    masked = masked or {}
    return {
        key: (masked.get(key) or mask_value(key, value)) if key in CONTACT_FIELDS else value
        for key, value in form_data.items()
    }
