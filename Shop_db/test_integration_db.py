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

FLOW_STATE: dict[str, object] = {}


def _state_set(key: str, value: object) -> None:
    FLOW_STATE[key] = value


def _state_get(key: str) -> object:
    assert key in FLOW_STATE, f"Missing state '{key}'. Run integration tests from test_01..."
    return FLOW_STATE[key]


@pytest.fixture(scope="module")
def db_session():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="module")
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


def _register_user(
    client: TestClient,
    *,
    role: str = "user",
    password: str = "002233Tt",
    username_prefix: str = "user",
) -> dict[str, object]:
    suffix = random.randint(1, 1_000_000)
    username = f"{username_prefix}_{suffix}"
    email = f"{username}@example.com"

    response = client.post(
        "/register",
        params={
            "username": username,
            "email": email,
            "password": password,
            "phone": "1234567",
            "country": "UA",
            "role": role,
        },
    )
    assert response.status_code == 200, response.text

    payload = response.json()
    return {
        "CustomerID": payload["customer_id"],
        "SupplierID": payload.get("supplier_id"),
        "Name": username,
        "Email": email,
        "Password": password,
    }


def _login_user(client: TestClient, username: str, password: str) -> str:
    response = client.post(
        "/login",
        data={"username": username, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_01_seller_register_account(client):
    seller = _register_user(client, role="seller", username_prefix="seller_stage")
    assert seller["SupplierID"] is not None
    _state_set("seller", seller)


def test_02_seller_login(client):
    seller = _state_get("seller")
    token = _login_user(client, seller["Name"], seller["Password"])
    _state_set("seller_headers", _auth_headers(token))


def test_03_seller_profile_read_and_update(client):
    seller = _state_get("seller")
    seller_headers = _state_get("seller_headers")

    read_profile = client.get(f"/customer/{seller['CustomerID']}", headers=seller_headers)
    assert read_profile.status_code == 200
    assert read_profile.json()["CustomerID"] == seller["CustomerID"]

    update_profile = client.put(
        f"/customer/{seller['CustomerID']}",
        json={"Phone": "5551234", "Country": "PL"},
        headers=seller_headers,
    )
    assert update_profile.status_code == 200
    assert update_profile.json()["Country"] == "PL"


def test_04_seller_supplier_manipulations(client):
    seller = _state_get("seller")
    seller_headers = _state_get("seller_headers")
    supplier_id = seller["SupplierID"]

    suppliers = client.get("/supplier", headers=seller_headers)
    assert suppliers.status_code == 200
    supplier_payload = suppliers.json()
    assert len(supplier_payload) == 1
    assert supplier_payload[0]["SupplierID"] == supplier_id

    update_supplier = client.put(
        f"/supplier/{supplier_id}",
        json={
            "SupplierName": "Seller Stage Supplier",
            "Address": "Warsaw, PL",
            "Phone": "9998887",
        },
        headers=seller_headers,
    )
    assert update_supplier.status_code == 200
    assert update_supplier.json()["SupplierName"] == "Seller Stage Supplier"

    create_supplier_forbidden = client.post(
        "/supplier",
        json={
            "SupplierName": "Should Not Be Created",
            "Address": "Kyiv, UA",
            "Phone": "1234567",
        },
        headers=seller_headers,
    )
    assert create_supplier_forbidden.status_code == 403


def test_05_seller_create_products(client):
    seller = _state_get("seller")
    seller_headers = _state_get("seller_headers")
    supplier_id = seller["SupplierID"]

    main_product_response = client.post(
        "/product",
        json={
            "ProductName": "iPhone Stage",
            "Price": 1000,
            "AvailableQuantity": 10,
            "SupplierID": supplier_id,
        },
        headers=seller_headers,
    )
    assert main_product_response.status_code == 200
    main_product = main_product_response.json()

    extra_product_response = client.post(
        "/product",
        json={
            "ProductName": "Watch Stage",
            "Price": 200,
            "AvailableQuantity": 6,
            "SupplierID": supplier_id,
        },
        headers=seller_headers,
    )
    assert extra_product_response.status_code == 200
    extra_product = extra_product_response.json()

    seller_products = client.get("/product", headers=seller_headers)
    assert seller_products.status_code == 200
    seller_product_ids = {item["ProductID"] for item in seller_products.json()}
    assert main_product["ProductID"] in seller_product_ids
    assert extra_product["ProductID"] in seller_product_ids

    supplier_products = client.get(f"/supplier/{supplier_id}/products", headers=seller_headers)
    assert supplier_products.status_code == 200
    supplier_product_ids = {item["ProductID"] for item in supplier_products.json()}
    assert main_product["ProductID"] in supplier_product_ids
    assert extra_product["ProductID"] in supplier_product_ids

    _state_set("main_product", main_product)
    _state_set("extra_product", extra_product)


def test_06_seller_update_and_delete_extra_product(client):
    seller = _state_get("seller")
    seller_headers = _state_get("seller_headers")
    supplier_id = seller["SupplierID"]
    main_product = _state_get("main_product")
    extra_product = _state_get("extra_product")

    update_product = client.put(
        f"/product/{extra_product['ProductID']}",
        json={
            "ProductName": "Watch Stage Updated",
            "Price": 250,
            "AvailableQuantity": 8,
            "SupplierID": supplier_id,
        },
        headers=seller_headers,
    )
    assert update_product.status_code == 200
    assert float(update_product.json()["Price"]) == 250.0

    delete_product = client.delete(f"/product/{extra_product['ProductID']}", headers=seller_headers)
    assert delete_product.status_code == 200

    main_product_read = client.get(f"/product/{main_product['ProductID']}", headers=seller_headers)
    assert main_product_read.status_code == 200
    main_product_payload = main_product_read.json()
    assert main_product_payload["AvailableQuantity"] == 10
    assert "ApproxPriceUSD" in main_product_payload
    assert "ApproxPriceEUR" in main_product_payload


def test_07_customer_register_account(client):
    customer = _register_user(client, role="user", username_prefix="customer_stage")
    _state_set("customer", customer)


def test_08_customer_login(client):
    customer = _state_get("customer")
    token = _login_user(client, customer["Name"], customer["Password"])
    _state_set("customer_headers", _auth_headers(token))


def test_09_customer_profile_and_product_permissions(client):
    customer = _state_get("customer")
    customer_headers = _state_get("customer_headers")
    seller = _state_get("seller")
    main_product = _state_get("main_product")

    read_profile = client.get(f"/customer/{customer['CustomerID']}", headers=customer_headers)
    assert read_profile.status_code == 200

    update_profile = client.put(
        f"/customer/{customer['CustomerID']}",
        json={"Phone": "7776665", "Country": "DE"},
        headers=customer_headers,
    )
    assert update_profile.status_code == 200
    assert update_profile.json()["Country"] == "DE"

    products = client.get("/product", headers=customer_headers)
    assert products.status_code == 200
    assert any(item["ProductID"] == main_product["ProductID"] for item in products.json())

    read_main_product = client.get(f"/product/{main_product['ProductID']}", headers=customer_headers)
    assert read_main_product.status_code == 200

    create_product_forbidden = client.post(
        "/product",
        json={
            "ProductName": "Customer Forbidden Product",
            "Price": 10,
            "AvailableQuantity": 2,
            "SupplierID": seller["SupplierID"],
        },
        headers=customer_headers,
    )
    assert create_product_forbidden.status_code == 403

    update_supplier_forbidden = client.put(
        f"/supplier/{seller['SupplierID']}",
        json={"SupplierName": "Customer Forbidden Supplier", "Address": "Berlin, DE", "Phone": "5554443"},
        headers=customer_headers,
    )
    assert update_supplier_forbidden.status_code == 403


def test_10_customer_create_first_order_and_detail(client):
    customer = _state_get("customer")
    customer_headers = _state_get("customer_headers")
    seller_headers = _state_get("seller_headers")
    main_product = _state_get("main_product")

    order_response = client.post(
        "/order",
        json={"OrderDate": datetime.now().isoformat(), "Status": "Pending"},
        headers=customer_headers,
    )
    assert order_response.status_code == 200
    order = order_response.json()
    assert order["CustomerID"] == customer["CustomerID"]
    _state_set("order_1", order)

    create_detail = client.post(
        "/orderdetail",
        json={
            "OrderID": order["OrderID"],
            "ProductID": main_product["ProductID"],
            "Quantity": 3,
            "ShippingAddress": "Main street 1",
        },
        headers=customer_headers,
    )
    assert create_detail.status_code == 200
    detail = create_detail.json()
    _state_set("detail_1", detail)

    product_after_detail = client.get(f"/product/{main_product['ProductID']}", headers=seller_headers)
    assert product_after_detail.status_code == 200
    assert product_after_detail.json()["AvailableQuantity"] == 7


def test_11_customer_update_order_detail(client):
    customer_headers = _state_get("customer_headers")
    seller_headers = _state_get("seller_headers")
    main_product = _state_get("main_product")
    detail = _state_get("detail_1")

    update_detail = client.put(
        f"/orderdetail/{detail['OrderDetailID']}",
        json={"Quantity": 4, "ShippingAddress": "Main street 2"},
        headers=customer_headers,
    )
    assert update_detail.status_code == 200
    assert update_detail.json()["Quantity"] == 4

    product_after_update = client.get(f"/product/{main_product['ProductID']}", headers=seller_headers)
    assert product_after_update.status_code == 200
    assert product_after_update.json()["AvailableQuantity"] == 6


def test_12_customer_courier_flow(client):
    customer = _state_get("customer")
    customer_headers = _state_get("customer_headers")
    order = _state_get("order_1")

    create_courier = client.post(
        "/courier",
        json={
            "Name": "Fast Courier",
            "Country": "UA",
            "Price": 50,
            "OrderID": order["OrderID"],
        },
        headers=customer_headers,
    )
    assert create_courier.status_code == 200
    courier = create_courier.json()
    _state_set("courier", courier)

    read_courier = client.get(f"/courier/{courier['CourierID']}", headers=customer_headers)
    assert read_courier.status_code == 200

    update_courier = client.put(
        f"/courier/{courier['CourierID']}",
        json={"Price": 55},
        headers=customer_headers,
    )
    assert update_courier.status_code == 200
    assert float(update_courier.json()["Price"]) == 55.0

    read_courier_hier = client.get(
        f"/customer/{customer['CustomerID']}/orders/{order['OrderID']}/courier",
        headers=customer_headers,
    )
    assert read_courier_hier.status_code == 200
    assert read_courier_hier.json()["CourierID"] == courier["CourierID"]


def test_13_customer_payment_flow(client):
    customer = _state_get("customer")
    customer_headers = _state_get("customer_headers")
    order = _state_get("order_1")

    create_payment = client.post(
        "/payment",
        json={
            "OrderID": order["OrderID"],
            "Status": "Pending",
            "Amount": 4000,
            "PaymentDate": datetime.now().isoformat(),
        },
        headers=customer_headers,
    )
    assert create_payment.status_code == 200
    payment = create_payment.json()
    _state_set("payment", payment)

    read_payment = client.get(f"/payment/{payment['PaymentID']}", headers=customer_headers)
    assert read_payment.status_code == 200

    update_payment = client.put(
        f"/payment/{payment['PaymentID']}",
        json={"Status": "Paid", "Amount": 4000},
        headers=customer_headers,
    )
    assert update_payment.status_code == 200
    assert update_payment.json()["Status"] == "Paid"

    read_payment_hier = client.get(
        f"/customer/{customer['CustomerID']}/orders/{order['OrderID']}/payment",
        headers=customer_headers,
    )
    assert read_payment_hier.status_code == 200
    assert read_payment_hier.json()["PaymentID"] == payment["PaymentID"]


def test_14_customer_gift_flow(client):
    customer = _state_get("customer")
    customer_headers = _state_get("customer_headers")
    order = _state_get("order_1")
    payment = _state_get("payment")

    create_gift = client.post(
        "/gift",
        json={"Amount": 50, "Unit": "USD", "Type": "Gift", "PaymentID": payment["PaymentID"]},
        headers=customer_headers,
    )
    assert create_gift.status_code == 200
    gift = create_gift.json()
    _state_set("gift", gift)

    update_gift = client.put(
        f"/gift/{gift['GiftID']}",
        json={"Amount": 80},
        headers=customer_headers,
    )
    assert update_gift.status_code == 200
    assert float(update_gift.json()["Amount"]) == 80.0

    read_gift = client.get(f"/gift/{gift['GiftID']}", headers=customer_headers)
    assert read_gift.status_code == 200

    read_gifts_hier = client.get(
        f"/customer/{customer['CustomerID']}/orders/{order['OrderID']}/payment/{payment['PaymentID']}/gifts",
        headers=customer_headers,
    )
    assert read_gifts_hier.status_code == 200
    assert any(item["GiftID"] == gift["GiftID"] for item in read_gifts_hier.json())


def test_15_customer_complete_first_order_and_create_second_order(client):
    customer_headers = _state_get("customer_headers")
    seller_headers = _state_get("seller_headers")
    main_product = _state_get("main_product")
    order_1 = _state_get("order_1")

    complete_order = client.put(
        f"/order/{order_1['OrderID']}",
        json={"Status": "Completed"},
        headers=customer_headers,
    )
    assert complete_order.status_code == 200
    assert complete_order.json()["Status"] == "Completed"

    order_2_response = client.post(
        "/order",
        json={"OrderDate": datetime.now().isoformat(), "Status": "Pending"},
        headers=customer_headers,
    )
    assert order_2_response.status_code == 200
    order_2 = order_2_response.json()
    _state_set("order_2", order_2)

    create_second_detail = client.post(
        "/orderdetail",
        json={
            "OrderID": order_2["OrderID"],
            "ProductID": main_product["ProductID"],
            "Quantity": 1,
            "ShippingAddress": "Main street 3",
        },
        headers=customer_headers,
    )
    assert create_second_detail.status_code == 200

    product_after_second_order = client.get(f"/product/{main_product['ProductID']}", headers=seller_headers)
    assert product_after_second_order.status_code == 200
    assert product_after_second_order.json()["AvailableQuantity"] == 5


def test_16_seller_statistics_are_correct(client):
    seller = _state_get("seller")
    seller_headers = _state_get("seller_headers")
    main_product = _state_get("main_product")

    summary_response = client.get("/analytics/seller/summary", headers=seller_headers)
    assert summary_response.status_code == 200
    summary = summary_response.json()
    assert summary["SellerCustomerID"] == seller["CustomerID"]
    assert summary["OwnedProductsCount"] == 1
    assert summary["SoldUnits"] == 5
    assert summary["SalesAmount"] == 5000.0
    assert summary["OrdersWithSales"] == 2
    assert summary["CompletedOrders"] == 1
    assert summary["PendingOrders"] == 1
    assert summary["ShippedOrders"] == 0
    assert summary["CancelledOrders"] == 0

    top_products_response = client.get("/analytics/seller/top-products?limit=3", headers=seller_headers)
    assert top_products_response.status_code == 200
    top_products = top_products_response.json()
    assert len(top_products) >= 1
    assert top_products[0]["ProductID"] == main_product["ProductID"]
    assert top_products[0]["SoldUnits"] == 5
    assert top_products[0]["SalesAmount"] == 5000.0


def test_17_customer_cannot_access_seller_statistics(client):
    customer_headers = _state_get("customer_headers")
    response = client.get("/analytics/seller/summary", headers=customer_headers)
    assert response.status_code == 403


def test_18_seller_statistics_are_isolated_from_other_sellers(client):
    seller_headers = _state_get("seller_headers")

    second_seller = _register_user(client, role="seller", username_prefix="seller_second_stage")
    second_token = _login_user(client, second_seller["Name"], second_seller["Password"])
    second_headers = _auth_headers(second_token)

    second_product = client.post(
        "/product",
        json={
            "ProductName": "Second Seller Product",
            "Price": 700,
            "AvailableQuantity": 5,
            "SupplierID": second_seller["SupplierID"],
        },
        headers=second_headers,
    )
    assert second_product.status_code == 200
    second_product_id = second_product.json()["ProductID"]

    second_summary_response = client.get("/analytics/seller/summary", headers=second_headers)
    assert second_summary_response.status_code == 200
    second_summary = second_summary_response.json()
    assert second_summary["SellerCustomerID"] == second_seller["CustomerID"]
    assert second_summary["SoldUnits"] == 0
    assert second_summary["SalesAmount"] == 0.0
    assert second_summary["OrdersWithSales"] == 0
    assert second_summary["CompletedOrders"] == 0
    assert second_summary["PendingOrders"] == 0

    first_summary_response = client.get("/analytics/seller/summary", headers=seller_headers)
    assert first_summary_response.status_code == 200
    first_summary = first_summary_response.json()
    assert first_summary["SoldUnits"] == 5
    assert first_summary["SalesAmount"] == 5000.0

    first_seller_cannot_open_second_product = client.get(f"/product/{second_product_id}", headers=seller_headers)
    assert first_seller_cannot_open_second_product.status_code == 404
