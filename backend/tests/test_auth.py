"""Email 註冊／登入流程：註冊、重複、密碼強度、登入、token 授權、資料隔離。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

client = TestClient(app)


def _register(email, password="secret123", name="測試"):
    return client.post("/api/auth/register",
                       json={"email": email, "password": password, "name": name})


def test_register_then_authenticated_me():
    r = _register("alice@example.com", name="Alice")
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "Alice"
    assert body["sub"].startswith("user-")
    token = body["token"]

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["sub"] == body["sub"]


def test_duplicate_email_rejected():
    _register("dup@example.com")
    r = _register("dup@example.com")
    assert r.status_code == 409
    assert r.json()["detail"]["error"]["code"] == "EMAIL_EXISTS"


def test_weak_password_rejected():
    r = _register("weak@example.com", password="123")
    assert r.status_code == 400
    assert r.json()["detail"]["error"]["code"] == "WEAK_PASSWORD"


def test_invalid_email_rejected():
    r = _register("not-an-email")
    assert r.status_code == 400
    assert r.json()["detail"]["error"]["code"] == "INVALID_EMAIL"


def test_login_success_and_wrong_password():
    _register("bob@example.com", password="rightpass1")
    ok = client.post("/api/auth/login",
                     json={"email": "bob@example.com", "password": "rightpass1"})
    assert ok.status_code == 200
    assert ok.json()["token"]

    bad = client.post("/api/auth/login",
                      json={"email": "bob@example.com", "password": "wrongpass1"})
    assert bad.status_code == 401
    assert bad.json()["detail"]["error"]["code"] == "INVALID_CREDENTIALS"


def test_login_unknown_email():
    r = client.post("/api/auth/login",
                    json={"email": "nobody@example.com", "password": "whatever1"})
    assert r.status_code == 401
    assert r.json()["detail"]["error"]["code"] == "INVALID_CREDENTIALS"


def test_email_case_insensitive():
    _register("Case@Example.com", password="mixedcase1")
    r = client.post("/api/auth/login",
                    json={"email": "case@example.com", "password": "mixedcase1"})
    assert r.status_code == 200


def test_missing_token_unauthorized():
    assert client.get("/api/auth/me").status_code == 401


def test_registered_users_have_distinct_subs():
    a = _register("iso1@example.com").json()["sub"]
    b = _register("iso2@example.com").json()["sub"]
    assert a != b
