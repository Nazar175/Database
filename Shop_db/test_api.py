import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_customer_crud():
    # CREATE
    resp = client.post("/customer", json={
        "name": "Test User",
        "email": "testuser@example.com",
        "phone": "+380991234567",
        "country": "Ukraine"
    })
    assert resp.status_code == 200
    cust = resp.json()
    assert cust["name"] == "Test User"
    customer_id = cust["customerID"]  # поле в JSON точно таке

    # READ
    resp = client.get(f"/customer/{customer_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Test User"

    # UPDATE
    resp = client.put(f"/customer/{customer_id}", json={"name": "Updated User"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated User"

    # DELETE
    resp = client.delete(f"/customer/{customer_id}")
    assert resp.status_code == 200
    resp = client.get(f"/customer/{customer_id}")
    assert resp.status_code == 404


def test_supplier_crud():
    # CREATE
    resp = client.post("/supplier", json={"supplierName": "Test Supplier"})
    assert resp.status_code == 200
    supplier = resp.json()
    supplier_id = supplier["supplierID"]

    # READ
    resp = client.get(f"/supplier/{supplier_id}")
    assert resp.status_code == 200
    assert resp.json()["supplierName"] == "Test Supplier"

    # UPDATE
    resp = client.put(f"/supplier/{supplier_id}", json={"supplierName": "Updated Supplier"})
    assert resp.status_code == 200
    assert resp.json()["supplierName"] == "Updated Supplier"

    # DELETE
    resp = client.delete(f"/supplier/{supplier_id}")
    assert resp.status_code == 200
    resp = client.get(f"/supplier/{supplier_id}")
    assert resp.status_code == 404


def test_product_crud():
    # CREATE
    resp = client.post("/product", json={
        "productName": "Test Product",
        "price": 123.45,
        "supplierID": None  # точно як у Pydantic-моделі
    })
    assert resp.status_code == 200
    product = resp.json()
    product_id = product["productID"]

    # READ
    resp = client.get(f"/product/{product_id}")
    assert resp.status_code == 200
    assert resp.json()["productName"] == "Test Product"

    # UPDATE
    resp = client.put(f"/product/{product_id}", json={"price": 200.0})
    assert resp.status_code == 200
    assert resp.json()["price"] == 200.0

    # DELETE
    resp = client.delete(f"/product/{product_id}")
    assert resp.status_code == 200
    resp = client.get(f"/product/{product_id}")
    assert resp.status_code == 404


def test_order_crud():
    # CREATE customer for order
    cust_resp = client.post("/customer", json={"name": "OrderUser", "email": "orderuser@example.com"})
    assert cust_resp.status_code == 200
    cust = cust_resp.json()
    customer_id = cust["customerID"]

    # CREATE order
    resp = client.post("/order", json={"customerID": customer_id})
    assert resp.status_code == 200
    order = resp.json()
    order_id = order["orderID"]

    # READ
    resp = client.get(f"/order/{order_id}")
    assert resp.status_code == 200
    assert resp.json()["customerID"] == customer_id

    # UPDATE
    resp = client.put(f"/order/{order_id}", json={"customerID": customer_id})
    assert resp.status_code == 200

    # DELETE
    resp = client.delete(f"/order/{order_id}")
    assert resp.status_code == 200
    resp = client.get(f"/order/{order_id}")
    assert resp.status_code == 404
