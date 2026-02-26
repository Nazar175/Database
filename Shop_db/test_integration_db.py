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


def _register_customer(client, username: str | None = None, password: str = "002233Tt"):
    suffix = random.randint(1, 1_000_000)
    username = username or f"user_{suffix}"
    email = f"{username}@example.com"
    response = client.post(
        "/register",
        params={
            "username": username,
            "email": email,
            "password": password,
            "phone": "1234567",
            "country": "UA",
        },
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
        auth_customer = _register_customer(c, username=f"auth_{random.randint(1, 1_000_000)}")
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
            "ShippingAddress": "Main street 1",
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
        },
    ).json()
    detail_2 = client.post(
        "/orderdetail",
        json={
            "OrderID": order_id,
            "ProductID": product_ids[1],
            "Quantity": 2,
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
