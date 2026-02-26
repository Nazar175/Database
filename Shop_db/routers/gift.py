from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import crud, models
from pydantic import BaseModel, condecimal, constr, Field
from datetime import datetime
from typing import List

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

# ---------- ROUTES ----------
@router.get("/gift", response_model=List[Gift])
def read_gifts(db: Session = Depends(get_db)):
    return crud.get_gifts(db)


@router.get("/gift/{gift_id}", response_model=Gift)
def read_gift(gift_id: int, db: Session = Depends(get_db)):
    gift = crud.get_gift(db, gift_id)
    if not gift:
        raise HTTPException(status_code=404, detail="Gift not found")
    return gift


@router.post("/gift", response_model=Gift)
def create_gift(gift: Gift, db: Session = Depends(get_db)):
    if gift.paymentID and not crud.get_payment(db, gift.paymentID):
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
def update_gift(gift_id: int, gift: Gift, db: Session = Depends(get_db)):
    db_gift = crud.get_gift(db, gift_id)
    if not db_gift:
        raise HTTPException(status_code=404, detail="Gift not found")
    return crud.update_gift(db, gift_id, **gift.dict(by_alias=True, exclude_unset=True))


@router.delete("/gift/{gift_id}")
def delete_gift(gift_id: int, db: Session = Depends(get_db)):
    if not crud.delete_gift(db, gift_id):
        raise HTTPException(status_code=404, detail="Gift not found")
    return {"message": "Gift deleted successfully"}


# ---------- HIERARCHICAL ----------
@router.get("/customer/{customer_id}/orders/{order_id}/payment/{payment_id}/gifts")
def get_gifts_by_payment(customer_id: int, order_id: int, payment_id: int, db: Session = Depends(get_db)):
    order = crud.get_order(db, order_id)
    if not order or order.CustomerID != customer_id:
        raise HTTPException(status_code=404, detail="Order not found for this customer")
    payment = crud.get_payment(db, payment_id)
    if not payment or payment.OrderID != order_id:
        raise HTTPException(status_code=404, detail="Payment not found for this order")
    return [g for g in crud.get_gifts(db) if g.PaymentID == payment_id]

@router.post("/customer/{customer_id}/orders/{order_id}/payment/{payment_id}/gift", response_model=Gift)
def create_gift_for_payment(customer_id: int, order_id: int, payment_id: int, gift: Gift, db: Session = Depends(get_db)):
    order = crud.get_order(db, order_id)
    if not order or order.CustomerID != customer_id:
        raise HTTPException(status_code=404, detail="Order not found for this customer")
    payment = crud.get_payment(db, payment_id)
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
def update_gift_for_payment(customer_id: int, order_id: int, payment_id: int, gift_id: int, gift: Gift, db: Session = Depends(get_db)):
    order = crud.get_order(db, order_id)
    if not order or order.CustomerID != customer_id:
        raise HTTPException(status_code=404, detail="Order not found for this customer")
    payment = crud.get_payment(db, payment_id)
    if not payment or payment.OrderID != order_id:
        raise HTTPException(status_code=404, detail="Payment not found for this order")
    db_gift = crud.get_gift(db, gift_id)
    if not db_gift or db_gift.PaymentID != payment_id:
        raise HTTPException(status_code=404, detail="Gift not found for this payment")
    return crud.update_gift(db, gift_id, **gift.dict(exclude_unset=True))

@router.delete("/customer/{customer_id}/orders/{order_id}/payment/{payment_id}/gift/{gift_id}")
def delete_gift_for_payment(customer_id: int, order_id: int, payment_id: int, gift_id: int, db: Session = Depends(get_db)):
    order = crud.get_order(db, order_id)
    if not order or order.CustomerID != customer_id:
        raise HTTPException(status_code=404, detail="Order not found for this customer")
    payment = crud.get_payment(db, payment_id)
    if not payment or payment.OrderID != order_id:
        raise HTTPException(status_code=404, detail="Payment not found for this order")
    db_gift = crud.get_gift(db, gift_id)
    if not db_gift or db_gift.PaymentID != payment_id:
        raise HTTPException(status_code=404, detail="Gift not found for this payment")
    if not crud.delete_gift(db, gift_id):
        raise HTTPException(status_code=404, detail="Gift not found")
    return {"message": "Gift deleted successfully"}