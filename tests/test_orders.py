from unittest.mock import patch

from tests.conftest import auth_headers


def make_product(client, admin_token, price=10.00, stock=20, name="Widget"):
    resp = client.post(
        "/api/products",
        json={"name": name, "description": "desc", "price": price, "stock_quantity": stock},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 201
    return resp.json()


def test_create_order_publishes_to_sqs_and_stores_invoice(client, admin_token, customer_token):
    product = make_product(client, admin_token)

    with patch("app.services.order_service.aws_sqs.send_order_event") as mock_sqs, \
         patch("app.services.order_service.aws_s3.store_invoice") as mock_s3:
        mock_sqs.return_value = "fake-message-id-123"
        mock_s3.return_value = "orders/2026/09/ORD-2026-000001/invoice.json"

        resp = client.post(
            "/api/orders",
            json={
                "shipping_address": "123 Main St, Springfield",
                "items": [{"product_id": product["id"], "quantity": 2}],
            },
            headers=auth_headers(customer_token),
        )

        assert resp.status_code == 201
        body = resp.json()
        assert body["status"] == "PENDING"
        assert float(body["total_amount"]) == 20.00
        assert len(body["items"]) == 1

        mock_s3.assert_called_once()
        mock_sqs.assert_called_once()
        _, kwargs = mock_sqs.call_args
        assert kwargs["event_type"] == "ORDER_CREATED"
        assert kwargs["order_number"] == body["order_number"]


def test_create_order_decrements_stock(client, admin_token, customer_token):
    product = make_product(client, admin_token, stock=5)

    resp = client.post(
        "/api/orders",
        json={"shipping_address": "1 Test Way", "items": [{"product_id": product["id"], "quantity": 3}]},
        headers=auth_headers(customer_token),
    )
    assert resp.status_code == 201

    remaining = client.get(f"/api/products/{product['id']}").json()
    assert remaining["stock_quantity"] == 2


def test_create_order_rejects_insufficient_stock(client, admin_token, customer_token):
    product = make_product(client, admin_token, stock=1)

    resp = client.post(
        "/api/orders",
        json={"shipping_address": "1 Test Way", "items": [{"product_id": product["id"], "quantity": 5}]},
        headers=auth_headers(customer_token),
    )
    assert resp.status_code == 400


def test_create_order_rejects_unknown_product(client, customer_token):
    resp = client.post(
        "/api/orders",
        json={"shipping_address": "1 Test Way", "items": [{"product_id": 99999, "quantity": 1}]},
        headers=auth_headers(customer_token),
    )
    assert resp.status_code == 404


def test_create_order_requires_at_least_one_item(client, customer_token):
    resp = client.post(
        "/api/orders",
        json={"shipping_address": "1 Test Way", "items": []},
        headers=auth_headers(customer_token),
    )
    assert resp.status_code == 422


def test_customer_cannot_view_another_customers_order(client, admin_token, customer_token):
    product = make_product(client, admin_token)
    order = client.post(
        "/api/orders",
        json={"shipping_address": "1 Test Way", "items": [{"product_id": product["id"], "quantity": 1}]},
        headers=auth_headers(customer_token),
    ).json()

    other = client.post(
        "/api/auth/register",
        json={"name": "Other Customer", "email": "other@example.com", "password": "StrongPass123"},
    ).json()

    resp = client.get(f"/api/orders/{order['id']}", headers=auth_headers(other["access_token"]))
    assert resp.status_code == 403


def test_admin_can_view_any_order(client, admin_token, customer_token):
    product = make_product(client, admin_token)
    order = client.post(
        "/api/orders",
        json={"shipping_address": "1 Test Way", "items": [{"product_id": product["id"], "quantity": 1}]},
        headers=auth_headers(customer_token),
    ).json()

    resp = client.get(f"/api/orders/{order['id']}", headers=auth_headers(admin_token))
    assert resp.status_code == 200


def test_valid_status_transition_succeeds(client, admin_token, customer_token):
    product = make_product(client, admin_token)
    order = client.post(
        "/api/orders",
        json={"shipping_address": "1 Test Way", "items": [{"product_id": product["id"], "quantity": 1}]},
        headers=auth_headers(customer_token),
    ).json()

    with patch("app.services.order_service.aws_sns.publish_order_event"):
        resp = client.patch(
            f"/api/orders/{order['id']}/status",
            json={"status": "PROCESSING"},
            headers=auth_headers(admin_token),
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == "PROCESSING"


def test_invalid_status_transition_rejected(client, admin_token, customer_token):
    product = make_product(client, admin_token)
    order = client.post(
        "/api/orders",
        json={"shipping_address": "1 Test Way", "items": [{"product_id": product["id"], "quantity": 1}]},
        headers=auth_headers(customer_token),
    ).json()

    # PENDING -> COMPLETED is not a legal transition.
    resp = client.patch(
        f"/api/orders/{order['id']}/status",
        json={"status": "COMPLETED"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 400


def test_customer_cannot_update_order_status(client, admin_token, customer_token):
    product = make_product(client, admin_token)
    order = client.post(
        "/api/orders",
        json={"shipping_address": "1 Test Way", "items": [{"product_id": product["id"], "quantity": 1}]},
        headers=auth_headers(customer_token),
    ).json()

    resp = client.patch(
        f"/api/orders/{order['id']}/status",
        json={"status": "PROCESSING"},
        headers=auth_headers(customer_token),
    )
    assert resp.status_code == 403


def test_customer_can_cancel_own_pending_order_and_stock_is_restored(client, admin_token, customer_token):
    product = make_product(client, admin_token, stock=10)
    order = client.post(
        "/api/orders",
        json={"shipping_address": "1 Test Way", "items": [{"product_id": product["id"], "quantity": 4}]},
        headers=auth_headers(customer_token),
    ).json()

    with patch("app.services.order_service.aws_sns.publish_order_event"):
        resp = client.post(f"/api/orders/{order['id']}/cancel", headers=auth_headers(customer_token))
    assert resp.status_code == 200
    assert resp.json()["status"] == "CANCELLED"

    restocked = client.get(f"/api/products/{product['id']}").json()
    assert restocked["stock_quantity"] == 10


def test_order_events_endpoint_lists_the_creation_event(client, admin_token, customer_token):
    product = make_product(client, admin_token)
    order = client.post(
        "/api/orders",
        json={"shipping_address": "1 Test Way", "items": [{"product_id": product["id"], "quantity": 1}]},
        headers=auth_headers(customer_token),
    ).json()

    resp = client.get(f"/api/orders/{order['id']}/events", headers=auth_headers(customer_token))
    assert resp.status_code == 200
    events = resp.json()
    assert any(e["event_type"] == "ORDER_CREATED" for e in events)
