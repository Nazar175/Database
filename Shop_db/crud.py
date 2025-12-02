from sqlalchemy.orm import Session
import models

# ---------- CUSTOMER ----------
def create_customer(db: Session, Name: str, Email: str, Phone: str = None, Country: str = None):
    customer = models.Customer(Name=Name, Email=Email, Phone=Phone, Country=Country)
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer

def get_customers(db: Session):
    return db.query(models.Customer).all()

def get_customer(db: Session, customer_id: int):
    return db.query(models.Customer).filter(models.Customer.CustomerID == customer_id).first()

def update_customer(db: Session, customer_id: int, **kwargs):
    customer = get_customer(db, customer_id)
    if not customer:
        return None
    for key, value in kwargs.items():
        setattr(customer, key, value)
    db.commit()
    db.refresh(customer)
    return customer

def delete_customer(db: Session, customer_id: int):
    customer = get_customer(db, customer_id)
    if not customer:
        return None
    db.delete(customer)
    db.commit()
    return customer


# ---------- SUPPLIER ----------
def create_supplier(db: Session, supplier_name: str, address: str = None, phone: str = None, delivery_date=None):
    supplier = models.Supplier(SupplierName=supplier_name, Address=address, Phone=phone, DeliveryDate=delivery_date)
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier

def get_suppliers(db: Session):
    return db.query(models.Supplier).all()

def get_supplier(db: Session, supplier_id: int):
    return db.query(models.Supplier).filter(models.Supplier.SupplierID == supplier_id).first()

def update_supplier(db: Session, supplier_id: int, **kwargs):
    supplier = get_supplier(db, supplier_id)
    if not supplier:
        return None
    for key, value in kwargs.items():
        setattr(supplier, key, value)
    db.commit()
    db.refresh(supplier)
    return supplier

def delete_supplier(db: Session, supplier_id: int):
    supplier = get_supplier(db, supplier_id)
    if not supplier:
        return None
    db.delete(supplier)
    db.commit()
    return supplier


# ---------- PRODUCT ----------
def create_product(db: Session, name: str, Price: float, supplier_id: int = None):
    product = models.Product(ProductName=name, Price=Price, SupplierID=supplier_id)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product

def get_products(db: Session):
    return db.query(models.Product).all()

def get_product(db: Session, product_id: int):
    return db.query(models.Product).filter(models.Product.ProductID == product_id).first()

def update_product(db: Session, product_id: int, **kwargs):
    product = get_product(db, product_id)
    if not product:
        return None
    for key, value in kwargs.items():
        setattr(product, key, value)
    db.commit()
    db.refresh(product)
    return product

def delete_product(db: Session, product_id: int):
    product = get_product(db, product_id)
    if not product:
        return None
    db.delete(product)
    db.commit()
    return product


# ---------- ORDERS ----------
def create_order(db: Session, order_date, customer_id: int, shipping_address: str, Status: str = "Pending"):
    order = models.Orders(OrderDate=order_date, CustomerID=customer_id, ShippingAddress=shipping_address, Status=Status)
    db.add(order)
    db.commit()
    db.refresh(order)
    return order

def get_orders(db: Session):
    return db.query(models.Orders).all()

def get_order(db: Session, order_id: int):
    return db.query(models.Orders).filter(models.Orders.OrderID == order_id).first()

def update_order(db: Session, order_id: int, **kwargs):
    order = get_order(db, order_id)
    if not order:
        return None

    field_map = {
        "ShippingAddress": "ShippingAddress",
        "shipping_address": "ShippingAddress",
        "Status": "Status",
        "status": "Status",
        "OrderDate": "OrderDate",
        "order_date": "OrderDate",
        "CustomerID": "CustomerID",
        "customer_id": "CustomerID"
    }

    for key, value in kwargs.items():
        if key in field_map:
            setattr(order, field_map[key], value)

    db.commit()
    db.refresh(order)
    return order

def delete_order(db: Session, order_id: int):
    order = get_order(db, order_id)
    if not order:
        return None
    db.delete(order)
    db.commit()
    return order


# ---------- ORDER DETAIL ----------
def create_order_detail(db: Session, order_id: int, product_id: int, quantity: int = 1):
    detail = models.OrderDetail(OrderID=order_id, ProductID=product_id, Quantity=quantity)
    db.add(detail)
    db.commit()
    db.refresh(detail)
    return detail

def get_order_details(db: Session):
    return db.query(models.OrderDetail).all()

def get_order_detail(db: Session, detail_id: int):
    return db.query(models.OrderDetail).filter(models.OrderDetail.OrderDetailID == detail_id).first()

def update_order_detail(db: Session, detail_id: int, **kwargs):
    detail = get_order_detail(db, detail_id)
    if not detail:
        return None
    for key, value in kwargs.items():
        setattr(detail, key, value)
    db.commit()
    db.refresh(detail)
    return detail

def delete_order_detail(db: Session, detail_id: int):
    detail = get_order_detail(db, detail_id)
    if not detail:
        return None
    db.delete(detail)
    db.commit()
    return detail


# ---------- COURIER ----------
def create_courier(db: Session, courier_name: str, country: str = None, price: float = None, order_id: int = None):
    db_courier = models.Courier(
        Name=courier_name,
        Country=country,
        Price=price,
        OrderID=order_id
    )
    db.add(db_courier)
    db.commit()
    db.refresh(db_courier)
    return db_courier


def get_couriers(db: Session):
    return db.query(models.Courier).all()

def get_courier(db: Session, courier_id: int):
    return db.query(models.Courier).filter(models.Courier.CourierID == courier_id).first()

def update_courier(db: Session, courier_id: int, **kwargs):
    courier = get_courier(db, courier_id)
    if not courier:
        return None
    for key, value in kwargs.items():
        setattr(courier, key, value)
    db.commit()
    db.refresh(courier)
    return courier

def delete_courier(db: Session, courier_id: int):
    courier = get_courier(db, courier_id)
    if not courier:
        return None
    db.delete(courier)
    db.commit()
    return courier


# ---------- PAYMENT ----------
def create_payment(db: Session, order_id: int, Status: str, amount: float, payment_date):
    payment = models.Payment(OrderID=order_id, Status=Status, Amount=amount, PaymentDate=payment_date)
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment

def get_payments(db: Session):
    return db.query(models.Payment).all()

def get_payment(db: Session, payment_id: int):
    return db.query(models.Payment).filter(models.Payment.PaymentID == payment_id).first()

def update_payment(db: Session, payment_id: int, **kwargs):
    payment = get_payment(db, payment_id)
    if not payment:
        return None
    for key, value in kwargs.items():
        if key == "amount":
            key = "Amount"
        setattr(payment, key, value)
    db.commit()
    db.refresh(payment)
    return payment

def delete_payment(db: Session, payment_id: int):
    payment = get_payment(db, payment_id)
    if not payment:
        return None
    db.delete(payment)
    db.commit()
    return payment


# ---------- GIFTS ----------
def create_gift(db: Session, amount: float, exp_date, type_: str, unit: str, payment_id: int = None):
    gift = models.Gifts(Amount=amount, ExparesDate=exp_date, Type=type_, Unit=unit, PaymentID=payment_id)
    db.add(gift)
    db.commit()
    db.refresh(gift)
    return gift

def get_gifts(db: Session):
    return db.query(models.Gifts).all()

def get_gift(db: Session, gift_id: int):
    return db.query(models.Gifts).filter(models.Gifts.GiftID == gift_id).first()

def update_gift(db: Session, gift_id: int, **kwargs):
    gift = get_gift(db, gift_id)
    if not gift:
        return None
    for key, value in kwargs.items():
        setattr(gift, key, value)
    db.commit()
    db.refresh(gift)
    return gift

def delete_gift(db: Session, gift_id: int):
    gift = get_gift(db, gift_id)
    if not gift:
        return None
    db.delete(gift)
    db.commit()
    return gift
