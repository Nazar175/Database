from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import crud, models
from pydantic import BaseModel, condecimal, constr, Field
from datetime import datetime
from typing import List

router = APIRouter()

# ---------- SCHEMAS ----------
class Payment(BaseModel):
    PaymentID: int | None = None
    OrderID: int = Field(..., alias="OrderID")
    Status: str = Field(..., alias="Status")
    amount: condecimal(gt=0) = Field(..., alias="amount")
    PaymentDate: datetime = Field(..., alias="PaymentDate")
    PaymentMethod: str | None = Field(None, alias="PaymentMethod")

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "validate_by_name": True,
    }

# ---------- ROUTES ----------
@router.get("/payment", response_model=List[Payment])
def read_payments(db: Session = Depends(get_db)):
    return crud.get_payments(db)


@router.get("/payment/{payment_id}", response_model=Payment)
def read_payment(payment_id: int, db: Session = Depends(get_db)):
    payment = crud.get_payment(db, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment


@router.post("/payment", response_model=Payment)
def create_payment(payment: Payment, db: Session = Depends(get_db)):
    order = crud.get_order(db, payment.OrderID)
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
def update_payment(payment_id: int, payment: Payment, db: Session = Depends(get_db)):
    db_payment = crud.get_payment(db, payment_id)
    if not db_payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return crud.update_payment(db, payment_id, **payment.dict(exclude_unset=True))


@router.delete("/payment/{payment_id}")
def delete_payment(payment_id: int, db: Session = Depends(get_db)):
    if not crud.delete_payment(db, payment_id):
        raise HTTPException(status_code=404, detail="Payment not found")
    return {"message": "Payment deleted successfully"}


# ---------- HIERARCHICAL ----------
@router.get("/customer/{customer_id}/orders/{order_id}/payment")
def get_payment_by_order(customer_id: int, order_id: int, db: Session = Depends(get_db)):
    order = crud.get_order(db, order_id)
    if not order or order.CustomerID != customer_id:
        raise HTTPException(status_code=404, detail="Order not found for this customer")
    payment = db.query(models.Payment).filter(models.Payment.OrderID == order_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found for this order")
    return payment

@router.post("/customer/{customer_id}/orders/{order_id}/payment", response_model=Payment)
def create_payment_for_order(customer_id: int, order_id: int, payment: Payment, db: Session = Depends(get_db)):
    order = crud.get_order(db, order_id)
    if not order or order.CustomerID != customer_id:
        raise HTTPException(status_code=404, detail="Order not found for this customer")
    return crud.create_payment(
        db,
        order_id=order_id,
        status=payment.status,
        amount=payment.amount,
        payment_date=payment.PaymentDate,
    )

@router.put("/customer/{customer_id}/orders/{order_id}/payment", response_model=Payment)
def update_payment_for_order(customer_id: int, order_id: int, payment: Payment, db: Session = Depends(get_db)):
    order = crud.get_order(db, order_id)
    if not order or order.CustomerID != customer_id:
        raise HTTPException(status_code=404, detail="Order not found for this customer")
    payment_record = db.query(models.Payment).filter(models.Payment.OrderID == order_id).first()
    if not payment_record:
        raise HTTPException(status_code=404, detail="Payment not found for this order")
    return crud.update_payment(db, payment_record.PaymentID, **payment.dict(exclude_unset=True))

@router.delete("/customer/{customer_id}/orders/{order_id}/payment")
def delete_payment_for_order(customer_id: int, order_id: int, db: Session = Depends(get_db)):
    order = crud.get_order(db, order_id)
    if not order or order.CustomerID != customer_id:
        raise HTTPException(status_code=404, detail="Order not found for this customer")
    payment_record = db.query(models.Payment).filter(models.Payment.OrderID == order_id).first()
    if not payment_record:
        raise HTTPException(status_code=404, detail="Payment not found for this order")
    if not crud.delete_payment(db, payment_record.PaymentID):
        raise HTTPException(status_code=404, detail="Payment not found")
    return {"message": "Payment deleted successfully"}