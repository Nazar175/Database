import pytest
from fastapi.testclient import TestClient
from main import app
from datetime import datetime
from decimal import Decimal

client = TestClient(app)

# ---- Глобальні змінні для створених записів ----
customer_id = 1
order_id = None
payment_id = None
gift_id = None
courier_id = None

# ---------- 1) Orders ----------
def test_create_order():
    global order_id
    payload = {
        "order_date": datetime.now().isoformat(),
        "shipping_address": "Kyiv, Khreshchatyk 1",
        "status": "Pending"
    }
    response = client.post(f"/customer/{customer_id}/orders", json=payload)
    assert response.status_code == 201, response.text
    data = response.json()
    order_id = data["OrderID"]
    assert data["ShippingAddress"] == payload["shipping_address"]

def test_get_orders():
    response = client.get(f"/customer/{customer_id}/orders")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_update_order():
    payload = {"status": "Shipped"}
    response = client.put(f"/customer/{customer_id}/orders/{order_id}", json=payload)
    assert response.status_code == 200
    assert response.json()["Status"] == "Shipped"

def test_delete_order_invalid():
    response = client.delete(f"/customer/{customer_id}/orders/99999")
    assert response.status_code == 404

# ---------- 2) Payment ----------
def test_create_payment():
    global payment_id
    payload = {
        "status": "Paid",
        "amount": "200.50",
        "payment_date": datetime.now().isoformat()
    }
    response = client.post(f"/customer/{customer_id}/orders/{order_id}/payment", json=payload)
    assert response.status_code == 201
    payment_id = response.json()["PaymentID"]

def test_get_payment():
    response = client.get(f"/customer/{customer_id}/orders/{order_id}/payment")
    assert response.status_code == 200

def test_update_payment():
    payload = {"status": "Refunded"}
    response = client.put(f"/customer/{customer_id}/orders/{order_id}/payment/{payment_id}", json=payload)
    assert response.status_code == 200
    assert response.json()["Status"] == "Refunded"

# ---------- 3) Gifts ----------
def test_create_gift():
    global gift_id
    payload = {
        "amount": "50.00",
        "expares_date": "2026-01-01T00:00:00",
        "type": "Certificate",
        "unit": "USD"
    }
    response = client.post(f"/customer/{customer_id}/orders/{order_id}/payment/{payment_id}/gifts", json=payload)
    assert response.status_code == 201
    gift_id = response.json()["GiftID"]

def test_get_gifts():
    response = client.get(f"/customer/{customer_id}/orders/{order_id}/payment/{payment_id}/gifts")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_update_gift():
    payload = {"amount": "75.00"}
    response = client.put(f"/customer/{customer_id}/orders/{order_id}/payment/{payment_id}/gifts/{gift_id}", json=payload)
    assert response.status_code == 200
    assert Decimal(response.json()["Amount"]) == Decimal("75.00")

# ---------- 4) Courier ----------
def test_create_courier():
    global courier_id
    payload = {
        "name": "Nova Poshta",
        "country": "Ukraine",
        "price": "100.00"
    }
    response = client.post(f"/customer/{customer_id}/orders/{order_id}/courier", json=payload)
    assert response.status_code == 201
    courier_id = response.json()["CourierID"]

def test_get_courier():
    response = client.get(f"/customer/{customer_id}/orders/{order_id}/courier")
    assert response.status_code == 200

def test_update_courier():
    payload = {"price": "150.00"}
    response = client.put(f"/customer/{customer_id}/orders/{order_id}/courier/{courier_id}", json=payload)
    assert response.status_code == 200
    assert Decimal(response.json()["Price"]) == Decimal("150.00")

# ---------- 5) Delete everything ----------
def test_delete_gift():
    response = client.delete(f"/customer/{customer_id}/orders/{order_id}/payment/{payment_id}/gifts/{gift_id}")
    assert response.status_code == 200

def test_delete_payment():
    response = client.delete(f"/customer/{customer_id}/orders/{order_id}/payment/{payment_id}")
    assert response.status_code == 200

def test_delete_courier():
    response = client.delete(f"/customer/{customer_id}/orders/{order_id}/courier/{courier_id}")
    assert response.status_code == 200

def test_delete_order():
    response = client.delete(f"/customer/{customer_id}/orders/{order_id}")
    assert response.status_code == 200
