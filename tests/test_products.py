from tests.conftest import auth_headers


def create_product(client, token, **overrides):
    payload = {
        "name": "Test Widget",
        "description": "A widget for testing.",
        "price": 19.99,
        "stock_quantity": 50,
    }
    payload.update(overrides)
    return client.post("/api/products", json=payload, headers=auth_headers(token))


def test_customers_cannot_create_products(client, customer_token):
    resp = create_product(client, customer_token)
    assert resp.status_code == 403


def test_admin_can_create_product(client, admin_token):
    resp = create_product(client, admin_token)
    assert resp.status_code == 201
    assert resp.json()["name"] == "Test Widget"


def test_list_products_is_public(client, admin_token):
    create_product(client, admin_token)
    resp = client.get("/api/products")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_get_single_product(client, admin_token):
    created = create_product(client, admin_token).json()
    resp = client.get(f"/api/products/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


def test_get_missing_product_returns_404(client):
    resp = client.get("/api/products/9999")
    assert resp.status_code == 404


def test_admin_can_update_product(client, admin_token):
    created = create_product(client, admin_token).json()
    resp = client.put(
        f"/api/products/{created['id']}",
        json={"price": 29.99, "stock_quantity": 5},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert float(body["price"]) == 29.99
    assert body["stock_quantity"] == 5


def test_admin_can_deactivate_product(client, admin_token):
    created = create_product(client, admin_token).json()
    resp = client.delete(f"/api/products/{created['id']}", headers=auth_headers(admin_token))
    assert resp.status_code == 204

    listing = client.get("/api/products").json()
    assert all(p["id"] != created["id"] for p in listing)


def test_create_product_rejects_non_positive_price(client, admin_token):
    resp = create_product(client, admin_token, price=0)
    assert resp.status_code == 422
