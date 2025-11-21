import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from database import Base, get_db
from main import app
import random

# ---------- In-memory SQLite ----------
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base.metadata.create_all(bind=engine)

# ---------- Fixtures ----------
@pytest.fixture(scope="function")
def db_session():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            db_session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

# ======================================================
# CUSTOMER TESTS
# ======================================================
def test_create_customer(client):
    email = f"user{random.randint(1,10000)}@example.com"
    r = client.post("/customer", json={
        "Name": "John Doe",
        "Email": email,
        "Phone": "344-678-2578",
        "Country": "USA"
    })
    assert r.status_code == 200
    assert r.json()["Name"] == "John Doe"

def test_read_customer(client):
    email = f"user{random.randint(1,10000)}@example.com"
    c = client.post("/customer", json={"Name":"A","Email":email,"Phone":"123","Country":"USA"}).json()
    r = client.get(f"/customer/{c['CustomerID']}")
    assert r.status_code == 200
    assert r.json()["Email"] == email

def test_update_customer(client):
    email = f"user{random.randint(1,10000)}@example.com"
    c = client.post("/customer", json={"Name":"A","Email":email,"Phone":"123","Country":"USA"}).json()
    r = client.put(f"/customer/{c['CustomerID']}", json={"Name":"Updated"})
    assert r.status_code == 200
    assert r.json()["Name"] == "Updated"

def test_delete_customer(client):
    email = f"user{random.randint(1,10000)}@example.com"
    c = client.post("/customer", json={"Name":"A","Email":email,"Phone":"123","Country":"USA"}).json()
    r = client.delete(f"/customer/{c['CustomerID']}")
    assert r.status_code == 200

# ======================================================
# SUPPLIER TESTS
# ======================================================
def test_create_supplier(client):
    r = client.post("/supplier", json={"SupplierName":"S","Address":"Addr","Phone":"123"}).json()
    assert r["SupplierName"] == "S"

def test_read_supplier(client):
    s = client.post("/supplier", json={"SupplierName":"S","Address":"Addr"}).json()
    r = client.get(f"/supplier/{s['SupplierID']}")
    assert r.status_code == 200

def test_update_supplier(client):
    s = client.post("/supplier", json={"SupplierName":"S","Address":"Addr"}).json()
    r = client.put(f"/supplier/{s['SupplierID']}", json={"SupplierName":"Updated"}).json()
    assert r["SupplierName"] == "Updated"

def test_delete_supplier(client):
    s = client.post("/supplier", json={"SupplierName":"S"}).json()
    r = client.delete(f"/supplier/{s['SupplierID']}")
    assert r.status_code == 200

# ======================================================
# PRODUCT TESTS
# ======================================================
def test_create_product(client):
    s = client.post("/supplier", json={"SupplierName":"S"}).json()
    p = client.post("/product", json={"ProductName":"P","Price":10,"SupplierID":s["SupplierID"]}).json()
    assert p["ProductName"] == "P"

def test_read_product(client):
    s = client.post("/supplier", json={"SupplierName":"S"}).json()
    p = client.post("/product", json={"ProductName":"P","Price":10,"SupplierID":s["SupplierID"]}).json()
    r = client.get(f"/product/{p['ProductID']}")
    assert r.status_code == 200

def test_update_product(client):
    s = client.post("/supplier", json={"SupplierName":"S"}).json()
    p = client.post("/product", json={"ProductName":"P","Price":10,"SupplierID":s["SupplierID"]}).json()
    r = client.put(f"/product/{p['ProductID']}", json={"ProductName":"Updated"}).json()
    assert r["ProductName"] == "Updated"

def test_delete_product(client):
    s = client.post("/supplier", json={"SupplierName":"S"}).json()
    p = client.post("/product", json={"ProductName":"P","Price":10,"SupplierID":s["SupplierID"]}).json()
    r = client.delete(f"/product/{p['ProductID']}")
    assert r.status_code == 200

# ======================================================
# COURIER TESTS
# ======================================================
def test_create_courier(client):
    r = client.post("/courier", json={"Name":"DHL","Country":"DE","Price":25}).json()
    assert r["Name"] == "DHL"

def test_read_courier(client):
    c = client.post("/courier", json={"Name":"DHL"}).json()
    r = client.get(f"/courier/{c['CourierID']}")
    assert r.status_code == 200

def test_update_courier(client):
    c = client.post("/courier", json={"Name":"DHL"}).json()
    r = client.put(f"/courier/{c['CourierID']}", json={"Name":"Updated"}).json()
    assert r["Name"] == "Updated"

def test_delete_courier(client):
    c = client.post("/courier", json={"Name":"DHL"}).json()
    r = client.delete(f"/courier/{c['CourierID']}")
    assert r.status_code == 200

# ======================================================
# ORDER TESTS
# ======================================================
def test_create_order(client):
    cust = client.post("/customer", json={"Name":"A","Email":f"{random.randint(1,1000)}@a.com","Phone":"123","Country":"UA"}).json()
    r = client.post("/order", json={
        "OrderDate":"2025-10-22T00:00:00",
        "ShippingAddress":"Addr",
        "Status":"Pending",
        "CustomerID":cust["CustomerID"]
    }).json()
    assert r["CustomerID"] == cust["CustomerID"]

def test_read_order(client):
    cust = client.post("/customer", json={"Name":"A","Email":f"{random.randint(1,1000)}@a.com","Phone":"123","Country":"UA"}).json()
    o = client.post("/order", json={"OrderDate":"2025-10-22","ShippingAddress":"Addr","Status":"Pending","CustomerID":cust["CustomerID"]}).json()
    r = client.get(f"/order/{o['OrderID']}")
    assert r.status_code == 200

def test_update_order(client):
    cust = client.post("/customer", json={"Name":"A","Email":f"{random.randint(1,1000)}@a.com","Phone":"123","Country":"UA"}).json()
    o = client.post("/order", json={"OrderDate":"2025-10-22","ShippingAddress":"Addr","Status":"Pending","CustomerID":cust["CustomerID"]}).json()
    r = client.put(f"/order/{o['OrderID']}", json={"ShippingAddress":"Updated"}).json()
    assert r["ShippingAddress"] == "Updated"

def test_delete_order(client):
    cust = client.post("/customer", json={"Name":"A","Email":f"{random.randint(1,1000)}@a.com","Phone":"123","Country":"UA"}).json()
    o = client.post("/order", json={"OrderDate":"2025-10-22","ShippingAddress":"Addr","Status":"Pending","CustomerID":cust["CustomerID"]}).json()
    r = client.delete(f"/order/{o['OrderID']}")
    assert r.status_code == 200

# ======================================================
# PAYMENT TESTS
# ======================================================
def test_create_payment(client):
    cust = client.post("/customer", json={"Name":"A","Email":f"{random.randint(1,1000)}@a.com"}).json()
    o = client.post("/order", json={"OrderDate":"2025-10-22","ShippingAddress":"Addr","Status":"Pending","CustomerID":cust["CustomerID"]}).json()
    r = client.post("/payment", json={"OrderID":o["OrderID"],"Status":"Pending","Amount":100,"PaymentDate":"2025-10-22T00:00:00"}).json()
    assert r["Amount"] == 100

def test_read_payment(client):
    cust = client.post("/customer", json={"Name":"A","Email":f"{random.randint(1,1000)}@a.com"}).json()
    o = client.post("/order", json={"OrderDate":"2025-10-22","ShippingAddress":"Addr","Status":"Pending","CustomerID":cust["CustomerID"]}).json()
    p = client.post("/payment", json={"OrderID":o["OrderID"],"Status":"Pending","Amount":100,"PaymentDate":"2025-10-22T00:00:00"}).json()
    r = client.get(f"/payment/{p['PaymentID']}")
    assert r.status_code == 200

def test_update_payment(client):
    cust = client.post("/customer", json={"Name":"A","Email":f"{random.randint(1,1000)}@a.com"}).json()
    o = client.post("/order", json={"OrderDate":"2025-10-22","ShippingAddress":"Addr","Status":"Pending","CustomerID":cust["CustomerID"]}).json()
    p = client.post("/payment", json={"OrderID":o["OrderID"],"Status":"Pending","Amount":100,"PaymentDate":"2025-10-22T00:00:00"}).json()
    r = client.put(f"/payment/{p['PaymentID']}", json={"Amount":200}).json()
    assert r["Amount"] == 200

def test_delete_payment(client):
    cust = client.post("/customer", json={"Name":"A","Email":f"{random.randint(1,1000)}@a.com"}).json()
    o = client.post("/order", json={"OrderDate":"2025-10-22","ShippingAddress":"Addr","Status":"Pending","CustomerID":cust["CustomerID"]}).json()
    p = client.post("/payment", json={"OrderID":o["OrderID"],"Status":"Pending","Amount":100,"PaymentDate":"2025-10-22T00:00:00"}).json()
    r = client.delete(f"/payment/{p['PaymentID']}")
    assert r.status_code == 200

# ======================================================
# ORDERDETAIL TESTS
# ======================================================
def test_create_orderdetail(client):
    cust = client.post("/customer", json={"Name":"A","Email":f"{random.randint(1,1000)}@a.com"}).json()
    s = client.post("/supplier", json={"SupplierName":"S"}).json()
    prod = client.post("/product", json={"ProductName":"P","Price":10,"SupplierID":s["SupplierID"]}).json()
    o = client.post("/order", json={"OrderDate":"2025-10-22","ShippingAddress":"Addr","Status":"Pending","CustomerID":cust["CustomerID"]}).json()
    od = client.post("/orderdetail", json={"OrderID":o["OrderID"],"ProductID":prod["ProductID"],"Quantity":2}).json()
    assert od["Quantity"] == 2

def test_read_orderdetail(client):
    cust = client.post("/customer", json={"Name":"A","Email":f"{random.randint(1,1000)}@a.com"}).json()
    s = client.post("/supplier", json={"SupplierName":"S"}).json()
    prod = client.post("/product", json={"ProductName":"P","Price":10,"SupplierID":s["SupplierID"]}).json()
    o = client.post("/order", json={"OrderDate":"2025-10-22","ShippingAddress":"Addr","Status":"Pending","CustomerID":cust["CustomerID"]}).json()
    od = client.post("/orderdetail", json={"OrderID":o["OrderID"],"ProductID":prod["ProductID"],"Quantity":2}).json()
    r = client.get(f"/orderdetail/{od['OrderDetailID']}")
    assert r.status_code == 200

def test_update_orderdetail(client):
    cust = client.post("/customer", json={"Name":"A","Email":f"{random.randint(1,1000)}@a.com"}).json()
    s = client.post("/supplier", json={"SupplierName":"S"}).json()
    prod = client.post("/product", json={"ProductName":"P","Price":10,"SupplierID":s["SupplierID"]}).json()
    o = client.post("/order", json={"OrderDate":"2025-10-22","ShippingAddress":"Addr","Status":"Pending","CustomerID":cust["CustomerID"]}).json()
    od = client.post("/orderdetail", json={"OrderID":o["OrderID"],"ProductID":prod["ProductID"],"Quantity":2}).json()
    r = client.put(f"/orderdetail/{od['OrderDetailID']}", json={"Quantity":5}).json()
    assert r["Quantity"] == 5

def test_delete_orderdetail(client):
    cust = client.post("/customer", json={"Name":"A","Email":f"{random.randint(1,1000)}@a.com"}).json()
    s = client.post("/supplier", json={"SupplierName":"S"}).json()
    prod = client.post("/product", json={"ProductName":"P","Price":10,"SupplierID":s["SupplierID"]}).json()
    o = client.post("/order", json={"OrderDate":"2025-10-22","ShippingAddress":"Addr","Status":"Pending","CustomerID":cust["CustomerID"]}).json()
    od = client.post("/orderdetail", json={"OrderID":o["OrderID"],"ProductID":prod["ProductID"],"Quantity":2}).json()
    r = client.delete(f"/orderdetail/{od['OrderDetailID']}")
    assert r.status_code == 200

# ======================================================
# GIFT TESTS
# ======================================================
def test_create_gift(client):
    cust = client.post("/customer", json={"Name":"A","Email":f"{random.randint(1,1000)}@a.com"}).json()
    o = client.post("/order", json={"OrderDate":"2025-10-22","ShippingAddress":"Addr","Status":"Pending","CustomerID":cust["CustomerID"]}).json()
    p = client.post("/payment", json={"OrderID":o["OrderID"],"Status":"Pending","Amount":100,"PaymentDate":"2025-10-22T00:00:00"}).json()
    g = client.post("/gift", json={"Amount":50,"Unit":"USD","Type":"Gift","PaymentID":p["PaymentID"]}).json()
    assert g["Amount"] == 50

def test_read_gift(client):
    cust = client.post("/customer", json={"Name":"A","Email":f"{random.randint(1,1000)}@a.com"}).json()
    o = client.post("/order", json={"OrderDate":"2025-10-22","ShippingAddress":"Addr","Status":"Pending","CustomerID":cust["CustomerID"]}).json()
    p = client.post("/payment", json={"OrderID":o["OrderID"],"Status":"Pending","Amount":100,"PaymentDate":"2025-10-22T00:00:00"}).json()
    g = client.post("/gift", json={"Amount":50,"Unit":"USD","Type":"Gift","PaymentID":p["PaymentID"]}).json()
    r = client.get(f"/gift/{g['GiftID']}")
    assert r.status_code == 200

def test_update_gift(client):
    cust = client.post("/customer", json={"Name":"A","Email":f"{random.randint(1,1000)}@a.com"}).json()
    o = client.post("/order", json={"OrderDate":"2025-10-22","ShippingAddress":"Addr","Status":"Pending","CustomerID":cust["CustomerID"]}).json()
    p = client.post("/payment", json={"OrderID":o["OrderID"],"Status":"Pending","Amount":100,"PaymentDate":"2025-10-22T00:00:00"}).json()
    g = client.post("/gift", json={"Amount":50,"Unit":"USD","Type":"Gift","PaymentID":p["PaymentID"]}).json()
    r = client.put(f"/gift/{g['GiftID']}", json={"Amount":100}).json()
    assert r["Amount"] == 100

def test_delete_gift(client):
    cust = client.post("/customer", json={"Name":"A","Email":f"{random.randint(1,1000)}@a.com"}).json()
    o = client.post("/order", json={"OrderDate":"2025-10-22","ShippingAddress":"Addr","Status":"Pending","CustomerID":cust["CustomerID"]}).json()
    p = client.post("/payment", json={"OrderID":o["OrderID"],"Status":"Pending","Amount":100,"PaymentDate":"2025-10-22T00:00:00"}).json()
    g = client.post("/gift", json={"Amount":50,"Unit":"USD","Type":"Gift","PaymentID":p["PaymentID"]}).json()
    r = client.delete(f"/gift/{g['GiftID']}")
    assert r.status_code == 200

def test_analytics_top_customers(client):
    r = client.get("/analytics/top_customers")
    assert r.status_code in (200, 404)

def test_analytics_sales_by_country(client):
    r = client.get("/analytics/sales_by_country")
    assert r.status_code in (200, 404)

def test_analytics_top_products(client):
    r = client.get("/analytics/top_products")
    assert r.status_code in (200, 404)

def test_analytics_revenue_by_supplier(client):
    r = client.get("/analytics/revenue_by_supplier")
    assert r.status_code in (200, 404)
