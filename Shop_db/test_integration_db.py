import random
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import database
from database import Base, get_db

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

database.engine = engine
database.SessionLocal = TestingSessionLocal

from main import app

Base.metadata.create_all(bind=engine)


@pytest.fixture(scope="function")
def db_session():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def _register_customer(
    client,
    username: str | None = None,
    password: str = "002233Tt",
    role: str = "user",
    admin_key: str | None = None,
):
    suffix = random.randint(1, 1_000_000)
    username = username or f"user_{suffix}"
    email = f"{username}@example.com"
    params = {
        "username": username,
        "email": email,
        "password": password,
        "phone": "1234567",
        "country": "UA",
        "role": role,
    }
    if admin_key is not None:
        params["admin_key"] = admin_key
    response = client.post(
        "/register",
        params=params,
    )
    assert response.status_code == 200
    return {
        "CustomerID": response.json()["customer_id"],
        "Name": username,
        "Email": email,
        "Password": password,
    }


def _login_customer(client, username: str, password: str) -> str:
    response = client.post(
        "/login",
        data={"username": username, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            db_session.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        auth_customer = _register_customer(
            c,
            username=f"auth_{random.randint(1, 1_000_000)}",
            role="admin",
            admin_key="1461",
        )
        access_token = _login_customer(c, auth_customer["Name"], auth_customer["Password"])
        c.headers.update({"Authorization": f"Bearer {access_token}"})
        yield c

    app.dependency_overrides.clear()


STATE: dict[str, object] = {}


def _require_state(key: str):
    assert key in STATE, f"Missing {key}. Run previous tests in order."
    return STATE[key]


def test_create_supplier(client):
    supplier = client.post(
        "/supplier",
        json={
            "SupplierName": "SupplierFlow",
            "Address": "Kyiv, UA",
            "Phone": "1234567",
        },
    ).json()
    assert supplier["SupplierID"] > 0
    STATE["supplier_id"] = supplier["SupplierID"]


def test_create_products_for_supplier(client):
    supplier_id = _require_state("supplier_id")
    product_1 = client.post(
        "/product",
        json={
            "ProductName": "Laptop Flow",
            "Price": 1200,
            "SupplierID": supplier_id,
        },
    ).json()
    product_2 = client.post(
        "/product",
        json={
            "ProductName": "Mouse Flow",
            "Price": 25,
            "SupplierID": supplier_id,
        },
    ).json()
    STATE["product_ids"] = [product_1["ProductID"], product_2["ProductID"]]


def test_read_supplier_list(client):
    supplier_id = _require_state("supplier_id")
    suppliers = client.get("/supplier")
    assert suppliers.status_code == 200
    suppliers_json = suppliers.json()
    assert any(s["SupplierID"] == supplier_id for s in suppliers_json)


def test_read_supplier_products(client):
    supplier_id = _require_state("supplier_id")
    product_ids = set(_require_state("product_ids"))
    supplier_products = client.get(f"/supplier/{supplier_id}/products")
    assert supplier_products.status_code == 200
    products_json = supplier_products.json()
    found_ids = {p["ProductID"] for p in products_json}
    assert product_ids.issubset(found_ids)


def test_register_and_login_customer(client):
    customer = _register_customer(client, username=f"CustomerFlow_{random.randint(1, 1_000_000)}")
    token = _login_customer(client, customer["Name"], customer["Password"])
    assert token
    STATE["customer_id"] = customer["CustomerID"]


def test_create_order(client):
    customer_id = _require_state("customer_id")
    order = client.post(
        "/order",
        json={
            "OrderDate": datetime.now().isoformat(),
            "Status": "Pending",
            "CustomerID": customer_id,
        },
    ).json()
    assert order["CustomerID"] == customer_id
    STATE["order_id"] = order["OrderID"]


def test_add_products_to_order(client):
    order_id = _require_state("order_id")
    product_ids = _require_state("product_ids")
    detail_1 = client.post(
        "/orderdetail",
        json={
            "OrderID": order_id,
            "ProductID": product_ids[0],
            "Quantity": 1,
            "ShippingAddress": "Main street 1",
        },
    ).json()
    detail_2 = client.post(
        "/orderdetail",
        json={
            "OrderID": order_id,
            "ProductID": product_ids[1],
            "Quantity": 2,
            "ShippingAddress": "Main street 1",
        },
    ).json()
    assert detail_1["OrderID"] == order_id
    assert detail_2["OrderID"] == order_id


def test_add_courier_to_order(client):
    order_id = _require_state("order_id")
    courier = client.post(
        "/courier",
        json={
            "Name": "Fast Courier",
            "Country": "UA",
            "Price": 50,
            "OrderID": order_id,
        },
    ).json()
    assert courier["OrderID"] == order_id


def test_create_payment(client):
    order_id = _require_state("order_id")
    payment = client.post(
        "/payment",
        json={
            "OrderID": order_id,
            "Status": "Pending",
            "Amount": 1250,
            "PaymentDate": datetime.now().isoformat(),
        },
    ).json()
    assert payment["OrderID"] == order_id
    STATE["payment_id"] = payment["PaymentID"]


def test_add_gift_to_payment(client):
    payment_id = _require_state("payment_id")
    gift = client.post(
        "/gift",
        json={
            "Amount": 100,
            "Unit": "USD",
            "Type": "Certificate",
            "PaymentID": payment_id,
        },
    ).json()
    assert gift["PaymentID"] == payment_id


def test_customer_can_read_products_but_cannot_modify_supplier_or_product(client):
    seller = _register_customer(
        client,
        username=f"seller_{random.randint(1, 1_000_000)}",
        role="seller",
    )
    seller_token = _login_customer(client, seller["Name"], seller["Password"])
    seller_headers = {"Authorization": f"Bearer {seller_token}"}

    supplier_list_response = client.get("/supplier", headers=seller_headers)
    assert supplier_list_response.status_code == 200
    supplier_payload = supplier_list_response.json()
    assert len(supplier_payload) >= 1
    supplier_id = supplier_payload[0]["SupplierID"]

    product_response = client.post(
        "/product",
        json={
            "ProductName": "Seller Product",
            "Price": 99,
            "SupplierID": supplier_id,
        },
        headers=seller_headers,
    )
    assert product_response.status_code == 200
    product_id = product_response.json()["ProductID"]

    buyer = _register_customer(client, username=f"buyer_{random.randint(1, 1_000_000)}")
    buyer_token = _login_customer(client, buyer["Name"], buyer["Password"])
    buyer_headers = {"Authorization": f"Bearer {buyer_token}"}

    products_list = client.get("/product", headers=buyer_headers)
    assert products_list.status_code == 200
    assert any(p["ProductID"] == product_id for p in products_list.json())

    single_product = client.get(f"/product/{product_id}", headers=buyer_headers)
    assert single_product.status_code == 200
    assert single_product.json()["ProductID"] == product_id

    create_product_forbidden = client.post(
        "/product",
        json={
            "ProductName": "Buyer Product",
            "Price": 10,
            "SupplierID": supplier_id,
        },
        headers=buyer_headers,
    )
    assert create_product_forbidden.status_code == 403

    update_product_forbidden = client.put(
        f"/product/{product_id}",
        json={
            "ProductName": "Buyer Updated Product",
            "Price": 101,
            "SupplierID": supplier_id,
        },
        headers=buyer_headers,
    )
    assert update_product_forbidden.status_code == 403

    update_supplier_forbidden = client.put(
        f"/supplier/{supplier_id}",
        json={
            "SupplierName": "Buyer Updated Supplier",
            "Address": "Lviv, UA",
            "Phone": "1234567",
        },
        headers=buyer_headers,
    )
    assert update_supplier_forbidden.status_code == 403


def test_supplier_is_auto_created_for_seller_and_user_cannot_create_supplier(client):
    user = _register_customer(client, username=f"user_no_supplier_{random.randint(1, 1_000_000)}")
    user_token = _login_customer(client, user["Name"], user["Password"])
    user_headers = {"Authorization": f"Bearer {user_token}"}

    create_supplier_forbidden = client.post(
        "/supplier",
        json={
            "SupplierName": "NotAllowedSupplier",
            "Address": "Kyiv, UA",
            "Phone": "1234567",
        },
        headers=user_headers,
    )
    assert create_supplier_forbidden.status_code == 403

    seller = _register_customer(
        client,
        username=f"seller_auto_{random.randint(1, 1_000_000)}",
        role="seller",
    )
    assert "CustomerID" in seller
    seller_token = _login_customer(client, seller["Name"], seller["Password"])
    seller_headers = {"Authorization": f"Bearer {seller_token}"}

    seller_suppliers = client.get("/supplier", headers=seller_headers)
    assert seller_suppliers.status_code == 200
    suppliers_payload = seller_suppliers.json()
    assert len(suppliers_payload) >= 1


def test_seller_can_view_only_own_products_in_get_endpoints(client):
    seller_one = _register_customer(
        client,
        username=f"seller_one_{random.randint(1, 1_000_000)}",
        role="seller",
    )
    seller_one_token = _login_customer(client, seller_one["Name"], seller_one["Password"])
    seller_one_headers = {"Authorization": f"Bearer {seller_one_token}"}

    seller_one_supplier = client.get("/supplier", headers=seller_one_headers).json()[0]
    seller_one_product_response = client.post(
        "/product",
        json={
            "ProductName": "Seller One Product",
            "Price": 50,
            "SupplierID": seller_one_supplier["SupplierID"],
        },
        headers=seller_one_headers,
    )
    assert seller_one_product_response.status_code == 200
    seller_one_product_id = seller_one_product_response.json()["ProductID"]

    seller_two = _register_customer(
        client,
        username=f"seller_two_{random.randint(1, 1_000_000)}",
        role="seller",
    )
    seller_two_token = _login_customer(client, seller_two["Name"], seller_two["Password"])
    seller_two_headers = {"Authorization": f"Bearer {seller_two_token}"}

    seller_two_supplier = client.get("/supplier", headers=seller_two_headers).json()[0]
    seller_two_product_response = client.post(
        "/product",
        json={
            "ProductName": "Seller Two Product",
            "Price": 75,
            "SupplierID": seller_two_supplier["SupplierID"],
        },
        headers=seller_two_headers,
    )
    assert seller_two_product_response.status_code == 200
    seller_two_product_id = seller_two_product_response.json()["ProductID"]

    seller_one_products = client.get("/product", headers=seller_one_headers)
    assert seller_one_products.status_code == 200
    seller_one_product_ids = {product["ProductID"] for product in seller_one_products.json()}
    assert seller_one_product_id in seller_one_product_ids
    assert seller_two_product_id not in seller_one_product_ids

    seller_one_own_product = client.get(f"/product/{seller_one_product_id}", headers=seller_one_headers)
    assert seller_one_own_product.status_code == 200

    seller_one_foreign_product = client.get(f"/product/{seller_two_product_id}", headers=seller_one_headers)
    assert seller_one_foreign_product.status_code == 404
