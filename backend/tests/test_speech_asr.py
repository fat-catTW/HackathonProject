from unittest.mock import patch

import pytest

from backend.app.services import speech_asr


class _Pipeline:
    def __init__(self):
        self.audio_path = None
        self.kwargs = None

    def __call__(self, audio_path, **kwargs):
        self.audio_path = audio_path
        self.kwargs = kwargs
        return {"text": "幫我預約冷氣清洗"}


def test_transcribe_taiwanese_uses_breeze_pipeline():
    pipe = _Pipeline()
    with patch("backend.app.services.speech_asr._load_pipeline", return_value=pipe):
        text = speech_asr.transcribe("audio.webm", "nan")

    assert text == "幫我預約冷氣清洗"
    assert pipe.audio_path == "audio.webm"
    assert pipe.kwargs == {"generate_kwargs": {"task": "transcribe"}}


def test_transcribe_rejects_mandarin_backend_path():
    with pytest.raises(speech_asr.SpeechAsrUnavailable):
        speech_asr.transcribe("audio.webm", "zh")
