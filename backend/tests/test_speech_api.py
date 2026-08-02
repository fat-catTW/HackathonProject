from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.main import app


def _headers(client: TestClient):
    accounts = client.get("/api/auth/demo-accounts").json()["accounts"]
    return {"Authorization": f"Bearer {accounts[0]['token']}"}


def test_transcribe_speech_returns_text_and_language():
    client = TestClient(app)
    with patch("backend.app.api.speech.transcribe", return_value="幫我預約打掃") as asr:
        response = client.post(
            "/api/speech/transcribe",
            headers=_headers(client),
            data={"language": "nan"},
            files={"audio": ("speech.webm", b"audio-bytes", "audio/webm")},
        )

    assert response.status_code == 200
    assert response.json() == {"text": "幫我預約打掃", "language": "nan"}
    assert asr.call_args.args[1] == "nan"


def test_transcribe_speech_rejects_unknown_language():
    client = TestClient(app)
    response = client.post(
        "/api/speech/transcribe",
        headers=_headers(client),
        data={"language": "en"},
        files={"audio": ("speech.webm", b"audio-bytes", "audio/webm")},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["error"]["code"] == "INVALID_LANGUAGE"


def test_transcribe_speech_rejects_mandarin_backend_path():
    client = TestClient(app)
    response = client.post(
        "/api/speech/transcribe",
        headers=_headers(client),
        data={"language": "zh"},
        files={"audio": ("speech.webm", b"audio-bytes", "audio/webm")},
    )

    assert response.status_code == 400
    assert response.json()["detail"]["error"]["code"] == "INVALID_LANGUAGE"
