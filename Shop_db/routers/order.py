from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import crud, models
from pydantic import BaseModel, constr, Field
from typing import List
from datetime import datetime

router = APIRouter()

# ---------- SCHEMAS ----------
class Order(BaseModel):
    OrderID: int | None = None
    orderDate: datetime | None = Field(None, alias="OrderDate")
    shippingAddress: constr(min_length=5, max_length=200) | None = Field(None, alias="ShippingAddress")
    Status: str | None = Field("Pending", alias="Status")
    CustomerID: int | None = Field(None, alias="CustomerID")

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "validate_by_name": True,
    }
    
# ---------- ROUTES ----------
@router.get("/order", response_model=List[Order])
def read_orders(db: Session = Depends(get_db)):
    return crud.get_orders(db)


@router.get("/order/{order_id}", response_model=Order)
def read_order(order_id: int, db: Session = Depends(get_db)):
    order = crud.get_order(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.post("/order", response_model=Order)
def create_order(order: Order, db: Session = Depends(get_db)):
    customer = crud.get_customer(db, order.CustomerID)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return crud.create_order(
        db,
        order_date=order.orderDate,
        customer_id=order.CustomerID,
        shipping_address=order.shippingAddress,
        Status=order.Status,
    )


@router.put("/order/{order_id}", response_model=Order)
def update_order(order_id: int, order: Order, db: Session = Depends(get_db)):
    db_order = crud.get_order(db, order_id)
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    return crud.update_order(db, order_id, **order.dict(exclude_unset=True))


@router.delete("/order/{order_id}")
def delete_order(order_id: int, db: Session = Depends(get_db)):
    order = crud.delete_order(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return {"message": "Order deleted successfully"}


# ---------- HIERARCHICAL ----------
@router.get("/customer/{customer_id}/orders")
def get_orders_by_customer(customer_id: int, db: Session = Depends(get_db)):
    customer = crud.get_customer(db, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return [o for o in crud.get_orders(db) if o.CustomerID == customer_id]

@router.post("/customer/{customer_id}/orders", response_model=Order)
def create_order_for_customer(customer_id: int, order: Order, db: Session = Depends(get_db)):
    customer = crud.get_customer(db, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return crud.create_order(
        db,
        order_date=order.orderDate,
        customer_id=customer_id,
        shipping_address=order.shippingAddress,
        Status=order.Status,
    )

@router.put("/customer/{customer_id}/orders/{order_id}", response_model=Order)
def update_order_for_customer(customer_id: int, order_id: int, order: Order, db: Session = Depends(get_db)):
    customer = crud.get_customer(db, customer_id)
    db_order = crud.get_order(db, order_id)
    if not customer or not db_order or db_order.CustomerID != customer_id:
        raise HTTPException(status_code=404, detail="Order not found for this customer")
    return crud.update_order(db, order_id, **order.dict(exclude_unset=True))

@router.delete("/customer/{customer_id}/orders/{order_id}")
def delete_order_for_customer(customer_id: int, order_id: int, db: Session = Depends(get_db)):
    customer = crud.get_customer(db, customer_id)
    db_order = crud.get_order(db, order_id)
    if not customer or not db_order or db_order.CustomerID != customer_id:
        raise HTTPException(status_code=404, detail="Order not found for this customer")
    crud.delete_order(db, order_id)
    return {"message": "Order deleted successfully"}