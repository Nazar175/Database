from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

import crud
import models
from database import get_db
from .customer import get_current_user

router = APIRouter()


# ---------- SCHEMAS ----------
class Payment(BaseModel):
    PaymentID: int | None = None
    OrderID: int | None = None
    Status: str | None = None
    amount: float | None = Field(None, alias="Amount")
    PaymentDate: datetime | None = None
    PaymentMethod: str | None = None

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "validate_by_name": True,
    }


def _ensure_customer_scope(customer_id: int, current_user: models.Customer) -> None:
    if customer_id != current_user.CustomerID:
        raise HTTPException(status_code=403, detail="Access denied")


# ---------- ROUTES ----------
@router.get("/payment", response_model=List[Payment])
def read_payments(
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    return crud.get_payments(db, customer_id=current_user.CustomerID)


@router.get("/payment/{payment_id}", response_model=Payment)
def read_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    payment = crud.get_payment(db, payment_id, customer_id=current_user.CustomerID)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment


@router.post("/payment", response_model=Payment)
def create_payment(
    payment: Payment,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    order = crud.get_order(db, payment.OrderID, customer_id=current_user.CustomerID)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return crud.create_payment(
        db,
        order_id=payment.OrderID,
        Status=payment.Status,
        amount=payment.amount,
        payment_date=payment.PaymentDate,
    )


@router.put("/payment/{payment_id}", response_model=Payment)
def update_payment(
    payment_id: int,
    payment: Payment,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    db_payment = crud.get_payment(db, payment_id, customer_id=current_user.CustomerID)
    if not db_payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    update_data = payment.dict(exclude_unset=True)

    if "OrderID" in update_data:
        order = crud.get_order(db, update_data["OrderID"], customer_id=current_user.CustomerID)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

    return crud.update_payment(db, payment_id, customer_id=current_user.CustomerID, **update_data)


@router.delete("/payment/{payment_id}")
def delete_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    if not crud.delete_payment(db, payment_id, customer_id=current_user.CustomerID):
        raise HTTPException(status_code=404, detail="Payment not found")
    return {"message": "Payment deleted successfully"}


# ---------- HIERARCHICAL ----------
@router.get("/customer/{customer_id}/orders/{order_id}/payment")
def get_payment_by_order(
    customer_id: int,
    order_id: int,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    _ensure_customer_scope(customer_id, current_user)

    order = crud.get_order(db, order_id, customer_id=current_user.CustomerID)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found for this customer")

    payment = db.query(models.Payment).filter(models.Payment.OrderID == order_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found for this order")

    return payment


@router.post("/customer/{customer_id}/orders/{order_id}/payment", response_model=Payment)
def create_payment_for_order(
    customer_id: int,
    order_id: int,
    payment: Payment,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    _ensure_customer_scope(customer_id, current_user)

    order = crud.get_order(db, order_id, customer_id=current_user.CustomerID)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found for this customer")

    return crud.create_payment(
        db,
        order_id=order_id,
        Status=payment.Status,
        amount=payment.amount,
        payment_date=payment.PaymentDate,
    )


@router.put("/customer/{customer_id}/orders/{order_id}/payment", response_model=Payment)
def update_payment_for_order(
    customer_id: int,
    order_id: int,
    payment: Payment,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    _ensure_customer_scope(customer_id, current_user)

    order = crud.get_order(db, order_id, customer_id=current_user.CustomerID)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found for this customer")

    payment_record = db.query(models.Payment).filter(models.Payment.OrderID == order_id).first()
    if not payment_record:
        raise HTTPException(status_code=404, detail="Payment not found for this order")

    return crud.update_payment(
        db,
        payment_record.PaymentID,
        customer_id=current_user.CustomerID,
        **payment.dict(exclude_unset=True),
    )


@router.delete("/customer/{customer_id}/orders/{order_id}/payment")
def delete_payment_for_order(
    customer_id: int,
    order_id: int,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    _ensure_customer_scope(customer_id, current_user)

    order = crud.get_order(db, order_id, customer_id=current_user.CustomerID)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found for this customer")

    payment_record = db.query(models.Payment).filter(models.Payment.OrderID == order_id).first()
    if not payment_record:
        raise HTTPException(status_code=404, detail="Payment not found for this order")

    if not crud.delete_payment(db, payment_record.PaymentID, customer_id=current_user.CustomerID):
        raise HTTPException(status_code=404, detail="Payment not found")

    return {"message": "Payment deleted successfully"}
