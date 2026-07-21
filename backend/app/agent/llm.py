"""LLM 語意判斷層（Amazon Bedrock）。

Milestone 1.5：把 Agent 狀態機裡的 hardcode 詞表判斷（確認／拒絕）換成 LLM 語意理解。
一律走 Amazon Bedrock（模型由 BEDROCK_MODEL_ID 設定，對齊 M2 部署目標）。
無 AWS 憑證時回傳 None，呼叫端 fallback 回規則式判斷，Demo 不中斷。
"""
from __future__ import annotations

import json
from functools import lru_cache

from ..config import get_settings

_INTERPRET_SCHEMA = {
    "type": "object",
    "properties": {
        "intent": {
            "type": "string",
            "enum": ["yes", "no", "unclear"],
            "description": "使用者對這個是非題的回答意圖",
        },
    },
    "required": ["intent"],
    "additionalProperties": False,
}

_SYSTEM = (
    "你是生活服務預約系統的語意判斷模組。"
    "給你一個系統問使用者的是非題，以及使用者的回覆，判斷回覆的意圖：\n"
    "- yes：同意／接受（例如「好」「都可以」「嗯」「行」「沒問題」「照舊」）\n"
    "- no：拒絕／要改（例如「不要」「換一個」「不用了」）\n"
    "- unclear：答非所問或提供了別的資訊（例如被問地址卻回了電話號碼）\n"
    "只依語意判斷，不要臆測使用者沒說的內容。"
)


@lru_cache
def _get_client():
    """建立 Bedrock client；無 AWS 憑證時回傳 (None, None)。"""
    settings = get_settings()
    try:
        import boto3

        if boto3.Session().get_credentials() is not None:
            from anthropic import AnthropicBedrockMantle

            return (
                AnthropicBedrockMantle(aws_region=settings.aws_region, timeout=10.0),
                settings.bedrock_model_id,
            )
    except Exception:
        pass
    return None, None


def is_available() -> bool:
    return _get_client()[0] is not None


def interpret_yes_no(question: str, reply: str) -> str | None:
    """判斷使用者對是非題的回覆意圖。

    回傳 "yes" / "no" / "unclear"；LLM 不可用或呼叫失敗時回傳 None。
    """
    client, model = _get_client()
    if client is None:
        return None
    try:
        response = client.messages.create(
            model=model,
            max_tokens=256,
            system=_SYSTEM,
            output_config={"format": {"type": "json_schema", "schema": _INTERPRET_SCHEMA}},
            messages=[
                {
                    "role": "user",
                    "content": f"系統問題：「{question}」\n使用者回覆：「{reply}」",
                }
            ],
        )
        text = next(b.text for b in response.content if b.type == "text")
        intent = json.loads(text)["intent"]
        return intent if intent in ("yes", "no", "unclear") else None
    except Exception:
        return None
