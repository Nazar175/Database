# Для запуску програми: cd Shop_db
# Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
# venv/Scripts/activate
# uvicorn main:app --reload
from fastapi import FastAPI, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from database import SessionLocal
from models import *
import crud

app = FastAPI(title="ShopDB REST API")

# ---------- DB SESSION ----------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------- CUSTOMER ----------
@app.get("/customers")
def get_customers(db: Session = Depends(get_db)):
    return crud.get_customers(db)

@app.get("/customers/{customer_id}")
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    customer = crud.get_customer(db, customer_id)
    if not customer:
        raise HTTPException(404, "Customer not found")
    return customer

@app.post("/customers")
async def create_customer(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    return crud.create_customer(db, **data)

@app.put("/customers/{customer_id}")
async def update_customer(customer_id: int, request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    updated = crud.update_customer(db, customer_id, **data)
    if not updated:
        raise HTTPException(404, "Customer not found")
    return updated

@app.delete("/customers/{customer_id}")
def delete_customer(customer_id: int, db: Session = Depends(get_db)):
    deleted = crud.delete_customer(db, customer_id)
    if not deleted:
        raise HTTPException(404, "Customer not found")
    return {"message": "Customer deleted"}


# ---------- SUPPLIER ----------
@app.get("/suppliers")
def get_suppliers(db: Session = Depends(get_db)):
    return crud.get_suppliers(db)

@app.get("/suppliers/{supplier_id}")
def get_supplier(supplier_id: int, db: Session = Depends(get_db)):
    supplier = crud.get_supplier(db, supplier_id)
    if not supplier:
        raise HTTPException(404, "Supplier not found")
    return supplier

@app.post("/suppliers")
async def create_supplier(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    return crud.create_supplier(db, **data)

@app.put("/suppliers/{supplier_id}")
async def update_supplier(supplier_id: int, request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    updated = crud.update_supplier(db, supplier_id, **data)
    if not updated:
        raise HTTPException(404, "Supplier not found")
    return updated

@app.delete("/suppliers/{supplier_id}")
def delete_supplier(supplier_id: int, db: Session = Depends(get_db)):
    deleted = crud.delete_supplier(db, supplier_id)
    if not deleted:
        raise HTTPException(404, "Supplier not found")
    return {"message": "Supplier deleted"}


# ---------- PRODUCT ----------
@app.get("/products")
def get_products(db: Session = Depends(get_db)):
    return crud.get_products(db)

@app.get("/products/{product_id}")
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = crud.get_product(db, product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    return product

@app.post("/products")
async def create_product(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    return crud.create_product(db, **data)

@app.put("/products/{product_id}")
async def update_product(product_id: int, request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    updated = crud.update_product(db, product_id, **data)
    if not updated:
        raise HTTPException(404, "Product not found")
    return updated

@app.delete("/products/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    deleted = crud.delete_product(db, product_id)
    if not deleted:
        raise HTTPException(404, "Product not found")
    return {"message": "Product deleted"}


# ---------- ORDERS ----------
@app.get("/orders")
def get_orders(db: Session = Depends(get_db)):
    return crud.get_orders(db)

@app.get("/orders/{order_id}")
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = crud.get_order(db, order_id)
    if not order:
        raise HTTPException(404, "Order not found")
    return order

@app.post("/orders")
async def create_order(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    return crud.create_order(db, **data)

@app.put("/orders/{order_id}")
async def update_order(order_id: int, request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    updated = crud.update_order(db, order_id, **data)
    if not updated:
        raise HTTPException(404, "Order not found")
    return updated

@app.delete("/orders/{order_id}")
def delete_order(order_id: int, db: Session = Depends(get_db)):
    deleted = crud.delete_order(db, order_id)
    if not deleted:
        raise HTTPException(404, "Order not found")
    return {"message": "Order deleted"}


# ---------- ORDER DETAILS ----------
@app.get("/orderdetails")
def get_order_details(db: Session = Depends(get_db)):
    return crud.get_order_details(db)

@app.get("/orderdetails/{detail_id}")
def get_order_detail(detail_id: int, db: Session = Depends(get_db)):
    detail = crud.get_order_detail(db, detail_id)
    if not detail:
        raise HTTPException(404, "Order detail not found")
    return detail

@app.post("/orderdetails")
async def create_order_detail(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    return crud.create_order_detail(db, **data)

@app.put("/orderdetails/{detail_id}")
async def update_order_detail(detail_id: int, request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    updated = crud.update_order_detail(db, detail_id, **data)
    if not updated:
        raise HTTPException(404, "Order detail not found")
    return updated

@app.delete("/orderdetails/{detail_id}")
def delete_order_detail(detail_id: int, db: Session = Depends(get_db)):
    deleted = crud.delete_order_detail(db, detail_id)
    if not deleted:
        raise HTTPException(404, "Order detail not found")
    return {"message": "Order detail deleted"}


# ---------- COURIER ----------
@app.get("/couriers")
def get_couriers(db: Session = Depends(get_db)):
    return crud.get_couriers(db)

@app.get("/couriers/{courier_id}")
def get_courier(courier_id: int, db: Session = Depends(get_db)):
    courier = crud.get_courier(db, courier_id)
    if not courier:
        raise HTTPException(404, "Courier not found")
    return courier

@app.post("/couriers")
async def create_courier(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    return crud.create_courier(db, **data)

@app.put("/couriers/{courier_id}")
async def update_courier(courier_id: int, request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    updated = crud.update_courier(db, courier_id, **data)
    if not updated:
        raise HTTPException(404, "Courier not found")
    return updated

@app.delete("/couriers/{courier_id}")
def delete_courier(courier_id: int, db: Session = Depends(get_db)):
    deleted = crud.delete_courier(db, courier_id)
    if not deleted:
        raise HTTPException(404, "Courier not found")
    return {"message": "Courier deleted"}


# ---------- PAYMENT ----------
@app.get("/payments")
def get_payments(db: Session = Depends(get_db)):
    return crud.get_payments(db)

@app.get("/payments/{payment_id}")
def get_payment(payment_id: int, db: Session = Depends(get_db)):
    payment = crud.get_payment(db, payment_id)
    if not payment:
        raise HTTPException(404, "Payment not found")
    return payment

@app.post("/payments")
async def create_payment(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    return crud.create_payment(db, **data)

@app.put("/payments/{payment_id}")
async def update_payment(payment_id: int, request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    updated = crud.update_payment(db, payment_id, **data)
    if not updated:
        raise HTTPException(404, "Payment not found")
    return updated

@app.delete("/payments/{payment_id}")
def delete_payment(payment_id: int, db: Session = Depends(get_db)):
    deleted = crud.delete_payment(db, payment_id)
    if not deleted:
        raise HTTPException(404, "Payment not found")
    return {"message": "Payment deleted"}


# ---------- GIFTS ----------
@app.get("/gifts")
def get_gifts(db: Session = Depends(get_db)):
    return crud.get_gifts(db)

@app.get("/gifts/{gift_id}")
def get_gift(gift_id: int, db: Session = Depends(get_db)):
    gift = crud.get_gift(db, gift_id)
    if not gift:
        raise HTTPException(404, "Gift not found")
    return gift

@app.post("/gifts")
async def create_gift(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    return crud.create_gift(db, **data)

@app.put("/gifts/{gift_id}")
async def update_gift(gift_id: int, request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    updated = crud.update_gift(db, gift_id, **data)
    if not updated:
        raise HTTPException(404, "Gift not found")
    return updated

@app.delete("/gifts/{gift_id}")
def delete_gift(gift_id: int, db: Session = Depends(get_db)):
    deleted = crud.delete_gift(db, gift_id)
    if not deleted:
        raise HTTPException(404, "Gift not found")
    return {"message": "Gift deleted"}