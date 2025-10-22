from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import crud, models
from pydantic import BaseModel
from typing import List

router = APIRouter()

# ---------- SCHEMAS ----------
class OrderDetail(BaseModel):
    OrderDetailID: int | None = None
    OrderID: int | None = None
    ProductID: int | None = None
    quantity: int | None = None

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "validate_by_name": True,
    }

# ---------- ROUTES ----------

@router.get("/orderdetail", response_model=List[OrderDetail])
def read_details(db: Session = Depends(get_db)):
    return crud.get_order_details(db)


@router.get("/orderdetail/{orderdetail_id}", response_model=OrderDetail)
def read_detail(orderdetail_id: int, db: Session = Depends(get_db)):
    detail = crud.get_order_detail(db, orderdetail_id)
    if not detail:
        raise HTTPException(status_code=404, detail="OrderDetail not found")
    return detail


@router.post("/orderdetail", response_model=OrderDetail)
def create_detail(detail: OrderDetail, db: Session = Depends(get_db)):
    order = crud.get_order(db, detail.OrderID)
    product = crud.get_product(db, detail.ProductID)
    if not order or not product:
        raise HTTPException(status_code=404, detail="Order or Product not found")
    return crud.create_order_detail(db, detail.OrderID, detail.ProductID, detail.Quantity)


@router.put("/orderdetail/{orderdetail_id}", response_model=OrderDetail)
def update_detail(orderdetail_id: int, detail: OrderDetail, db: Session = Depends(get_db)):
    db_detail = crud.get_order_detail(db, orderdetail_id)
    if not db_detail:
        raise HTTPException(status_code=404, detail="OrderDetail not found")
    return crud.update_order_detail(db, orderdetail_id, **detail.dict(exclude_unset=True))


@router.delete("/orderdetail/{orderdetail_id}")
def delete_detail(orderdetail_id: int, db: Session = Depends(get_db)):
    if not crud.delete_order_detail(db, orderdetail_id):
        raise HTTPException(status_code=404, detail="OrderDetail not found")
    return {"message": "OrderDetail deleted successfully"}


# ---------- HIERARCHICAL ----------
@router.get("/customer/{customer_id}/orders/{order_id}/orderdetail")
def get_details_by_order(customer_id: int, order_id: int, db: Session = Depends(get_db)):
    customer = crud.get_customer(db, customer_id)
    order = crud.get_order(db, order_id)
    if not customer or not order or order.CustomerID != customer.CustomerID:
        raise HTTPException(status_code=404, detail="Order not found for this customer")
    return [d for d in crud.get_order_details(db) if d.OrderID == order_id]

@router.post("/customer/{customer_id}/orders/{order_id}/orderdetail", response_model=OrderDetail)
def create_detail_for_order(customer_id: int, order_id: int, detail: OrderDetail, db: Session = Depends(get_db)):
    customer = crud.get_customer(db, customer_id)
    order = crud.get_order(db, order_id)
    product = crud.get_product(db, detail.ProductID)
    if not customer or not order or not product or order.CustomerID != customer.CustomerID:
        raise HTTPException(status_code=404, detail="Order or Product not found for this customer")
    return crud.create_order_detail(db, order_id, detail.ProductID, detail.Quantity)

@router.put("/customer/{customer_id}/orders/{order_id}/orderdetail/{detail_id}", response_model=OrderDetail)
def update_detail_for_order(customer_id: int, order_id: int, detail_id: int, detail: OrderDetail, db: Session = Depends(get_db)):
    customer = crud.get_customer(db, customer_id)
    order = crud.get_order(db, order_id)
    db_detail = crud.get_order_detail(db, detail_id)
    if not customer or not order or not db_detail or order.CustomerID != customer.CustomerID or db_detail.OrderID != order.OrderID:
        raise HTTPException(status_code=404, detail="OrderDetail not found for this customer and order")
    return crud.update_order_detail(db, detail_id, **detail.dict(exclude_unset=True))

@router.delete("/customer/{customer_id}/orders/{order_id}/orderdetail/{detail_id}")
def delete_detail_for_order(customer_id: int, order_id: int, detail_id: int, db: Session = Depends(get_db)):
    customer = crud.get_customer(db, customer_id)
    order = crud.get_order(db, order_id)
    db_detail = crud.get_order_detail(db, detail_id)
    if not customer or not order or not db_detail or order.CustomerID != customer.CustomerID or db_detail.OrderID != order.OrderID:
        raise HTTPException(status_code=404, detail="OrderDetail not found for this customer and order")
    if not crud.delete_order_detail(db, detail_id):
        raise HTTPException(status_code=404, detail="OrderDetail not found")
    return {"message": "OrderDetail deleted successfully"}