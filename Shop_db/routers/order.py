from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

import crud
import models
from database import get_db
from .customer import ensure_customer_scope, get_current_user, is_admin

router = APIRouter()


# ---------- SCHEMAS ----------
class Order(BaseModel):
    OrderID: int | None = None
    orderDate: datetime | None = Field(None, alias="OrderDate")
    Status: str | None = Field("Pending", alias="Status")
    CustomerID: int | None = Field(None, alias="CustomerID")


class Config:
    orm_mode = True
    allow_population_by_field_name = True


# ---------- ROUTES ----------
@router.get("/order", response_model=List[Order])
def read_orders(
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    return crud.get_orders(db, customer_id=current_user.CustomerID)


@router.get("/order/{order_id}", response_model=Order)
def read_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    order = crud.get_order(db, order_id, customer_id=current_user.CustomerID)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.post("/order", response_model=Order)
def create_order(
    order: Order,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    if not is_admin(current_user):
        if order.CustomerID is not None and order.CustomerID != current_user.CustomerID:
            raise HTTPException(status_code=403, detail="Access denied")
        target_customer_id = current_user.CustomerID
    else:
        target_customer_id = order.CustomerID or current_user.CustomerID

    return crud.create_order(
        db,
        order_date=order.orderDate,
        customer_id=target_customer_id,
        Status=order.Status,
    )


@router.put("/order/{order_id}", response_model=Order)
def update_order(
    order_id: int,
    order: Order,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    db_order = crud.get_order(db, order_id, customer_id=current_user.CustomerID)
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")

    update_data = order.dict(exclude_unset=True, by_alias=True)
    if not is_admin(current_user):
        if "CustomerID" in update_data and update_data["CustomerID"] != current_user.CustomerID:
            raise HTTPException(status_code=403, detail="Access denied")
        update_data["CustomerID"] = current_user.CustomerID

    return crud.update_order(db, order_id, customer_id=current_user.CustomerID, **update_data)


@router.delete("/order/{order_id}")
def delete_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    order = crud.delete_order(db, order_id, customer_id=current_user.CustomerID)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return {"message": "Order deleted successfully"}


# ---------- HIERARCHICAL ----------
@router.get("/customer/{customer_id}/orders")
def get_orders_by_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    ensure_customer_scope(customer_id, current_user)
    return crud.get_orders(db, customer_id=customer_id)


@router.post("/customer/{customer_id}/orders", response_model=Order)
def create_order_for_customer(
    customer_id: int,
    order: Order,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    ensure_customer_scope(customer_id, current_user)

    target_customer_id = customer_id if is_admin(current_user) else current_user.CustomerID

    return crud.create_order(
        db,
        order_date=order.orderDate,
        customer_id=target_customer_id,
        Status=order.Status,
    )


@router.put("/customer/{customer_id}/orders/{order_id}", response_model=Order)
def update_order_for_customer(
    customer_id: int,
    order_id: int,
    order: Order,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    ensure_customer_scope(customer_id, current_user)

    db_order = crud.get_order(db, order_id, customer_id=customer_id)
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found for this customer")

    update_data = order.dict(exclude_unset=True)
    if not is_admin(current_user):
        if "CustomerID" in update_data and update_data["CustomerID"] != current_user.CustomerID:
            raise HTTPException(status_code=403, detail="Access denied")
        update_data["CustomerID"] = current_user.CustomerID
    else:
        update_data["CustomerID"] = customer_id

    return crud.update_order(db, order_id, customer_id=customer_id, **update_data)


@router.delete("/customer/{customer_id}/orders/{order_id}")
def delete_order_for_customer(
    customer_id: int,
    order_id: int,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    ensure_customer_scope(customer_id, current_user)

    db_order = crud.get_order(db, order_id, customer_id=customer_id)
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found for this customer")

    crud.delete_order(db, order_id, customer_id=customer_id)
    return {"message": "Order deleted successfully"}
