from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

import crud
import models
from database import get_db
from .customer import ensure_customer_scope, get_current_user

router = APIRouter()


# ---------- SCHEMAS ----------
class OrderDetail(BaseModel):
    OrderDetailID: int | None = None
    OrderID: int | None = None
    ProductID: int | None = None
    quantity: int | None = Field(None, alias="Quantity")

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "validate_by_name": True,
    }

# ---------- ROUTES ----------
@router.get("/orderdetail", response_model=List[OrderDetail])
def read_details(
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    return crud.get_order_details(db, customer_id=current_user.CustomerID)


@router.get("/orderdetail/{orderdetail_id}", response_model=OrderDetail)
def read_detail(
    orderdetail_id: int,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    detail = crud.get_order_detail(db, orderdetail_id, customer_id=current_user.CustomerID)
    if not detail:
        raise HTTPException(status_code=404, detail="OrderDetail not found")
    return detail


@router.post("/orderdetail", response_model=OrderDetail)
def create_detail(
    detail: OrderDetail,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    order = crud.get_order(db, detail.OrderID, customer_id=current_user.CustomerID)
    product = crud.get_product(db, detail.ProductID, owner_customer_id=current_user.CustomerID)
    if not order or not product:
        raise HTTPException(status_code=404, detail="Order or Product not found")

    return crud.create_order_detail(db, detail.OrderID, detail.ProductID, detail.quantity)


@router.put("/orderdetail/{orderdetail_id}", response_model=OrderDetail)
def update_detail(
    orderdetail_id: int,
    detail: OrderDetail,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    db_detail = crud.get_order_detail(db, orderdetail_id, customer_id=current_user.CustomerID)
    if not db_detail:
        raise HTTPException(status_code=404, detail="OrderDetail not found")

    update_data = detail.dict(by_alias=True, exclude_unset=True)

    if "OrderID" in update_data:
        order = crud.get_order(db, update_data["OrderID"], customer_id=current_user.CustomerID)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

    if "ProductID" in update_data:
        product = crud.get_product(db, update_data["ProductID"], owner_customer_id=current_user.CustomerID)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

    return crud.update_order_detail(
        db,
        orderdetail_id,
        customer_id=current_user.CustomerID,
        **update_data,
    )


@router.delete("/orderdetail/{orderdetail_id}")
def delete_detail(
    orderdetail_id: int,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    if not crud.delete_order_detail(db, orderdetail_id, customer_id=current_user.CustomerID):
        raise HTTPException(status_code=404, detail="OrderDetail not found")
    return {"message": "OrderDetail deleted successfully"}


# ---------- HIERARCHICAL ----------
@router.get("/customer/{customer_id}/orders/{order_id}/orderdetail")
def get_details_by_order(
    customer_id: int,
    order_id: int,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    ensure_customer_scope(customer_id, current_user)

    order = crud.get_order(db, order_id, customer_id=customer_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found for this customer")

    return [d for d in crud.get_order_details(db, customer_id=customer_id) if d.OrderID == order_id]


@router.post("/customer/{customer_id}/orders/{order_id}/orderdetail", response_model=OrderDetail)
def create_detail_for_order(
    customer_id: int,
    order_id: int,
    detail: OrderDetail,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    ensure_customer_scope(customer_id, current_user)

    order = crud.get_order(db, order_id, customer_id=customer_id)
    product = crud.get_product(db, detail.ProductID, owner_customer_id=current_user.CustomerID)
    if not order or not product:
        raise HTTPException(status_code=404, detail="Order or Product not found for this customer")

    return crud.create_order_detail(db, order_id, detail.ProductID, detail.quantity)


@router.put("/customer/{customer_id}/orders/{order_id}/orderdetail/{detail_id}", response_model=OrderDetail)
def update_detail_for_order(
    customer_id: int,
    order_id: int,
    detail_id: int,
    detail: OrderDetail,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    ensure_customer_scope(customer_id, current_user)

    order = crud.get_order(db, order_id, customer_id=customer_id)
    db_detail = crud.get_order_detail(db, detail_id, customer_id=customer_id)
    if not order or not db_detail or db_detail.OrderID != order.OrderID:
        raise HTTPException(status_code=404, detail="OrderDetail not found for this customer and order")

    update_data = detail.dict(exclude_unset=True)

    if "ProductID" in update_data:
        product = crud.get_product(db, update_data["ProductID"], owner_customer_id=current_user.CustomerID)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

    return crud.update_order_detail(db, detail_id, customer_id=customer_id, **update_data)


@router.delete("/customer/{customer_id}/orders/{order_id}/orderdetail/{detail_id}")
def delete_detail_for_order(
    customer_id: int,
    order_id: int,
    detail_id: int,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    ensure_customer_scope(customer_id, current_user)

    order = crud.get_order(db, order_id, customer_id=customer_id)
    db_detail = crud.get_order_detail(db, detail_id, customer_id=customer_id)
    if not order or not db_detail or db_detail.OrderID != order.OrderID:
        raise HTTPException(status_code=404, detail="OrderDetail not found for this customer and order")

    if not crud.delete_order_detail(db, detail_id, customer_id=customer_id):
        raise HTTPException(status_code=404, detail="OrderDetail not found")

    return {"message": "OrderDetail deleted successfully"}
