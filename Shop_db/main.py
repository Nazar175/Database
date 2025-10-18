# Для запуску програми: cd Shop_db
# Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
# venv/Scripts/activate
# uvicorn main:app --reload

from fastapi import FastAPI, Depends, HTTPException, Path
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from decimal import Decimal

import models
import crud
from database import get_db
from sqlalchemy.orm import Session

app = FastAPI(title="ShopDB API")

# ----------------------
# Pydantic Schemas
# ----------------------
class OrderCreate(BaseModel):
    order_date: datetime = Field(..., example="2025-10-18T10:00:00")
    shipping_address: str = Field(..., example="Khreshchatyk 1, Kyiv")
    status: Optional[str] = Field(None, example="Pending")  # will be converted to Enum by DB

class OrderUpdate(BaseModel):
    shipping_address: Optional[str] = None
    status: Optional[str] = None

class OrderOut(BaseModel):
    OrderID: int
    OrderDate: datetime
    CustomerID: int
    ShippingAddress: str
    Status: str

    class Config:
        orm_mode = True

class PaymentCreate(BaseModel):
    status: str = Field(..., example="Paid")
    amount: Decimal = Field(..., example="123.45")
    payment_date: datetime = Field(..., example="2025-10-18T12:00:00")

class PaymentUpdate(BaseModel):
    status: Optional[str] = None
    amount: Optional[Decimal] = None
    payment_date: Optional[datetime] = None

class PaymentOut(BaseModel):
    PaymentID: int
    OrderID: int
    Status: str
    Amount: Decimal
    PaymentDate: Optional[datetime]

    class Config:
        orm_mode = True

class GiftCreate(BaseModel):
    amount: Decimal = Field(..., example="10.00")
    expares_date: datetime = Field(..., example="2026-01-01T00:00:00")
    type_: str = Field(..., alias="type", example="Certificate")  # alias to accept "type"
    unit: str = Field(..., example="USD")

class GiftUpdate(BaseModel):
    amount: Optional[Decimal] = None
    expares_date: Optional[datetime] = None
    type_: Optional[str] = Field(None, alias="type")
    unit: Optional[str] = None

class GiftOut(BaseModel):
    GiftID: int
    Amount: Decimal
    ExparesDate: Optional[datetime]
    Type: Optional[str]
    Unit: str
    PaymentID: Optional[int]

    class Config:
        orm_mode = True

class CourierCreate(BaseModel):
    name: str
    country: Optional[str] = None
    price: Decimal
class CourierUpdate(BaseModel):
    name: Optional[str] = None
    country: Optional[str] = None
    price: Optional[Decimal] = None

class CourierOut(BaseModel):
    CourierID: int
    Name: str
    Country: Optional[str]
    Price: Optional[Decimal]
    OrderID: int

    class Config:
        orm_mode = True

class OrderDetailCreate(BaseModel):
    product_id: int
    quantity: int = 1

class OrderDetailUpdate(BaseModel):
    product_id: Optional[int] = None
    quantity: Optional[int] = None

class OrderDetailOut(BaseModel):
    OrderDetailID: int
    OrderID: int
    ProductID: int
    Quantity: int

    class Config:
        orm_mode = True

class ProductCreateUpdate(BaseModel):
    name: str
    price: Decimal

class ProductOut(BaseModel):
    ProductID: int
    ProductName: str
    Price: Decimal
    SupplierID: Optional[int]

    class Config:
        orm_mode = True

class SupplierCreateUpdate(BaseModel):
    supplier_name: str
    address: Optional[str] = None
    phone: Optional[str] = None

class SupplierOut(BaseModel):
    SupplierID: int
    SupplierName: str
    Address: Optional[str]
    Phone: Optional[str]
    DeliveryDate: Optional[datetime]

    class Config:
        orm_mode = True

# ----------------------
# Helper functions
# ----------------------
def get_order_or_404(db: Session, order_id: int):
    order = crud.get_order(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    return order

def get_customer_or_404(db: Session, customer_id: int):
    cust = crud.get_customer(db, customer_id)
    if not cust:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
    return cust

# ----------------------
# Routes
# ----------------------
# 1) /customer/{customer_id}/orders
@app.get("/customer/{customer_id}/orders", response_model=List[OrderOut])
def list_customer_orders(customer_id: int = Path(..., gt=0), db: Session = Depends(get_db)):
    get_customer_or_404(db, customer_id)
    orders = db.query(models.Orders).filter(models.Orders.CustomerID == customer_id).all()
    return orders

@app.post("/customer/{customer_id}/orders", response_model=OrderOut, status_code=201)
def create_customer_order(customer_id: int, payload: OrderCreate, db: Session = Depends(get_db)):
    get_customer_or_404(db, customer_id)
    order = crud.create_order(db, order_date=payload.order_date, customer_id=customer_id,
                              shipping_address=payload.shipping_address, status=payload.status or "Pending")
    return order

@app.put("/customer/{customer_id}/orders/{order_id}", response_model=OrderOut)
def update_customer_order(customer_id: int, order_id: int, payload: OrderUpdate, db: Session = Depends(get_db)):
    get_customer_or_404(db, customer_id)
    order = crud.get_order(db, order_id)
    if not order or order.CustomerID != customer_id:
        raise HTTPException(404, "Order not found for this customer")
    updated = crud.update_order(db, order_id, OrderDate=order.OrderDate, ShippingAddress=payload.shipping_address or order.ShippingAddress, Status=payload.status or order.Status)
    return updated

@app.delete("/customer/{customer_id}/orders/{order_id}", response_model=OrderOut)
def delete_customer_order(customer_id: int, order_id: int, db: Session = Depends(get_db)):
    get_customer_or_404(db, customer_id)
    order = crud.get_order(db, order_id)
    if not order or order.CustomerID != customer_id:
        raise HTTPException(404, "Order not found for this customer")
    deleted = crud.delete_order(db, order_id)
    return deleted

# 2) /customer/{customer_id}/orders/{order_id}/payment
@app.get("/customer/{customer_id}/orders/{order_id}/payment", response_model=Optional[PaymentOut])
def get_order_payment(customer_id: int, order_id: int, db: Session = Depends(get_db)):
    get_customer_or_404(db, customer_id)
    order = get_order_or_404(db, order_id)
    if order.CustomerID != customer_id:
        raise HTTPException(404, "Order not found for this customer")
    if not order.payment:
        return JSONResponse(status_code=200, content=None)
    return order.payment

@app.post("/customer/{customer_id}/orders/{order_id}/payment", response_model=PaymentOut, status_code=201)
def create_order_payment(customer_id: int, order_id: int, payload: PaymentCreate, db: Session = Depends(get_db)):
    get_customer_or_404(db, customer_id)
    order = get_order_or_404(db, order_id)
    if order.CustomerID != customer_id:
        raise HTTPException(404, "Order not found for this customer")
    payment = crud.create_payment(db, order_id=order_id, status=payload.status, amount=payload.amount, payment_date=payload.payment_date)
    return payment

@app.put("/customer/{customer_id}/orders/{order_id}/payment/{payment_id}", response_model=PaymentOut)
def update_order_payment(customer_id: int, order_id: int, payment_id: int, payload: PaymentUpdate, db: Session = Depends(get_db)):
    get_customer_or_404(db, customer_id)
    order = get_order_or_404(db, order_id)
    payment = crud.get_payment(db, payment_id)
    if not payment or payment.OrderID != order_id:
        raise HTTPException(404, "Payment not found for this order")
    updated = crud.update_payment(db, payment_id,
                                  Status=payload.status or payment.Status,
                                  Amount=payload.amount or payment.Amount,
                                  PaymentDate=payload.payment_date or payment.PaymentDate)
    return updated

@app.delete("/customer/{customer_id}/orders/{order_id}/payment/{payment_id}", response_model=PaymentOut)
def delete_order_payment(customer_id: int, order_id: int, payment_id: int, db: Session = Depends(get_db)):
    get_customer_or_404(db, customer_id)
    order = get_order_or_404(db, order_id)
    payment = crud.get_payment(db, payment_id)
    if not payment or payment.OrderID != order_id:
        raise HTTPException(404, "Payment not found for this order")
    deleted = crud.delete_payment(db, payment_id)
    return deleted

# 3) /customer/{customer_id}/orders/{order_id}/payment/{payment_id}/gifts
@app.get("/customer/{customer_id}/orders/{order_id}/payment/{payment_id}/gifts", response_model=List[GiftOut])
def list_payment_gifts(customer_id: int, order_id: int, payment_id: int, db: Session = Depends(get_db)):
    get_customer_or_404(db, customer_id)
    order = get_order_or_404(db, order_id)
    payment = crud.get_payment(db, payment_id)
    if not payment or payment.OrderID != order_id:
        raise HTTPException(404, "Payment not found for this order")
    gifts = db.query(models.Gifts).filter(models.Gifts.PaymentID == payment_id).all()
    return gifts

@app.post("/customer/{customer_id}/orders/{order_id}/payment/{payment_id}/gifts", response_model=GiftOut, status_code=201)
def create_payment_gift(customer_id: int, order_id: int, payment_id: int, payload: GiftCreate, db: Session = Depends(get_db)):
    get_customer_or_404(db, customer_id)
    get_order_or_404(db, order_id)
    payment = crud.get_payment(db, payment_id)
    if not payment or payment.OrderID != order_id:
        raise HTTPException(404, "Payment not found for this order")
    gift = crud.create_gift(db, amount=payload.amount, exp_date=payload.expares_date, type_=payload.type_, unit=payload.unit, payment_id=payment_id)
    return gift

@app.put("/customer/{customer_id}/orders/{order_id}/payment/{payment_id}/gifts/{gift_id}", response_model=GiftOut)
def update_payment_gift(customer_id: int, order_id: int, payment_id: int, gift_id: int, payload: GiftUpdate, db: Session = Depends(get_db)):
    get_customer_or_404(db, customer_id)
    get_order_or_404(db, order_id)
    payment = crud.get_payment(db, payment_id)
    gift = crud.get_gift(db, gift_id)
    if not payment or payment.OrderID != order_id or not gift or gift.PaymentID != payment_id:
        raise HTTPException(404, "Gift or Payment not found")
    updated = crud.update_gift(db, gift_id,
                               Amount=payload.amount or gift.Amount,
                               ExparesDate=payload.expares_date or gift.ExparesDate,
                               Type=payload.type_ or gift.Type,
                               Unit=payload.unit or gift.Unit)
    return updated

@app.delete("/customer/{customer_id}/orders/{order_id}/payment/{payment_id}/gifts/{gift_id}", response_model=GiftOut)
def delete_payment_gift(customer_id: int, order_id: int, payment_id: int, gift_id: int, db: Session = Depends(get_db)):
    get_customer_or_404(db, customer_id)
    get_order_or_404(db, order_id)
    payment = crud.get_payment(db, payment_id)
    gift = crud.get_gift(db, gift_id)
    if not payment or payment.OrderID != order_id or not gift or gift.PaymentID != payment_id:
        raise HTTPException(404, "Gift or Payment not found")
    deleted = crud.delete_gift(db, gift_id)
    return deleted

# 4) /customer/{customer_id}/orders/{order_id}/courier
@app.get("/customer/{customer_id}/orders/{order_id}/courier", response_model=Optional[CourierOut])
def get_order_courier(customer_id: int, order_id: int, db: Session = Depends(get_db)):
    get_customer_or_404(db, customer_id)
    order = get_order_or_404(db, order_id)
    if order.CustomerID != customer_id:
        raise HTTPException(404, "Order not found for this customer")
    if not order.courier:
        return JSONResponse(status_code=200, content=None)
    return order.courier

@app.post("/customer/{customer_id}/orders/{order_id}/courier", response_model=CourierOut, status_code=201)
def create_order_courier(customer_id: int, order_id: int, payload: CourierCreate, db: Session = Depends(get_db)):
    get_customer_or_404(db, customer_id)
    order = get_order_or_404(db, order_id)
    if order.CustomerID != customer_id:
        raise HTTPException(404, "Order not found for this customer")
    courier = crud.create_courier(db, name=payload.name, country=payload.country, price=payload.price, order_id=order_id)
    return courier

@app.put("/customer/{customer_id}/orders/{order_id}/courier/{courier_id}", response_model=CourierOut)
def update_order_courier(customer_id: int, order_id: int, courier_id: int, payload: CourierUpdate, db: Session = Depends(get_db)):
    get_customer_or_404(db, customer_id)
    get_order_or_404(db, order_id)
    courier = crud.get_courier(db, courier_id)
    if not courier or courier.OrderID != order_id:
        raise HTTPException(404, "Courier not found for this order")
    updated = crud.update_courier(db, courier_id,
                                  Name=payload.name or courier.Name,
                                  Country=payload.country or courier.Country,
                                  Price=payload.price or courier.Price)
    return updated

@app.delete("/customer/{customer_id}/orders/{order_id}/courier/{courier_id}", response_model=CourierOut)
def delete_order_courier(customer_id: int, order_id: int, courier_id: int, db: Session = Depends(get_db)):
    get_customer_or_404(db, customer_id)
    get_order_or_404(db, order_id)
    courier = crud.get_courier(db, courier_id)
    if not courier or courier.OrderID != order_id:
        raise HTTPException(404, "Courier not found for this order")
    deleted = crud.delete_courier(db, courier_id)
    return deleted

# 5) /customer/{customer_id}/orders/{order_id}/orderdetail
@app.get("/customer/{customer_id}/orders/{order_id}/orderdetail", response_model=List[OrderDetailOut])
def list_order_details(customer_id: int, order_id: int, db: Session = Depends(get_db)):
    get_customer_or_404(db, customer_id)
    order = get_order_or_404(db, order_id)
    if order.CustomerID != customer_id:
        raise HTTPException(404, "Order not found for this customer")
    details = db.query(models.OrderDetail).filter(models.OrderDetail.OrderID == order_id).all()
    return details

@app.post("/customer/{customer_id}/orders/{order_id}/orderdetail", response_model=OrderDetailOut, status_code=201)
def create_order_detail_endpoint(customer_id: int, order_id: int, payload: OrderDetailCreate, db: Session = Depends(get_db)):
    get_customer_or_404(db, customer_id)
    order = get_order_or_404(db, order_id)
    if order.CustomerID != customer_id:
        raise HTTPException(404, "Order not found for this customer")
    product = crud.get_product(db, payload.product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    detail = crud.create_order_detail(db, order_id=order_id, product_id=payload.product_id, quantity=payload.quantity)
    return detail

@app.put("/customer/{customer_id}/orders/{order_id}/orderdetail/{detail_id}", response_model=OrderDetailOut)
def update_order_detail_endpoint(customer_id: int, order_id: int, detail_id: int, payload: OrderDetailUpdate, db: Session = Depends(get_db)):
    get_customer_or_404(db, customer_id)
    get_order_or_404(db, order_id)
    detail = crud.get_order_detail(db, detail_id)
    if not detail or detail.OrderID != order_id:
        raise HTTPException(404, "Order detail not found for this order")
    updated = crud.update_order_detail(db, detail_id,
                                       OrderID=detail.OrderID,
                                       ProductID=payload.product_id or detail.ProductID,
                                       Quantity=payload.quantity or detail.Quantity)
    return updated

@app.delete("/customer/{customer_id}/orders/{order_id}/orderdetail/{detail_id}", response_model=OrderDetailOut)
def delete_order_detail_endpoint(customer_id: int, order_id: int, detail_id: int, db: Session = Depends(get_db)):
    get_customer_or_404(db, customer_id)
    get_order_or_404(db, order_id)
    detail = crud.get_order_detail(db, detail_id)
    if not detail or detail.OrderID != order_id:
        raise HTTPException(404, "Order detail not found for this order")
    deleted = crud.delete_order_detail(db, detail_id)
    return deleted

# 6) /customer/{customer_id}/orders/{order_id}/orderdetail/{detail_id}/product
@app.get("/customer/{customer_id}/orders/{order_id}/orderdetail/{detail_id}/product", response_model=ProductOut)
def get_product_for_order_detail(customer_id: int, order_id: int, detail_id: int, db: Session = Depends(get_db)):
    get_customer_or_404(db, customer_id)
    get_order_or_404(db, order_id)
    detail = crud.get_order_detail(db, detail_id)
    if not detail or detail.OrderID != order_id:
        raise HTTPException(404, "Order detail not found for this order")
    product = crud.get_product(db, detail.ProductID)
    if not product:
        raise HTTPException(404, "Product not found")
    return product

@app.post("/customer/{customer_id}/orders/{order_id}/orderdetail/{detail_id}/product", response_model=ProductOut, status_code=201)
def create_product_for_order_detail(customer_id: int, order_id: int, detail_id: int, payload: ProductCreateUpdate, db: Session = Depends(get_db)):
    get_customer_or_404(db, customer_id)
    get_order_or_404(db, order_id)
    detail = crud.get_order_detail(db, detail_id)
    if not detail or detail.OrderID != order_id:
        raise HTTPException(404, "Order detail not found for this order")
    product = crud.create_product(db, name=payload.name, price=payload.price)
    detail.ProductID = product.ProductID
    db.commit()
    db.refresh(detail)
    return product

@app.put("/customer/{customer_id}/orders/{order_id}/orderdetail/{detail_id}/product/{product_id}", response_model=ProductOut)
def update_product_for_order_detail(customer_id: int, order_id: int, detail_id: int, product_id: int, payload: ProductCreateUpdate, db: Session = Depends(get_db)):
    get_customer_or_404(db, customer_id)
    get_order_or_404(db, order_id)
    detail = crud.get_order_detail(db, detail_id)
    if not detail or detail.OrderID != order_id or detail.ProductID != product_id:
        raise HTTPException(404, "Order detail or product mismatch")
    product = crud.update_product(db, product_id, name=payload.name, price=payload.price)
    return product

@app.delete("/customer/{customer_id}/orders/{order_id}/orderdetail/{detail_id}/product/{product_id}", response_model=ProductOut)
def delete_product_for_order_detail(customer_id: int, order_id: int, detail_id: int, product_id: int, db: Session = Depends(get_db)):
    get_customer_or_404(db, customer_id)
    get_order_or_404(db, order_id)
    detail = crud.get_order_detail(db, detail_id)
    if not detail or detail.OrderID != order_id or detail.ProductID != product_id:
        raise HTTPException(404, "Order detail or product mismatch")
    deleted = crud.delete_product(db, product_id)
    detail.ProductID = None
    db.commit()
    return deleted

# 7) /customer/{customer_id}/orders/{order_id}/orderdetail/{detail_id}/product/{product_id}/supplier
@app.get("/customer/{customer_id}/orders/{order_id}/orderdetail/{detail_id}/product/{product_id}/supplier", response_model=SupplierOut)
def get_supplier_for_product(customer_id: int, order_id: int, detail_id: int, product_id: int, db: Session = Depends(get_db)):
    get_customer_or_404(db, customer_id)
    get_order_or_404(db, order_id)
    detail = crud.get_order_detail(db, detail_id)
    if not detail or detail.OrderID != order_id or detail.ProductID != product_id:
        raise HTTPException(404, "Mismatch between order detail and product")
    product = crud.get_product(db, product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    supplier = crud.get_supplier(db, product.SupplierID) if product.SupplierID else None
    if not supplier:
        raise HTTPException(404, "Supplier not found")
    return supplier

@app.post("/customer/{customer_id}/orders/{order_id}/orderdetail/{detail_id}/product/{product_id}/supplier", response_model=SupplierOut, status_code=201)
def create_supplier_for_product(customer_id: int, order_id: int, detail_id: int, product_id: int, payload: SupplierCreateUpdate, db: Session = Depends(get_db)):
    get_customer_or_404(db, customer_id)
    get_order_or_404(db, order_id)
    product = crud.get_product(db, product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    supplier = crud.create_supplier(db, supplier_name=payload.supplier_name, address=payload.address, phone=payload.phone)
    product.SupplierID = supplier.SupplierID
    db.commit()
    db.refresh(product)
    return supplier

@app.put("/customer/{customer_id}/orders/{order_id}/orderdetail/{detail_id}/product/{product_id}/supplier/{supplier_id}", response_model=SupplierOut)
def update_supplier_for_product(customer_id: int, order_id: int, detail_id: int, product_id: int, supplier_id: int, payload: SupplierCreateUpdate, db: Session = Depends(get_db)):
    get_customer_or_404(db, customer_id)
    get_order_or_404(db, order_id)
    product = crud.get_product(db, product_id)
    if not product or product.SupplierID != supplier_id:
        raise HTTPException(404, "Supplier mismatch")
    supplier = crud.update_supplier(db, supplier_id,
                                    supplier_name=payload.supplier_name,
                                    address=payload.address,
                                    phone=payload.phone)
    return supplier

@app.delete("/customer/{customer_id}/orders/{order_id}/orderdetail/{detail_id}/product/{product_id}/supplier/{supplier_id}", response_model=SupplierOut)
def delete_supplier_for_product(customer_id: int, order_id: int, detail_id: int, product_id: int, supplier_id: int, db: Session = Depends(get_db)):
    get_customer_or_404(db, customer_id)
    get_order_or_404(db, order_id)
    product = crud.get_product(db, product_id)
    if not product or product.SupplierID != supplier_id:
        raise HTTPException(404, "Supplier mismatch")
    deleted = crud.delete_supplier(db, supplier_id)
    product.SupplierID = None
    db.commit()
    return deleted

# Root
@app.get("/")
def root():
    return {"status": "ok", "message": "ShopDB API running. See /docs for OpenAPI UI."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
