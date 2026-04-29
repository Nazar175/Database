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
    admin_user = db_session.query(Customer).filter(Customer.Email == "test-admin@example.com").first()
    if admin_user is None:
        admin_user = Customer(
            Name="testadmin",
            Email="test-admin@example.com",
            Role="admin",
            password_hash="fakehash",
        )
        db_session.add(admin_user)
        db_session.commit()
        db_session.refresh(admin_user)
    admin_user_id = admin_user.CustomerID

    def override_get_current_user():
        current_admin = db_session.query(Customer).filter(Customer.CustomerID == admin_user_id).first()
        if current_admin is not None:
            return current_admin
        return Customer(
            CustomerID=admin_user_id,
            Name="testadmin",
            Email="test-admin@example.com",
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
    role: str = "user",
):
    response = client.post(
        "/register",
        params={
            "username": name,
            "email": email,
            "password": password,
            "phone": phone,
            "country": country,
            "role": role,
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
        "SupplierID": payload.get("supplier_id"),
    }


def _override_current_user(customer_id: int, name: str, email: str, role: str = "user"):
    from models import Customer

    def override_get_current_user():
        return Customer(
            CustomerID=customer_id,
            Name=name,
            Email=email,
            Role=role,
            password_hash="fakehash",
        )

    app.dependency_overrides[get_current_user] = override_get_current_user

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
    assert "AvailableQuantity" in p

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


def test_orderdetail_decreases_product_available_quantity(client):
    s = client.post("/supplier", json={"SupplierName":"SupplierStock"}).json()
    p = client.post(
        "/product",
        json={"ProductName": "iPhone", "Price": 1000, "SupplierID": s["SupplierID"], "AvailableQuantity": 5},
    ).json()

    o = client.post("/order", json={"OrderDate": datetime.now().isoformat(), "Status": "Pending", "CustomerID": 1}).json()
    od = client.post(
        "/orderdetail",
        json={"OrderID": o["OrderID"], "ProductID": p["ProductID"], "Quantity": 3, "ShippingAddress": "Kyiv"},
    )
    assert od.status_code == 200

    updated_product = client.get(f"/product/{p['ProductID']}").json()
    assert updated_product["AvailableQuantity"] == 2

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
    prod = client.post(
        "/product",
        json={"ProductName":"ProductOD","Price":10,"SupplierID":s["SupplierID"],"AvailableQuantity":10},
    ).json()
    o = client.post("/order", json={"OrderDate": datetime.now().isoformat(),"Status":"Pending","CustomerID":cust["CustomerID"]}).json()
    od = client.post("/orderdetail", json={"OrderID":o["OrderID"],"ProductID":prod["ProductID"],"Quantity":2,"ShippingAddress":"AddressOD"}).json()
    assert od["Quantity"] == 2
    assert od["ShippingAddress"] == "AddressOD"

def test_read_orderdetail(client):
    cust = _register_customer(client, name="CustomerODRead", email=f"{random.randint(1,1000)}@example.com")
    s = client.post("/supplier", json={"SupplierName":"SupplierODRead"}).json()
    prod = client.post(
        "/product",
        json={"ProductName":"ProductODRead","Price":10,"SupplierID":s["SupplierID"],"AvailableQuantity":10},
    ).json()
    o = client.post("/order", json={"OrderDate": datetime.now().isoformat(),"Status":"Pending","CustomerID":cust["CustomerID"]}).json()
    od = client.post("/orderdetail", json={"OrderID":o["OrderID"],"ProductID":prod["ProductID"],"Quantity":2,"ShippingAddress":"AddressODRead"}).json()
    r = client.get(f"/orderdetail/{od['OrderDetailID']}")
    assert r.status_code == 200

def test_update_orderdetail(client):
    cust = _register_customer(client, name="CustomerODUpdate", email=f"{random.randint(1,1000)}@example.com")
    s = client.post("/supplier", json={"SupplierName":"SupplierODUpdate"}).json()
    prod = client.post(
        "/product",
        json={"ProductName":"ProductODUpdate","Price":10,"SupplierID":s["SupplierID"],"AvailableQuantity":10},
    ).json()
    o = client.post("/order", json={"OrderDate": datetime.now().isoformat(),"Status":"Pending","CustomerID":cust["CustomerID"]}).json()
    od = client.post("/orderdetail", json={"OrderID":o["OrderID"],"ProductID":prod["ProductID"],"Quantity":2,"ShippingAddress":"AddressODUpdate"}).json()
    r = client.put(f"/orderdetail/{od['OrderDetailID']}", json={"Quantity":5,"ShippingAddress":"UpdatedODAddress"}).json()
    assert r["Quantity"] == 5
    assert r["ShippingAddress"] == "UpdatedODAddress"

def test_delete_orderdetail(client):
    cust = _register_customer(client, name="CustomerODDel", email=f"{random.randint(1,1000)}@example.com")
    s = client.post("/supplier", json={"SupplierName":"SupplierODDel"}).json()
    prod = client.post(
        "/product",
        json={"ProductName":"ProductODDel","Price":10,"SupplierID":s["SupplierID"],"AvailableQuantity":10},
    ).json()
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
    supplier = client.post("/supplier", json={"SupplierName": "AnalyticsSummarySupplier"}).json()
    seeded_product = client.post(
        "/product",
        json={
            "ProductName": "AnalyticsSummaryProduct",
            "Price": 100,
            "SupplierID": supplier["SupplierID"],
            "AvailableQuantity": 50,
        },
    )
    assert seeded_product.status_code == 200

    created_with_detail = 0
    attempts = 0
    while created_with_detail < 3 and attempts < 10:
        email = f"user{attempts}_{random.randint(1,1000)}@example.com"
        cust = _register_customer(client, name=f"Customer{attempts}", email=email, phone=f"12345{attempts}")
        create_random_order = client.post(f"/analytics/create-random-order/{cust['CustomerID']}")
        assert create_random_order.status_code == 200
        if create_random_order.json()["order"]["ShippingAddress"] is not None:
            created_with_detail += 1
        attempts += 1

    assert created_with_detail >= 3

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


def test_seller_analytics_summary_and_top_products(client):
    seller = _register_customer(
        client,
        name=f"seller_{random.randint(1,10000)}",
        email=f"seller_{random.randint(1,10000)}@example.com",
        role="seller",
    )
    assert seller["SupplierID"] is not None

    _override_current_user(
        customer_id=seller["CustomerID"],
        name=seller["Name"],
        email=seller["Email"],
        role="user",
    )

    product = client.post(
        "/product",
        json={
            "ProductName": "Seller iPhone",
            "Price": 1000,
            "SupplierID": seller["SupplierID"],
            "AvailableQuantity": 10,
        },
    ).json()

    order_completed = client.post(
        "/order",
        json={"OrderDate": datetime.now().isoformat(), "Status": "Pending"},
    ).json()
    create_detail_completed = client.post(
        "/orderdetail",
        json={
            "OrderID": order_completed["OrderID"],
            "ProductID": product["ProductID"],
            "Quantity": 3,
            "ShippingAddress": "Seller Address",
        },
    )
    assert create_detail_completed.status_code == 200

    order_pending = client.post(
        "/order",
        json={"OrderDate": datetime.now().isoformat(), "Status": "Pending"},
    ).json()
    create_detail_pending = client.post(
        "/orderdetail",
        json={
            "OrderID": order_pending["OrderID"],
            "ProductID": product["ProductID"],
            "Quantity": 1,
            "ShippingAddress": "Seller Address 2",
        },
    )
    assert create_detail_pending.status_code == 200

    update_order_completed = client.put(
        f"/order/{order_completed['OrderID']}",
        json={"Status": "Completed"},
    )
    assert update_order_completed.status_code == 200

    summary_response = client.get("/analytics/seller/summary")
    assert summary_response.status_code == 200
    summary = summary_response.json()
    assert summary["SellerCustomerID"] == seller["CustomerID"]
    assert summary["OwnedProductsCount"] == 1
    assert summary["SoldUnits"] == 4
    assert summary["SalesAmount"] == 4000.0
    assert summary["OrdersWithSales"] == 2
    assert summary["CompletedOrders"] == 1
    assert summary["PendingOrders"] == 1
    assert summary["ShippedOrders"] == 0
    assert summary["CancelledOrders"] == 0

    top_products_response = client.get("/analytics/seller/top-products?limit=5")
    assert top_products_response.status_code == 200
    top_products = top_products_response.json()
    assert len(top_products) >= 1
    assert top_products[0]["ProductID"] == product["ProductID"]
    assert top_products[0]["SoldUnits"] == 4
    assert top_products[0]["SalesAmount"] == 4000.0


def test_seller_analytics_forbidden_for_non_seller(client):
    response = client.get("/analytics/seller/summary")
    assert response.status_code == 403

