from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, condecimal, constr
from sqlalchemy.orm import Session

import crud
import models
from database import get_db
from .customer import ensure_customer_scope, get_current_user

router = APIRouter()


# ---------- SCHEMAS ----------
class Courier(BaseModel):
    CourierID: int | None = None
    Name: constr(min_length=2, max_length=100) | None = None
    Country: constr(min_length=2, max_length=50) | None = None
    Price: condecimal(gt=0) | None = None
    OrderID: int | None = None

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "validate_by_name": True,
    }

# ---------- ROUTES ----------
@router.get("/courier", response_model=List[Courier])
def read_couriers(
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    return crud.get_couriers(db, customer_id=current_user.CustomerID)


@router.get("/courier/{courier_id}", response_model=Courier)
def read_courier(
    courier_id: int,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    courier = crud.get_courier(db, courier_id, customer_id=current_user.CustomerID)
    if not courier:
        raise HTTPException(status_code=404, detail="Courier not found")
    return courier


@router.post("/courier", response_model=Courier)
def create_courier(
    courier: Courier,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    if courier.OrderID is None:
        raise HTTPException(status_code=400, detail="OrderID is required")

    order = crud.get_order(db, courier.OrderID, customer_id=current_user.CustomerID)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return crud.create_courier(
        db,
        courier.Name,
        courier.Country,
        courier.Price,
        courier.OrderID,
    )


@router.put("/courier/{courier_id}", response_model=Courier)
def update_courier(
    courier_id: int,
    courier: Courier,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    db_courier = crud.get_courier(db, courier_id, customer_id=current_user.CustomerID)
    if not db_courier:
        raise HTTPException(status_code=404, detail="Courier not found")

    data = courier.dict(exclude_unset=True)

    if "OrderID" in data:
        order = crud.get_order(db, data["OrderID"], customer_id=current_user.CustomerID)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

    return crud.update_courier(db, courier_id, customer_id=current_user.CustomerID, **data)


@router.delete("/courier/{courier_id}")
def delete_courier(
    courier_id: int,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    if not crud.delete_courier(db, courier_id, customer_id=current_user.CustomerID):
        raise HTTPException(status_code=404, detail="Courier not found")
    return {"message": "Courier deleted successfully"}


# ---------- HIERARCHICAL ----------
@router.get("/customer/{customer_id}/orders/{order_id}/courier")
def get_courier_by_order(
    customer_id: int,
    order_id: int,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    ensure_customer_scope(customer_id, current_user)

    order = crud.get_order(db, order_id, customer_id=customer_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found for this customer")

    courier = db.query(models.Courier).filter(models.Courier.OrderID == order_id).first()
    if not courier:
        raise HTTPException(status_code=404, detail="Courier not found for this order")

    return courier


@router.post("/customer/{customer_id}/orders/{order_id}/courier", response_model=Courier)
def create_courier_for_order(
    customer_id: int,
    order_id: int,
    courier: Courier,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    ensure_customer_scope(customer_id, current_user)

    order = crud.get_order(db, order_id, customer_id=customer_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found for this customer")

    return crud.create_courier(db, courier.Name, courier.Country, courier.Price, order_id)


@router.put("/customer/{customer_id}/orders/{order_id}/courier", response_model=Courier)
def update_courier_for_order(
    customer_id: int,
    order_id: int,
    courier: Courier,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    ensure_customer_scope(customer_id, current_user)

    order = crud.get_order(db, order_id, customer_id=customer_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found for this customer")

    courier_record = db.query(models.Courier).filter(models.Courier.OrderID == order_id).first()
    if not courier_record:
        raise HTTPException(status_code=404, detail="Courier not found for this order")

    update_data = courier.dict(exclude_unset=True)
    if "OrderID" in update_data and update_data["OrderID"] != order_id:
        target_order = crud.get_order(db, update_data["OrderID"], customer_id=customer_id)
        if not target_order:
            raise HTTPException(status_code=404, detail="Order not found")

    return crud.update_courier(
        db,
        courier_record.CourierID,
        customer_id=customer_id,
        **update_data,
    )


@router.delete("/customer/{customer_id}/orders/{order_id}/courier")
def delete_courier_for_order(
    customer_id: int,
    order_id: int,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    ensure_customer_scope(customer_id, current_user)

    order = crud.get_order(db, order_id, customer_id=customer_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found for this customer")

    courier_record = db.query(models.Courier).filter(models.Courier.OrderID == order_id).first()
    if not courier_record:
        raise HTTPException(status_code=404, detail="Courier not found for this order")

    if not crud.delete_courier(db, courier_record.CourierID, customer_id=customer_id):
        raise HTTPException(status_code=404, detail="Courier not found")

    return {"message": "Courier deleted successfully"}
