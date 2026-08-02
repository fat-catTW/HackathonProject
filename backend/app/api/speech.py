"""Speech-to-text APIs."""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from starlette.datastructures import UploadFile

from ..auth.cognito import CurrentUser, get_current_user
from ..config import get_settings
from ..services.speech_asr import SpeechAsrUnavailable, transcribe

router = APIRouter()

SpeechLanguage = Literal["zh", "nan"]


def _error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"success": False, "error": {"code": code, "message": message}},
    )


@router.post("/api/speech/transcribe")
async def transcribe_speech(request: Request, _user: CurrentUser = Depends(get_current_user)):
    settings = get_settings()
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > settings.asr_max_upload_bytes:
        raise _error(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            "AUDIO_TOO_LARGE",
            "Audio upload is too large.",
        )

    form = await request.form()
    upload = form.get("audio")
    language = form.get("language", "zh")
    if language != "nan":
        raise _error(
            status.HTTP_400_BAD_REQUEST,
            "INVALID_LANGUAGE",
            "Server-side speech recognition only accepts Taiwanese Hokkien (nan).",
        )
    if not isinstance(upload, UploadFile):
        raise _error(status.HTTP_400_BAD_REQUEST, "AUDIO_REQUIRED", "Audio file is required.")

    suffix = Path(upload.filename or "audio.webm").suffix or ".webm"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp_path = Path(tmp.name)
        total = 0
        while chunk := await upload.read(1024 * 1024):
            total += len(chunk)
            if total > settings.asr_max_upload_bytes:
                tmp_path.unlink(missing_ok=True)
                raise _error(
                    status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    "AUDIO_TOO_LARGE",
                    "Audio upload is too large.",
                )
            tmp.write(chunk)

    try:
        text = transcribe(str(tmp_path), language)  # type: ignore[arg-type]
    except SpeechAsrUnavailable as exc:
        raise _error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "ASR_UNAVAILABLE",
            f"Speech recognition is unavailable: {exc}",
        ) from exc
    except Exception as exc:
        raise _error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "ASR_TRANSCRIBE_FAILED",
            f"Speech recognition failed: {exc}",
        ) from exc
    finally:
        tmp_path.unlink(missing_ok=True)

    return {"text": text, "language": language}
