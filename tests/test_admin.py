from unittest.mock import patch

from tests.conftest import auth_headers


def make_product(client, admin_token, price=10.00, stock=20, name="Widget"):
    resp = client.post(
        "/api/products",
        json={"name": name, "description": "desc", "price": price, "stock_quantity": stock},
        headers=auth_headers(admin_token),
    )
    return resp.json()


def test_non_admin_cannot_access_admin_endpoints(client, customer_token):
    resp = client.get("/api/admin/dashboard", headers=auth_headers(customer_token))
    assert resp.status_code == 403


def test_unauthenticated_cannot_access_admin_endpoints(client):
    resp = client.get("/api/admin/dashboard")
    assert resp.status_code == 401


def test_dashboard_stats_reflect_created_orders(client, admin_token, customer_token):
    product = make_product(client, admin_token, stock=100)
    for _ in range(3):
        client.post(
            "/api/orders",
            json={"shipping_address": "1 Test Way", "items": [{"product_id": product["id"], "quantity": 1}]},
            headers=auth_headers(customer_token),
        )

    resp = client.get("/api/admin/dashboard", headers=auth_headers(admin_token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_orders"] == 3
    assert body["pending_orders"] == 3
    assert len(body["recent_orders"]) == 3


def test_admin_can_list_all_users(client, admin_token, customer_token):
    resp = client.get("/api/admin/users", headers=auth_headers(admin_token))
    assert resp.status_code == 200
    emails = {u["email"] for u in resp.json()}
    assert "admin@example.com" in emails
    assert "customer@example.com" in emails


def test_admin_can_list_all_orders_with_status_filter(client, admin_token, customer_token):
    product = make_product(client, admin_token)
    order = client.post(
        "/api/orders",
        json={"shipping_address": "1 Test Way", "items": [{"product_id": product["id"], "quantity": 1}]},
        headers=auth_headers(customer_token),
    ).json()

    resp = client.get("/api/admin/orders?status=PENDING", headers=auth_headers(admin_token))
    assert resp.status_code == 200
    assert any(o["id"] == order["id"] for o in resp.json())

    resp_empty = client.get("/api/admin/orders?status=COMPLETED", headers=auth_headers(admin_token))
    assert resp_empty.json() == []


def test_admin_can_list_all_events(client, admin_token, customer_token):
    product = make_product(client, admin_token)
    client.post(
        "/api/orders",
        json={"shipping_address": "1 Test Way", "items": [{"product_id": product["id"], "quantity": 1}]},
        headers=auth_headers(customer_token),
    )

    resp = client.get("/api/admin/events", headers=auth_headers(admin_token))
    assert resp.status_code == 200
    assert len(resp.json()) >= 1
