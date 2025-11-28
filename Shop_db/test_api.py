import pytest, random
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from database import Base, get_db
from main import app
import random
from datetime import datetime
from routers.auth import get_current_user

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

    from models import User
    def override_get_current_user():
        return User(id=1, username="testuser", email="test@example.com", password_hash="fakehash")

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

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
        "Phone": "1234567",
        "Country": "USA"
    })
    assert r.status_code == 200
    assert r.json()["Name"] == "John Doe"

def test_read_customer(client):
    email = f"user{random.randint(1,10000)}@example.com"
    c = client.post("/customer", json={
        "Name": "Johnny",
        "Email": email,
        "Phone": "1234567",
        "Country": "USA"
    }).json()
    r = client.get(f"/customer/{c['CustomerID']}")
    assert r.status_code == 200
    assert r.json()["Email"] == email

def test_update_customer(client):
    email = f"user{random.randint(1,10000)}@example.com"
    c = client.post("/customer", json={"Name":"Johnathan","Email":email,"Phone":"1234567","Country":"USA"}).json()
    r = client.put(f"/customer/{c['CustomerID']}", json={"Name":"UpdatedName"}).json()
    assert r["Name"] == "UpdatedName"

def test_delete_customer(client):
    email = f"user{random.randint(1,10000)}@example.com"
    c = client.post("/customer", json={"Name":"Jonathan","Email":email,"Phone":"1234567","Country":"USA"}).json()
    r = client.delete(f"/customer/{c['CustomerID']}")
    assert r.status_code == 200

# ======================================================
# SUPPLIER TESTS
# ======================================================
def test_create_supplier(client):
    r = client.post("/supplier", json={"SupplierName":"SupplierX","Address":"AddressLine1","Phone":"1234567"}).json()
    assert r["SupplierName"] == "SupplierX"

def test_read_supplier(client):
    s = client.post("/supplier", json={"SupplierName":"SupplierY","Address":"AddressLine2"}).json()
    r = client.get(f"/supplier/{s['SupplierID']}")
    assert r.status_code == 200

def test_update_supplier(client):
    s = client.post("/supplier", json={"SupplierName":"SupplierZ","Address":"AddressLine3"}).json()
    r = client.put(f"/supplier/{s['SupplierID']}", json={"SupplierName":"UpdatedSupplier"}).json()
    assert r["SupplierName"] == "UpdatedSupplier"

def test_delete_supplier(client):
    s = client.post("/supplier", json={"SupplierName":"SupplierDelete"}).json()
    r = client.delete(f"/supplier/{s['SupplierID']}")
    assert r.status_code == 200

# ======================================================
# PRODUCT TESTS
# ======================================================
def test_create_product(client):
    s = client.post("/supplier", json={"SupplierName":"SupplierProd"}).json()
    p = client.post("/product", json={"ProductName":"ProductX","Price":10,"SupplierID":s["SupplierID"]}).json()
    assert p["ProductName"] == "ProductX"

def test_read_product(client):
    s = client.post("/supplier", json={"SupplierName":"SupplierReadProd"}).json()
    p = client.post("/product", json={"ProductName":"ProductRead","Price":20,"SupplierID":s["SupplierID"]}).json()
    r = client.get(f"/product/{p['ProductID']}")
    assert r.status_code == 200

def test_update_product(client):
    s = client.post("/supplier", json={"SupplierName":"SupplierUpdateProd"}).json()
    p = client.post("/product", json={"ProductName":"ProductUpdate","Price":30,"SupplierID":s["SupplierID"]}).json()
    r = client.put(f"/product/{p['ProductID']}", json={"ProductName":"UpdatedProduct","Price":p["Price"],"SupplierID":p["SupplierID"]}).json()
    assert r["ProductName"] == "UpdatedProduct"


def test_delete_product(client):
    s = client.post("/supplier", json={"SupplierName":"SupplierDelProd"}).json()
    p = client.post("/product", json={"ProductName":"ProductDel","Price":40,"SupplierID":s["SupplierID"]}).json()
    r = client.delete(f"/product/{p['ProductID']}")
    assert r.status_code == 200

# ======================================================
# ORDER TESTS
# ======================================================
def test_create_order(client):
    cust = client.post("/customer", json={"Name":"CustomerOrder","Email":f"{random.randint(1,1000)}@example.com","Phone":"1234567","Country":"UA"}).json()
    r = client.post("/order", json={
        "OrderDate": datetime.now().isoformat(),
        "ShippingAddress":"AddressOrder",
        "Status":"Pending",
        "CustomerID":cust["CustomerID"]
    }).json()
    assert r["CustomerID"] == cust["CustomerID"]

def test_read_order(client):
    cust = client.post("/customer", json={"Name":"CustomerRead","Email":f"{random.randint(1,1000)}@example.com","Phone":"1234567","Country":"UA"}).json()
    o = client.post("/order", json={"OrderDate": datetime.now().isoformat(),"ShippingAddress":"AddressRead","Status":"Pending","CustomerID":cust["CustomerID"]}).json()
    r = client.get(f"/order/{o['OrderID']}")
    assert r.status_code == 200

def test_update_order(client):
    cust = client.post("/customer", json={"Name":"CustomerUpdate","Email":f"{random.randint(1,1000)}@example.com","Phone":"1234567","Country":"UA"}).json()
    o = client.post("/order", json={"OrderDate": datetime.now().isoformat(),"ShippingAddress":"AddressUpdate","Status":"Pending","CustomerID":cust["CustomerID"]}).json()
    r = client.put(f"/order/{o['OrderID']}", json={"ShippingAddress":"UpdatedAddress"}).json()
    assert r["ShippingAddress"] == "UpdatedAddress"

def test_delete_order(client):
    cust = client.post("/customer", json={"Name":"CustomerDel","Email":f"{random.randint(1,1000)}@example.com","Phone":"1234567","Country":"UA"}).json()
    o = client.post("/order", json={"OrderDate": datetime.now().isoformat(),"ShippingAddress":"AddressDel","Status":"Pending","CustomerID":cust["CustomerID"]}).json()
    r = client.delete(f"/order/{o['OrderID']}")
    assert r.status_code == 200

# ======================================================
# PAYMENT TESTS
# ======================================================
def test_create_payment(client):
    cust = client.post("/customer", json={"Name":"CustomerPay","Email":f"{random.randint(1,1000)}@example.com","Phone":"1234567","Country":"UA"}).json()
    o = client.post("/order", json={"OrderDate": datetime.now().isoformat(),"ShippingAddress":"AddressPay","Status":"Pending","CustomerID":cust["CustomerID"]}).json()
    r = client.post("/payment", json={"OrderID":o["OrderID"],"Status":"Pending","Amount":100,"PaymentDate":datetime.now().isoformat()}).json()
    assert r["Amount"] == 100

def test_read_payment(client):
    cust = client.post("/customer", json={"Name":"CustomerPayRead","Email":f"{random.randint(1,1000)}@example.com","Phone":"1234567","Country":"UA"}).json()
    o = client.post("/order", json={"OrderDate": datetime.now().isoformat(),"ShippingAddress":"AddressPayRead","Status":"Pending","CustomerID":cust["CustomerID"]}).json()
    p = client.post("/payment", json={"OrderID":o["OrderID"],"Status":"Pending","Amount":100,"PaymentDate":datetime.now().isoformat()}).json()
    r = client.get(f"/payment/{p['PaymentID']}")
    assert r.status_code == 200

def test_update_payment(client):
    cust = client.post("/customer", json={"Name":"CustomerPayUpdate","Email":f"{random.randint(1,1000)}@example.com","Phone":"1234567","Country":"UA"}).json()
    o = client.post("/order", json={"OrderDate": datetime.now().isoformat(),"ShippingAddress":"AddressPayUpdate","Status":"Pending","CustomerID":cust["CustomerID"]}).json()
    p = client.post("/payment", json={"OrderID":o["OrderID"],"Status":"Pending","Amount":100,"PaymentDate":datetime.now().isoformat()}).json()
    r = client.put(f"/payment/{p['PaymentID']}", json={"Amount":200}).json()
    assert r["Amount"] == 200

def test_delete_payment(client):
    cust = client.post("/customer", json={"Name":"CustomerPayDel","Email":f"{random.randint(1,1000)}@example.com","Phone":"1234567","Country":"UA"}).json()
    o = client.post("/order", json={"OrderDate": datetime.now().isoformat(),"ShippingAddress":"AddressPayDel","Status":"Pending","CustomerID":cust["CustomerID"]}).json()
    p = client.post("/payment", json={"OrderID":o["OrderID"],"Status":"Pending","Amount":100,"PaymentDate":datetime.now().isoformat()}).json()
    r = client.delete(f"/payment/{p['PaymentID']}")
    assert r.status_code == 200

# ======================================================
# ORDERDETAIL TESTS
# ======================================================
def test_create_orderdetail(client):
    cust = client.post("/customer", json={"Name":"CustomerOD","Email":f"{random.randint(1,1000)}@example.com","Phone":"1234567","Country":"UA"}).json()
    s = client.post("/supplier", json={"SupplierName":"SupplierOD"}).json()
    prod = client.post("/product", json={"ProductName":"ProductOD","Price":10,"SupplierID":s["SupplierID"]}).json()
    o = client.post("/order", json={"OrderDate": datetime.now().isoformat(),"ShippingAddress":"AddressOD","Status":"Pending","CustomerID":cust["CustomerID"]}).json()
    od = client.post("/orderdetail", json={"OrderID":o["OrderID"],"ProductID":prod["ProductID"],"Quantity":2}).json()
    assert od["Quantity"] == 2

def test_read_orderdetail(client):
    cust = client.post("/customer", json={"Name":"CustomerODRead","Email":f"{random.randint(1,1000)}@example.com","Phone":"1234567","Country":"UA"}).json()
    s = client.post("/supplier", json={"SupplierName":"SupplierODRead"}).json()
    prod = client.post("/product", json={"ProductName":"ProductODRead","Price":10,"SupplierID":s["SupplierID"]}).json()
    o = client.post("/order", json={"OrderDate": datetime.now().isoformat(),"ShippingAddress":"AddressODRead","Status":"Pending","CustomerID":cust["CustomerID"]}).json()
    od = client.post("/orderdetail", json={"OrderID":o["OrderID"],"ProductID":prod["ProductID"],"Quantity":2}).json()
    r = client.get(f"/orderdetail/{od['OrderDetailID']}")
    assert r.status_code == 200

def test_update_orderdetail(client):
    cust = client.post("/customer", json={"Name":"CustomerODUpdate","Email":f"{random.randint(1,1000)}@example.com","Phone":"1234567","Country":"UA"}).json()
    s = client.post("/supplier", json={"SupplierName":"SupplierODUpdate"}).json()
    prod = client.post("/product", json={"ProductName":"ProductODUpdate","Price":10,"SupplierID":s["SupplierID"]}).json()
    o = client.post("/order", json={"OrderDate": datetime.now().isoformat(),"ShippingAddress":"AddressODUpdate","Status":"Pending","CustomerID":cust["CustomerID"]}).json()
    od = client.post("/orderdetail", json={"OrderID":o["OrderID"],"ProductID":prod["ProductID"],"Quantity":2}).json()
    r = client.put(f"/orderdetail/{od['OrderDetailID']}", json={"Quantity":5}).json()
    assert r["Quantity"] == 5

def test_delete_orderdetail(client):
    cust = client.post("/customer", json={"Name":"CustomerODDel","Email":f"{random.randint(1,1000)}@example.com","Phone":"1234567","Country":"UA"}).json()
    s = client.post("/supplier", json={"SupplierName":"SupplierODDel"}).json()
    prod = client.post("/product", json={"ProductName":"ProductODDel","Price":10,"SupplierID":s["SupplierID"]}).json()
    o = client.post("/order", json={"OrderDate": datetime.now().isoformat(),"ShippingAddress":"AddressODDel","Status":"Pending","CustomerID":cust["CustomerID"]}).json()
    od = client.post("/orderdetail", json={"OrderID":o["OrderID"],"ProductID":prod["ProductID"],"Quantity":2}).json()
    r = client.delete(f"/orderdetail/{od['OrderDetailID']}")
    assert r.status_code == 200

# ======================================================
# GIFT TESTS
# ======================================================
def test_create_gift(client):
    cust = client.post("/customer", json={"Name":"CustomerGift","Email":f"{random.randint(1,1000)}@example.com","Phone":"1234567","Country":"UA"}).json()
    o = client.post("/order", json={"OrderDate": datetime.now().isoformat(),"ShippingAddress":"AddressGift","Status":"Pending","CustomerID":cust["CustomerID"]}).json()
    p = client.post("/payment", json={"OrderID":o["OrderID"],"Status":"Pending","Amount":100,"PaymentDate":datetime.now().isoformat()}).json()
    g = client.post("/gift", json={"Amount":50,"Unit":"USD","Type":"Gift","PaymentID":p["PaymentID"]}).json()
    assert g["Amount"] == 50

def test_read_gift(client):
    cust = client.post("/customer", json={"Name":"CustomerGiftRead","Email":f"{random.randint(1,1000)}@example.com","Phone":"1234567","Country":"UA"}).json()
    o = client.post("/order", json={"OrderDate": datetime.now().isoformat(),"ShippingAddress":"AddressGiftRead","Status":"Pending","CustomerID":cust["CustomerID"]}).json()
    p = client.post("/payment", json={"OrderID":o["OrderID"],"Status":"Pending","Amount":100,"PaymentDate":datetime.now().isoformat()}).json()
    g = client.post("/gift", json={"Amount":50,"Unit":"USD","Type":"Gift","PaymentID":p["PaymentID"]}).json()
    r = client.get(f"/gift/{g['GiftID']}")
    assert r.status_code == 200

def test_update_gift(client):
    cust = client.post("/customer", json={"Name":"CustomerGiftUpdate","Email":f"{random.randint(1,1000)}@example.com","Phone":"1234567","Country":"UA"}).json()
    o = client.post("/order", json={"OrderDate": datetime.now().isoformat(),"ShippingAddress":"AddressGiftUpdate","Status":"Pending","CustomerID":cust["CustomerID"]}).json()
    p = client.post("/payment", json={"OrderID":o["OrderID"],"Status":"Pending","Amount":100,"PaymentDate":datetime.now().isoformat()}).json()
    g = client.post("/gift", json={"Amount":50,"Unit":"USD","Type":"Gift","PaymentID":p["PaymentID"]}).json()
    r = client.put(f"/gift/{g['GiftID']}", json={"Amount":100}).json()
    assert r["Amount"] == 100

def test_delete_gift(client):
    cust = client.post("/customer", json={"Name":"CustomerGiftDel","Email":f"{random.randint(1,1000)}@example.com","Phone":"1234567","Country":"UA"}).json()
    o = client.post("/order", json={"OrderDate": datetime.now().isoformat(),"ShippingAddress":"AddressGiftDel","Status":"Pending","CustomerID":cust["CustomerID"]}).json()
    p = client.post("/payment", json={"OrderID":o["OrderID"],"Status":"Pending","Amount":100,"PaymentDate":datetime.now().isoformat()}).json()
    g = client.post("/gift", json={"Amount":50,"Unit":"USD","Type":"Gift","PaymentID":p["PaymentID"]}).json()
    r = client.delete(f"/gift/{g['GiftID']}")
    assert r.status_code == 200


# ======================================================
# ANALYTICS TESTS
# ======================================================

def test_create_random_order_analytics(client):

    email = f"user{random.randint(1,10000)}@example.com"
    cust = client.post("/customer", json={
        "Name": "AnalyticsCustomer",
        "Email": email,
        "Phone": "1234567",
        "Country": "UA"
    }).json()

    supplier = client.post("/supplier", json={"SupplierName": "AnalyticsSupplier"}).json()

    client.post("/product", json={
        "ProductName": "AnalyticsProduct",
        "Price": 50,
        "SupplierID": supplier["SupplierID"]
    }).json()

    r = client.post(f"/analytics/create-random-order/{cust['CustomerID']}").json()

    assert "message" in r
    assert r["message"] == "Random order created successfully ✅"
    assert "order" in r
    assert r["order"]["CustomerName"] == "AnalyticsCustomer"
    assert r["order"]["CustomerEmail"] == email


def test_order_summary_analytics(client):
    for i in range(3):
        email = f"user{i}_{random.randint(1,1000)}@example.com"
        cust = client.post("/customer", json={
            "Name": f"Customer{i}",
            "Email": email,
            "Phone": f"12345{i}",
            "Country": "UA"
        }).json()
        client.post(f"/analytics/create-random-order/{cust['CustomerID']}").json()

    r = client.get("/analytics/orders-summary")
    assert r.status_code == 200
    assert "order_summary" in r.json()
    summary = r.json()["order_summary"]
    assert len(summary) >= 3
    for row in summary:
        assert "OrderID" in row
        assert "CustomerName" in row
        assert "Status" in row
        assert "OrderDate" in row
