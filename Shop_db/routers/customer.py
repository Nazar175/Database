from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import crud, models
from pydantic import BaseModel, EmailStr, constr
from typing import List

router = APIRouter()

# ---------- SCHEMAS ----------
class CustomerBase(BaseModel):
    CustomerID: int | None = None
    Name: constr(min_length=2, max_length=100)
    Email: EmailStr
    Phone: constr(min_length=6, max_length=20) | None = None
    Country: constr(min_length=2, max_length=50) | None = None

    model_config = {
        "from_attributes": True  # замість orm_mode
    }

class CustomerCreate(BaseModel):
    Name: constr(min_length=2, max_length=100)
    Email: EmailStr
    Phone: constr(min_length=6, max_length=20) | None = None
    Country: constr(min_length=2, max_length=50) | None = None

    model_config = {
        "from_attributes": True
    }

class CustomerUpdate(BaseModel):
    Name: str | None = None
    Email: EmailStr | None = None
    Phone: str | None = None
    Country: str | None = None

    model_config = {
        "from_attributes": True
    }

# ---------- ROUTES ----------
@router.get("/customer", response_model=List[CustomerBase])
def read_customers(db: Session = Depends(get_db)):
    return crud.get_customers(db)

@router.get("/customer/{customer_id}", response_model=CustomerBase)
def read_customer(customer_id: int, db: Session = Depends(get_db)):
    customer = crud.get_customer(db, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer

@router.post("/customer", response_model=CustomerBase)
def create_customer(customer: CustomerCreate, db: Session = Depends(get_db)):
    new_customer = crud.create_customer(
        db,
        Name=customer.Name,
        Email=customer.Email,
        Phone=customer.Phone,
        Country=customer.Country
    )
    db.commit()
    db.refresh(new_customer)
    return new_customer

@router.put("/customer/{customer_id}", response_model=CustomerBase)
def update_customer(customer_id: int, customer: CustomerUpdate, db: Session = Depends(get_db)):
    db_customer = crud.get_customer(db, customer_id)
    if not db_customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return crud.update_customer(db, customer_id, **customer.dict(exclude_unset=True))

@router.delete("/customer/{customer_id}")
def delete_customer(customer_id: int, db: Session = Depends(get_db)):
    db_customer = crud.delete_customer(db, customer_id)
    if not db_customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return {"message": "Customer deleted successfully"}
