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
class Gift(BaseModel):
    GiftID: int | None = None
    amount: float | None = Field(None, alias="Amount")
    exparesDate: datetime | None = Field(None, alias="ExparesDate")
    type: str | None = Field(None, alias="Type")
    unit: str | None = Field(None, alias="Unit")
    paymentID: int | None = Field(None, alias="PaymentID")

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "validate_by_name": True,
    }


def _ensure_customer_scope(customer_id: int, current_user: models.Customer) -> None:
    if customer_id != current_user.CustomerID:
        raise HTTPException(status_code=403, detail="Access denied")


# ---------- ROUTES ----------
@router.get("/gift", response_model=List[Gift])
def read_gifts(
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    return crud.get_gifts(db, customer_id=current_user.CustomerID)


@router.get("/gift/{gift_id}", response_model=Gift)
def read_gift(
    gift_id: int,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    gift = crud.get_gift(db, gift_id, customer_id=current_user.CustomerID)
    if not gift:
        raise HTTPException(status_code=404, detail="Gift not found")
    return gift


@router.post("/gift", response_model=Gift)
def create_gift(
    gift: Gift,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    if gift.paymentID:
        payment = crud.get_payment(db, gift.paymentID, customer_id=current_user.CustomerID)
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")

    return crud.create_gift(
        db,
        amount=gift.amount,
        exp_date=gift.exparesDate,
        type_=gift.type,
        unit=gift.unit,
        payment_id=gift.paymentID,
    )


@router.put("/gift/{gift_id}", response_model=Gift)
def update_gift(
    gift_id: int,
    gift: Gift,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    db_gift = crud.get_gift(db, gift_id, customer_id=current_user.CustomerID)
    if not db_gift:
        raise HTTPException(status_code=404, detail="Gift not found")

    update_data = gift.dict(by_alias=True, exclude_unset=True)

    if "PaymentID" in update_data:
        payment = crud.get_payment(db, update_data["PaymentID"], customer_id=current_user.CustomerID)
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")

    return crud.update_gift(db, gift_id, customer_id=current_user.CustomerID, **update_data)


@router.delete("/gift/{gift_id}")
def delete_gift(
    gift_id: int,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    if not crud.delete_gift(db, gift_id, customer_id=current_user.CustomerID):
        raise HTTPException(status_code=404, detail="Gift not found")
    return {"message": "Gift deleted successfully"}


# ---------- HIERARCHICAL ----------
@router.get("/customer/{customer_id}/orders/{order_id}/payment/{payment_id}/gifts")
def get_gifts_by_payment(
    customer_id: int,
    order_id: int,
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    _ensure_customer_scope(customer_id, current_user)

    order = crud.get_order(db, order_id, customer_id=current_user.CustomerID)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found for this customer")

    payment = crud.get_payment(db, payment_id, customer_id=current_user.CustomerID)
    if not payment or payment.OrderID != order_id:
        raise HTTPException(status_code=404, detail="Payment not found for this order")

    return [g for g in crud.get_gifts(db, customer_id=current_user.CustomerID) if g.PaymentID == payment_id]


@router.post("/customer/{customer_id}/orders/{order_id}/payment/{payment_id}/gift", response_model=Gift)
def create_gift_for_payment(
    customer_id: int,
    order_id: int,
    payment_id: int,
    gift: Gift,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    _ensure_customer_scope(customer_id, current_user)

    order = crud.get_order(db, order_id, customer_id=current_user.CustomerID)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found for this customer")

    payment = crud.get_payment(db, payment_id, customer_id=current_user.CustomerID)
    if not payment or payment.OrderID != order_id:
        raise HTTPException(status_code=404, detail="Payment not found for this order")

    return crud.create_gift(
        db,
        amount=gift.amount,
        exp_date=gift.exparesDate,
        type_=gift.type,
        unit=gift.unit,
        payment_id=payment_id,
    )


@router.put("/customer/{customer_id}/orders/{order_id}/payment/{payment_id}/gift/{gift_id}", response_model=Gift)
def update_gift_for_payment(
    customer_id: int,
    order_id: int,
    payment_id: int,
    gift_id: int,
    gift: Gift,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    _ensure_customer_scope(customer_id, current_user)

    order = crud.get_order(db, order_id, customer_id=current_user.CustomerID)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found for this customer")

    payment = crud.get_payment(db, payment_id, customer_id=current_user.CustomerID)
    if not payment or payment.OrderID != order_id:
        raise HTTPException(status_code=404, detail="Payment not found for this order")

    db_gift = crud.get_gift(db, gift_id, customer_id=current_user.CustomerID)
    if not db_gift or db_gift.PaymentID != payment_id:
        raise HTTPException(status_code=404, detail="Gift not found for this payment")

    return crud.update_gift(
        db,
        gift_id,
        customer_id=current_user.CustomerID,
        **gift.dict(exclude_unset=True),
    )


@router.delete("/customer/{customer_id}/orders/{order_id}/payment/{payment_id}/gift/{gift_id}")
def delete_gift_for_payment(
    customer_id: int,
    order_id: int,
    payment_id: int,
    gift_id: int,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    _ensure_customer_scope(customer_id, current_user)

    order = crud.get_order(db, order_id, customer_id=current_user.CustomerID)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found for this customer")

    payment = crud.get_payment(db, payment_id, customer_id=current_user.CustomerID)
    if not payment or payment.OrderID != order_id:
        raise HTTPException(status_code=404, detail="Payment not found for this order")

    db_gift = crud.get_gift(db, gift_id, customer_id=current_user.CustomerID)
    if not db_gift or db_gift.PaymentID != payment_id:
        raise HTTPException(status_code=404, detail="Gift not found for this payment")

    if not crud.delete_gift(db, gift_id, customer_id=current_user.CustomerID):
        raise HTTPException(status_code=404, detail="Gift not found")

    return {"message": "Gift deleted successfully"}
