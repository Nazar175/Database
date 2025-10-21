from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import crud, models
from pydantic import BaseModel, constr, condecimal
from typing import List

router = APIRouter()

class CourierBase(BaseModel):
    name: constr(min_length=2, max_length=100)
    country: constr(min_length=2, max_length=50)
    price: condecimal(gt=0)
    orderID: int

class CourierUpdate(BaseModel):
    name: str | None = None
    country: str | None = None
    price: float | None = None


@router.get("/courier", response_model=List[CourierBase])
def read_couriers(db: Session = Depends(get_db)):
    return crud.get_couriers(db)


@router.get("/courier/{courier_id}", response_model=CourierBase)
def read_courier(courier_id: int, db: Session = Depends(get_db)):
    courier = crud.get_courier(db, courier_id)
    if not courier:
        raise HTTPException(status_code=404, detail="Courier not found")
    return courier


@router.post("/courier", response_model=CourierBase)
def create_courier(courier: CourierBase, db: Session = Depends(get_db)):
    order = crud.get_order(db, courier.OrderID)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return crud.create_courier(db, courier.Name, courier.Country, courier.Price, courier.OrderID)


@router.put("/courier/{courier_id}", response_model=CourierBase)
def update_courier(courier_id: int, courier: CourierUpdate, db: Session = Depends(get_db)):
    db_courier = crud.get_courier(db, courier_id)
    if not db_courier:
        raise HTTPException(status_code=404, detail="Courier not found")
    return crud.update_courier(db, courier_id, **courier.dict(exclude_unset=True))


@router.delete("/courier/{courier_id}")
def delete_courier(courier_id: int, db: Session = Depends(get_db)):
    if not crud.delete_courier(db, courier_id):
        raise HTTPException(status_code=404, detail="Courier not found")
    return {"message": "Courier deleted successfully"}


# ---------- HIERARCHICAL ----------
@router.get("/customer/{customer_id}/orders/{order_id}/courier")
def get_courier_by_order(customer_id: int, order_id: int, db: Session = Depends(get_db)):
    order = crud.get_order(db, order_id)
    if not order or order.CustomerID != customer_id:
        raise HTTPException(status_code=404, detail="Order not found for this customer")
    courier = db.query(models.Courier).filter(models.Courier.OrderID == order_id).first()
    if not courier:
        raise HTTPException(status_code=404, detail="Courier not found for this order")
    return courier

@router.post("/customer/{customer_id}/orders/{order_id}/courier", response_model=CourierBase)
def create_courier_for_order(customer_id: int, order_id: int, courier: CourierBase, db: Session = Depends(get_db)):
    order = crud.get_order(db, order_id)
    if not order or order.CustomerID != customer_id:
        raise HTTPException(status_code=404, detail="Order not found for this customer")
    return crud.create_courier(db, courier.Name, courier.Country, courier.Price, order_id)

@router.put("/customer/{customer_id}/orders/{order_id}/courier", response_model=CourierBase)
def update_courier_for_order(customer_id: int, order_id: int, courier: CourierUpdate, db: Session = Depends(get_db)):
    order = crud.get_order(db, order_id)
    if not order or order.CustomerID != customer_id:
        raise HTTPException(status_code=404, detail="Order not found for this customer")
    courier_record = db.query(models.Courier).filter(models.Courier.OrderID == order_id).first()
    if not courier_record:
        raise HTTPException(status_code=404, detail="Courier not found for this order")
    return crud.update_courier(db, courier_record.ID, **courier.dict(exclude_unset=True))

@router.delete("/customer/{customer_id}/orders/{order_id}/courier")
def delete_courier_for_order(customer_id: int, order_id: int, db: Session = Depends(get_db)):
    order = crud.get_order(db, order_id)
    if not order or order.CustomerID != customer_id:
        raise HTTPException(status_code=404, detail="Order not found for this customer")
    courier_record = db.query(models.Courier).filter(models.Courier.OrderID == order_id).first()
    if not courier_record:
        raise HTTPException(status_code=404, detail="Courier not found for this order")
    if not crud.delete_courier(db, courier_record.ID):
        raise HTTPException(status_code=404, detail="Courier not found")
    return {"message": "Courier deleted successfully"}

    raise HTTPException(status_code=404, detail="Payment not found for this order")
    return payment