import pytest, random
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from database import Base, get_db
from main import app
import random
from datetime import datetime
from routers.customer import get_current_user

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

    from models import Customer
    def override_get_current_user():
        return Customer(
            CustomerID=1,
            Name="testuser",
            Email="test@example.com",
            Role="admin",
            password_hash="fakehash",
        )

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


def _register_customer(
    client,
    name: str,
    email: str,
    phone: str = "1234567",
    country: str = "UA",
    password: str = "002233Tt",
):
    response = client.post(
        "/register",
        params={
            "username": name,
            "email": email,
            "password": password,
            "phone": phone,
            "country": country,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    return {
        "CustomerID": payload["customer_id"],
        "Name": name,
        "Email": email,
        "Phone": phone,
        "Country": country,
    }

# ======================================================
# CUSTOMER TESTS
# ======================================================
def test_register_customer(client):
    email = f"user{random.randint(1,10000)}@example.com"
    customer = _register_customer(client, name="John Doe", email=email, country="USA")
    assert customer["Name"] == "John Doe"

def test_read_customer(client):
    email = f"user{random.randint(1,10000)}@example.com"
    c = _register_customer(client, name="Johnny", email=email, country="USA")
    r = client.get(f"/customer/{c['CustomerID']}")
    assert r.status_code == 200
    assert r.json()["Email"] == email

def test_update_customer(client):
    email = f"user{random.randint(1,10000)}@example.com"
    c = _register_customer(client, name="Johnathan", email=email, country="USA")
    r = client.put(f"/customer/{c['CustomerID']}", json={"Name":"UpdatedName"}).json()
    assert r["Name"] == "UpdatedName"

def test_delete_customer(client):
    email = f"user{random.randint(1,10000)}@example.com"
    c = _register_customer(client, name="Jonathan", email=email, country="USA")
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

def test_read_supplier_products(client):
    s = client.post("/supplier", json={"SupplierName":"SupplierWithProducts"}).json()
    client.post("/product", json={"ProductName":"Product1","Price":10,"SupplierID":s["SupplierID"]}).json()
    client.post("/product", json={"ProductName":"Product2","Price":20,"SupplierID":s["SupplierID"]}).json()
    endpoints = [
        f"/supplier/{s['SupplierID']}/products",
        f"/suppliers/{s['SupplierID']}/products",
        f"/supplier/products/{s['SupplierID']}",
        f"/product/supplier/{s['SupplierID']}",
        f"/products/supplier/{s['SupplierID']}",
        f"/products?supplier_id={s['SupplierID']}",
        f"/product?supplier_id={s['SupplierID']}"
    ]

    r = None
    for ep in endpoints:
        r = client.get(ep)
        if r.status_code == 200:
            break

    assert r is not None
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
    payload = r.json()
    assert "ApproxPriceUSD" in payload
    assert "ApproxPriceEUR" in payload

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
    cust = _register_customer(client, name="CustomerOrder", email=f"{random.randint(1,1000)}@example.com")
    r = client.post("/order", json={
        "OrderDate": datetime.now().isoformat(),
        "Status":"Pending",
        "CustomerID":cust["CustomerID"]
    }).json()
    assert r["CustomerID"] == cust["CustomerID"]

def test_read_order(client):
    cust = _register_customer(client, name="CustomerRead", email=f"{random.randint(1,1000)}@example.com")
    o = client.post("/order", json={"OrderDate": datetime.now().isoformat(),"Status":"Pending","CustomerID":cust["CustomerID"]}).json()
    r = client.get(f"/order/{o['OrderID']}")
    assert r.status_code == 200

def test_update_order(client):
    cust = _register_customer(client, name="CustomerUpdate", email=f"{random.randint(1,1000)}@example.com")
    o = client.post("/order", json={"OrderDate": datetime.now().isoformat(),"Status":"Pending","CustomerID":cust["CustomerID"]}).json()
    r = client.put(f"/order/{o['OrderID']}", json={"Status":"Completed"}).json()
    assert r["Status"] == "Completed"

def test_delete_order(client):
    cust = _register_customer(client, name="CustomerDel", email=f"{random.randint(1,1000)}@example.com")
    o = client.post("/order", json={"OrderDate": datetime.now().isoformat(),"Status":"Pending","CustomerID":cust["CustomerID"]}).json()
    r = client.delete(f"/order/{o['OrderID']}")
    assert r.status_code == 200

# ======================================================
# PAYMENT TESTS
# ======================================================
def test_create_payment(client):
    cust = _register_customer(client, name="CustomerPay", email=f"{random.randint(1,1000)}@example.com")
    o = client.post("/order", json={"OrderDate": datetime.now().isoformat(),"Status":"Pending","CustomerID":cust["CustomerID"]}).json()
    r = client.post("/payment", json={"OrderID":o["OrderID"],"Status":"Pending","Amount":100,"PaymentDate":datetime.now().isoformat()}).json()
    assert r["Amount"] == 100

def test_read_payment(client):
    cust = _register_customer(client, name="CustomerPayRead", email=f"{random.randint(1,1000)}@example.com")
    o = client.post("/order", json={"OrderDate": datetime.now().isoformat(),"Status":"Pending","CustomerID":cust["CustomerID"]}).json()
    p = client.post("/payment", json={"OrderID":o["OrderID"],"Status":"Pending","Amount":100,"PaymentDate":datetime.now().isoformat()}).json()
    r = client.get(f"/payment/{p['PaymentID']}")
    assert r.status_code == 200

def test_update_payment(client):
    cust = _register_customer(client, name="CustomerPayUpdate", email=f"{random.randint(1,1000)}@example.com")
    o = client.post("/order", json={"OrderDate": datetime.now().isoformat(),"Status":"Pending","CustomerID":cust["CustomerID"]}).json()
    p = client.post("/payment", json={"OrderID":o["OrderID"],"Status":"Pending","Amount":100,"PaymentDate":datetime.now().isoformat()}).json()
    r = client.put(f"/payment/{p['PaymentID']}", json={"Amount":200}).json()
    assert r["Amount"] == 200

def test_delete_payment(client):
    cust = _register_customer(client, name="CustomerPayDel", email=f"{random.randint(1,1000)}@example.com")
    o = client.post("/order", json={"OrderDate": datetime.now().isoformat(),"Status":"Pending","CustomerID":cust["CustomerID"]}).json()
    p = client.post("/payment", json={"OrderID":o["OrderID"],"Status":"Pending","Amount":100,"PaymentDate":datetime.now().isoformat()}).json()
    r = client.delete(f"/payment/{p['PaymentID']}")
    assert r.status_code == 200

# ======================================================
# ORDERDETAIL TESTS
# ======================================================
def test_create_orderdetail(client):
    cust = _register_customer(client, name="CustomerOD", email=f"{random.randint(1,1000)}@example.com")
    s = client.post("/supplier", json={"SupplierName":"SupplierOD"}).json()
    prod = client.post("/product", json={"ProductName":"ProductOD","Price":10,"SupplierID":s["SupplierID"]}).json()
    o = client.post("/order", json={"OrderDate": datetime.now().isoformat(),"Status":"Pending","CustomerID":cust["CustomerID"]}).json()
    od = client.post("/orderdetail", json={"OrderID":o["OrderID"],"ProductID":prod["ProductID"],"Quantity":2,"ShippingAddress":"AddressOD"}).json()
    assert od["Quantity"] == 2
    assert od["ShippingAddress"] == "AddressOD"

def test_read_orderdetail(client):
    cust = _register_customer(client, name="CustomerODRead", email=f"{random.randint(1,1000)}@example.com")
    s = client.post("/supplier", json={"SupplierName":"SupplierODRead"}).json()
    prod = client.post("/product", json={"ProductName":"ProductODRead","Price":10,"SupplierID":s["SupplierID"]}).json()
    o = client.post("/order", json={"OrderDate": datetime.now().isoformat(),"Status":"Pending","CustomerID":cust["CustomerID"]}).json()
    od = client.post("/orderdetail", json={"OrderID":o["OrderID"],"ProductID":prod["ProductID"],"Quantity":2,"ShippingAddress":"AddressODRead"}).json()
    r = client.get(f"/orderdetail/{od['OrderDetailID']}")
    assert r.status_code == 200

def test_update_orderdetail(client):
    cust = _register_customer(client, name="CustomerODUpdate", email=f"{random.randint(1,1000)}@example.com")
    s = client.post("/supplier", json={"SupplierName":"SupplierODUpdate"}).json()
    prod = client.post("/product", json={"ProductName":"ProductODUpdate","Price":10,"SupplierID":s["SupplierID"]}).json()
    o = client.post("/order", json={"OrderDate": datetime.now().isoformat(),"Status":"Pending","CustomerID":cust["CustomerID"]}).json()
    od = client.post("/orderdetail", json={"OrderID":o["OrderID"],"ProductID":prod["ProductID"],"Quantity":2,"ShippingAddress":"AddressODUpdate"}).json()
    r = client.put(f"/orderdetail/{od['OrderDetailID']}", json={"Quantity":5,"ShippingAddress":"UpdatedODAddress"}).json()
    assert r["Quantity"] == 5
    assert r["ShippingAddress"] == "UpdatedODAddress"

def test_delete_orderdetail(client):
    cust = _register_customer(client, name="CustomerODDel", email=f"{random.randint(1,1000)}@example.com")
    s = client.post("/supplier", json={"SupplierName":"SupplierODDel"}).json()
    prod = client.post("/product", json={"ProductName":"ProductODDel","Price":10,"SupplierID":s["SupplierID"]}).json()
    o = client.post("/order", json={"OrderDate": datetime.now().isoformat(),"Status":"Pending","CustomerID":cust["CustomerID"]}).json()
    od = client.post("/orderdetail", json={"OrderID":o["OrderID"],"ProductID":prod["ProductID"],"Quantity":2,"ShippingAddress":"AddressODDel"}).json()
    r = client.delete(f"/orderdetail/{od['OrderDetailID']}")
    assert r.status_code == 200

# ======================================================
# GIFT TESTS
# ======================================================
def test_create_gift(client):
    cust = _register_customer(client, name="CustomerGift", email=f"{random.randint(1,1000)}@example.com")
    o = client.post("/order", json={"OrderDate": datetime.now().isoformat(),"Status":"Pending","CustomerID":cust["CustomerID"]}).json()
    p = client.post("/payment", json={"OrderID":o["OrderID"],"Status":"Pending","Amount":100,"PaymentDate":datetime.now().isoformat()}).json()
    g = client.post("/gift", json={"Amount":50,"Unit":"USD","Type":"Gift","PaymentID":p["PaymentID"]}).json()
    assert g["Amount"] == 50

def test_read_gift(client):
    cust = _register_customer(client, name="CustomerGiftRead", email=f"{random.randint(1,1000)}@example.com")
    o = client.post("/order", json={"OrderDate": datetime.now().isoformat(),"Status":"Pending","CustomerID":cust["CustomerID"]}).json()
    p = client.post("/payment", json={"OrderID":o["OrderID"],"Status":"Pending","Amount":100,"PaymentDate":datetime.now().isoformat()}).json()
    g = client.post("/gift", json={"Amount":50,"Unit":"USD","Type":"Gift","PaymentID":p["PaymentID"]}).json()
    r = client.get(f"/gift/{g['GiftID']}")
    assert r.status_code == 200

def test_update_gift(client):
    cust = _register_customer(client, name="CustomerGiftUpdate", email=f"{random.randint(1,1000)}@example.com")
    o = client.post("/order", json={"OrderDate": datetime.now().isoformat(),"Status":"Pending","CustomerID":cust["CustomerID"]}).json()
    p = client.post("/payment", json={"OrderID":o["OrderID"],"Status":"Pending","Amount":100,"PaymentDate":datetime.now().isoformat()}).json()
    g = client.post("/gift", json={"Amount":50,"Unit":"USD","Type":"Gift","PaymentID":p["PaymentID"]}).json()
    r = client.put(f"/gift/{g['GiftID']}", json={"Amount":100}).json()
    assert r["Amount"] == 100

def test_delete_gift(client):
    cust = _register_customer(client, name="CustomerGiftDel", email=f"{random.randint(1,1000)}@example.com")
    o = client.post("/order", json={"OrderDate": datetime.now().isoformat(),"Status":"Pending","CustomerID":cust["CustomerID"]}).json()
    p = client.post("/payment", json={"OrderID":o["OrderID"],"Status":"Pending","Amount":100,"PaymentDate":datetime.now().isoformat()}).json()
    g = client.post("/gift", json={"Amount":50,"Unit":"USD","Type":"Gift","PaymentID":p["PaymentID"]}).json()
    r = client.delete(f"/gift/{g['GiftID']}")
    assert r.status_code == 200


# ======================================================
# ANALYTICS TESTS
# ======================================================

def test_create_random_order_analytics(client):

    email = f"user{random.randint(1,10000)}@example.com"
    cust = _register_customer(client, name="AnalyticsCustomer", email=email)

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
        cust = _register_customer(client, name=f"Customer{i}", email=email, phone=f"12345{i}")
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

