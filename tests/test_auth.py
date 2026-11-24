def test_register_creates_user_and_returns_token(client):
    resp = client.post(
        "/api/auth/register",
        json={"name": "Jane Doe", "email": "jane@example.com", "password": "StrongPass123"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["user"]["email"] == "jane@example.com"
    assert body["user"]["role"] == "CUSTOMER"
    assert body["access_token"]


def test_register_rejects_duplicate_email(client):
    payload = {"name": "Jane Doe", "email": "dup@example.com", "password": "StrongPass123"}
    client.post("/api/auth/register", json=payload)
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 409


def test_register_rejects_short_password(client):
    resp = client.post(
        "/api/auth/register",
        json={"name": "Jane Doe", "email": "short@example.com", "password": "short"},
    )
    assert resp.status_code == 422


def test_login_succeeds_with_correct_credentials(client):
    client.post(
        "/api/auth/register",
        json={"name": "Jane Doe", "email": "login@example.com", "password": "StrongPass123"},
    )
    resp = client.post("/api/auth/login", json={"email": "login@example.com", "password": "StrongPass123"})
    assert resp.status_code == 200
    assert resp.json()["access_token"]


def test_login_fails_with_wrong_password(client):
    client.post(
        "/api/auth/register",
        json={"name": "Jane Doe", "email": "wrongpw@example.com", "password": "StrongPass123"},
    )
    resp = client.post("/api/auth/login", json={"email": "wrongpw@example.com", "password": "IncorrectPass1"})
    assert resp.status_code == 401


def test_me_requires_authentication(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_me_returns_current_user(client, customer_token):
    from tests.conftest import auth_headers

    resp = client.get("/api/auth/me", headers=auth_headers(customer_token))
    assert resp.status_code == 200
    assert resp.json()["email"] == "customer@example.com"
