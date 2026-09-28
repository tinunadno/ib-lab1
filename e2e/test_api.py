import json
import urllib.error
import urllib.request


def call(base, path, method="GET", body=None, token=None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(base + path, data=data, method=method)
    if body is not None:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req) as res:
            return res.status, json.loads(res.read())
    except urllib.error.HTTPError as err:
        raw = err.read()
        return err.code, json.loads(raw) if raw else {}


def test_login_and_read_data(base):
    status, body = call(
        base, "/auth/login", "POST", {"username": "alice", "password": "password"}
    )
    assert status == 200 and body["token"]
    status, body = call(base, "/api/data", token=body["token"])
    assert status == 200
    assert {"id": 1, "username": "alice"} in body["users"]


def test_login_rejects_bad_password(base):
    status, body = call(
        base, "/auth/login", "POST", {"username": "alice", "password": "wrong"}
    )
    assert status == 401
    assert "token" not in body


def test_login_rejects_sql_injection(base):
    status, body = call(
        base,
        "/auth/login",
        "POST",
        {"username": "' OR 1=1 --", "password": "x"},
    )
    assert status == 401
    assert "token" not in body


def test_data_requires_token(base):
    status, _ = call(base, "/api/data")
    assert status == 401


def test_data_rejects_bad_token(base):
    status, _ = call(base, "/api/data", token="not-a-jwt")
    assert status == 401


def test_message_requires_token(base):
    status, _ = call(base, "/api/messages", "POST", {"text": "hi"})
    assert status == 401


def test_message_rejects_empty_text(base):
    _, login = call(
        base, "/auth/login", "POST", {"username": "alice", "password": "password"}
    )
    status, _ = call(base, "/api/messages", "POST", {"text": "  "}, login["token"])
    assert status == 400


def test_message_escapes_html(base):
    _, login = call(
        base, "/auth/login", "POST", {"username": "alice", "password": "password"}
    )
    status, body = call(
        base,
        "/api/messages",
        "POST",
        {"text": "<script>alert(1)</script>"},
        login["token"],
    )
    assert status == 201
    assert body["text"] == "&lt;script&gt;alert(1)&lt;/script&gt;"
