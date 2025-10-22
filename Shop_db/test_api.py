import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base, get_db
from main import app

# ---------- In-memory SQLite ----------
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ---------- Fixtures ----------
@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

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
# ✅ CUSTOMER TESTS
# ======================================================
def test_customer_crud(client):
    # CREATE
    response = client.post("/customer", json={
        "Name": "John Doe",
        "Email": "john@example.com",
        "Phone": "1234567",
        "Country": "USA"
    })
    assert response.status_code == 200
    customer = response.json()
    cid = customer["CustomerID"]

    # READ
    assert client.get("/customer").status_code == 200
    assert client.get(f"/customer/{cid}").status_code == 200

    # UPDATE
    r = client.put(f"/customer/{cid}", json={"Name": "Updated"})
    assert r.status_code == 200
    assert r.json()["Name"] == "Updated"

    # DELETE
    r = client.delete(f"/customer/{cid}")
    assert r.status_code == 200
    assert r.json()["message"]

# ======================================================
# ✅ SUPPLIER TESTS
# ======================================================
def test_supplier_crud(client):
    response = client.post("/supplier", json={
        "supplierName": "ACME Corp",
        "Address": "Main St",
        "Phone": "555-555"
    })
    assert response.status_code == 200
    supplier = response.json()
    sid = supplier["SupplierID"]

    assert client.get("/supplier").status_code == 200
    assert client.get(f"/supplier/{sid}").status_code == 200

    r = client.put(f"/supplier/{sid}", json={"supplierName": "Updated Supplier"})
    assert r.status_code == 200
    assert r.json()["supplierName"] == "Updated Supplier"

    r = client.delete(f"/supplier/{sid}")
    assert r.status_code == 200

# ======================================================
# ✅ PRODUCT TESTS
# ======================================================
def test_product_crud(client):
    supplier = client.post("/supplier", json={
        "supplierName": "Best Supplier",
        "Address": "Nowhere 1",
        "Phone": "999"
    }).json()

    response = client.post("/product", json={
        "ProductName": "Phone",
        "Price": 999.99,
        "SupplierID": supplier["SupplierID"]
    })
    assert response.status_code == 200
    pid = response.json()["ProductID"]

    assert client.get(f"/product/{pid}").status_code == 200
    r = client.put(f"/product/{pid}", json={"ProductName": "Updated Phone"})
    assert r.status_code == 200
    assert r.json()["ProductName"] == "Updated Phone"

    r = client.delete(f"/product/{pid}")
    assert r.status_code == 200

# ======================================================
# ✅ COURIER TESTS
# ======================================================
def test_courier_crud(client):
    response = client.post("/courier", json={
        "CourierName": "DHL",
        "Phone": "111222",
        "VehicleNumber": "AA1234BB"
    })
    assert response.status_code == 200
    courier = response.json()
    cid = courier["CourierID"]

    assert client.get("/courier").status_code == 200
    assert client.get(f"/courier/{cid}").status_code == 200

    r = client.put(f"/courier/{cid}", json={"CourierName": "Updated DHL"})
    assert r.status_code == 200

    r = client.delete(f"/courier/{cid}")
    assert r.status_code == 200

# ======================================================
# ✅ ORDER TESTS
# ======================================================
def test_order_crud(client):
    customer = client.post("/customer", json={
        "Name": "Buyer",
        "Email": "buyer@mail.com",
        "Phone": "9999",
        "Country": "UK"
    }).json()

    courier = client.post("/courier", json={
        "CourierName": "NovaPoshta",
        "Phone": "444",
        "VehicleNumber": "CC1234DD"
    }).json()

    order = client.post("/order", json={
        "CustomerID": customer["CustomerID"],
        "CourierID": courier["CourierID"],
        "OrderDate": "2025-10-22",
        "TotalAmount": 500
    })
    assert order.status_code == 200
    oid = order.json()["OrderID"]

    assert client.get(f"/order/{oid}").status_code == 200
    r = client.put(f"/order/{oid}", json={"TotalAmount": 700})
    assert r.status_code == 200
    assert r.json()["TotalAmount"] == 700

    r = client.delete(f"/order/{oid}")
    assert r.status_code == 200

# ======================================================
# ✅ PAYMENT TESTS
# ======================================================
def test_payment_crud(client):
    customer = client.post("/customer", json={
        "Name": "PayUser",
        "Email": "pay@mail.com",
        "Phone": "888",
        "Country": "UA"
    }).json()

    order = client.post("/order", json={
        "CustomerID": customer["CustomerID"],
        "CourierID": None,
        "OrderDate": "2025-10-22",
        "TotalAmount": 200
    }).json()

    response = client.post("/payment", json={
        "OrderID": order["OrderID"],
        "Amount": 200,
        "PaymentDate": "2025-10-22",
        "PaymentMethod": "Card"
    })
    assert response.status_code == 200
    pid = response.json()["PaymentID"]

    assert client.get(f"/payment/{pid}").status_code == 200
    r = client.put(f"/payment/{pid}", json={"Amount": 300})
    assert r.status_code == 200
    assert r.json()["Amount"] == 300

    r = client.delete(f"/payment/{pid}")
    assert r.status_code == 200

# ======================================================
# ✅ GIFT TESTS
# ======================================================
def test_gift_crud(client):
    response = client.post("/gift", json={
        "GiftName": "Bonus Mug",
        "GiftType": "Accessory",
        "Price": 0
    })
    assert response.status_code == 200
    gift = response.json()
    gid = gift["GiftID"]

    assert client.get("/gift").status_code == 200
    assert client.get(f"/gift/{gid}").status_code == 200

    r = client.put(f"/gift/{gid}", json={"GiftName": "Updated Mug"})
    assert r.status_code == 200

    r = client.delete(f"/gift/{gid}")
    assert r.status_code == 200

# ======================================================
# ✅ ORDERDETAIL TESTS
# ======================================================
def test_orderdetail_crud(client):
    customer = client.post("/customer", json={
        "Name": "DetailUser",
        "Email": "d@mail.com",
        "Phone": "333",
        "Country": "UA"
    }).json()
    courier = client.post("/courier", json={
        "CourierName": "Glovo",
        "Phone": "777",
        "VehicleNumber": "EE5555FF"
    }).json()
    order = client.post("/order", json={
        "CustomerID": customer["CustomerID"],
        "CourierID": courier["CourierID"],
        "OrderDate": "2025-10-22",
        "TotalAmount": 200
    }).json()
    supplier = client.post("/supplier", json={
        "supplierName": "TestSupp",
        "Address": "Main 2",
        "Phone": "000"
    }).json()
    product = client.post("/product", json={
        "ProductName": "Charger",
        "Price": 15.5,
        "SupplierID": supplier["SupplierID"]
    }).json()

    response = client.post("/orderdetail", json={
        "OrderID": order["OrderID"],
        "ProductID": product["ProductID"],
        "Quantity": 2,
        "UnitPrice": 15.5
    })
    assert response.status_code == 200
    od = response.json()
    odid = od["OrderDetailID"]

    assert client.get(f"/orderdetail/{odid}").status_code == 200
    r = client.put(f"/orderdetail/{odid}", json={"Quantity": 3})
    assert r.status_code == 200
    assert r.json()["Quantity"] == 3

    r = client.delete(f"/orderdetail/{odid}")
    assert r.status_code == 200

# ======================================================
# ✅ ANALYTICS TESTS
# ======================================================
def test_analytics_endpoints(client):
    assert client.get("/analytics/top_customers").status_code in (200, 404)
    assert client.get("/analytics/sales_by_country").status_code in (200, 404)
    assert client.get("/analytics/top_products").status_code in (200, 404)
    assert client.get("/analytics/revenue_by_supplier").status_code in (200, 404)
