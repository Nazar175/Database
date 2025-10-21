from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import crud, models
from pydantic import BaseModel, constr, Field
from datetime import datetime
from typing import List

router = APIRouter()


# ---------- SCHEMAS ----------
class SupplierBase(BaseModel):
    SupplierID: int | None = None
    SupplierName: constr(min_length=2, max_length=100) = Field(..., alias="supplierName")
    Address: str | None = None
    Phone: str | None = None
    DeliveryDate: datetime | None = Field(None, alias="deliveryDate")

    model_config = {
        "from_attributes": True,
        "validate_by_name": True
    }


class SupplierCreate(SupplierBase):
    pass


class SupplierUpdate(BaseModel):
    SupplierName: str | None = Field(None, alias="supplierName")
    Address: str | None = None
    Phone: str | None = None
    DeliveryDate: datetime | None = Field(None, alias="deliveryDate")

model_config = {
    "from_attributes": True,
    "validate_by_name": True
}

# ---------- ROUTES ----------
@router.get("/supplier", response_model=List[SupplierBase])
def read_suppliers(db: Session = Depends(get_db)):
    return crud.get_suppliers(db)


@router.get("/supplier/{supplier_id}", response_model=SupplierBase)
def read_supplier(supplier_id: int, db: Session = Depends(get_db)):
    supplier = crud.get_supplier(db, supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return supplier


@router.post("/supplier", response_model=SupplierBase)
def create_supplier(supplier: SupplierCreate, db: Session = Depends(get_db)):
    new_supplier = crud.create_supplier(db, **supplier.dict(by_alias=True))
    db.commit()
    db.refresh(new_supplier)
    return new_supplier


@router.put("/supplier/{supplier_id}", response_model=SupplierBase)
def update_supplier(supplier_id: int, supplier: SupplierUpdate, db: Session = Depends(get_db)):
    db_supplier = crud.get_supplier(db, supplier_id)
    if not db_supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return crud.update_supplier(db, supplier_id, **supplier.dict(exclude_unset=True, by_alias=True))


@router.delete("/supplier/{supplier_id}")
def delete_supplier(supplier_id: int, db: Session = Depends(get_db)):
    if not crud.delete_supplier(db, supplier_id):
        raise HTTPException(status_code=404, detail="Supplier not found")
    return {"message": "Supplier deleted successfully"}


# ---------- HIERARCHICAL ----------
@router.get("/customer/{customer_id}/orders/{order_id}/orderdetail/{detail_id}/product/{product_id}/supplier", response_model=SupplierBase)
def get_supplier_by_product(customer_id: int, order_id: int, detail_id: int, product_id: int, db: Session = Depends(get_db)):
    customer = crud.get_customer(db, customer_id)
    order = crud.get_order(db, order_id)
    detail = crud.get_order_detail(db, detail_id)
    product = crud.get_product(db, product_id)
    if not customer or not order or not detail or not product:
        raise HTTPException(status_code=404, detail="Resource not found")
    if order.CustomerID != customer.CustomerID or detail.OrderID != order.OrderID or detail.ProductID != product.ProductID:
        raise HTTPException(status_code=400, detail="Mismatched Customer, Order, OrderDetail, or Product")
    supplier = crud.get_supplier(db, product.SupplierID)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return supplier


@router.post("/customer/{customer_id}/orders/{order_id}/orderdetail/{detail_id}/product/{product_id}/supplier", response_model=SupplierBase)
def create_supplier_for_product(customer_id: int, order_id: int, detail_id: int, product_id: int, supplier: SupplierBase, db: Session = Depends(get_db)):
    customer = crud.get_customer(db, customer_id)
    order = crud.get_order(db, order_id)
    detail = crud.get_order_detail(db, detail_id)
    product = crud.get_product(db, product_id)
    if not customer or not order or not detail or not product:
        raise HTTPException(status_code=404, detail="Resource not found")
    if order.CustomerID != customer.CustomerID or detail.OrderID != order.OrderID or detail.ProductID != product.ProductID:
        raise HTTPException(status_code=400, detail="Mismatched Customer, Order, OrderDetail, or Product")
    new_supplier = crud.create_supplier(
        db,
        SupplierName=supplier.SupplierName,
        Address=supplier.Address,
        Phone=supplier.Phone,
        DeliveryDate=supplier.DeliveryDate
    )
    product.SupplierID = new_supplier.SupplierID
    db.commit()
    db.refresh(new_supplier)
    return new_supplier


@router.put("/customer/{customer_id}/orders/{order_id}/orderdetail/{detail_id}/product/{product_id}/supplier/{supplier_id}", response_model=SupplierBase)
def update_supplier_for_product(customer_id: int, order_id: int, detail_id: int, product_id: int, supplier_id: int, supplier: SupplierUpdate, db: Session = Depends(get_db)):
    customer = crud.get_customer(db, customer_id)
    order = crud.get_order(db, order_id)
    detail = crud.get_order_detail(db, detail_id)
    product = crud.get_product(db, product_id)
    db_supplier = crud.get_supplier(db, supplier_id)
    if not customer or not order or not detail or not product or not db_supplier:
        raise HTTPException(status_code=404, detail="Resource not found")
    if order.CustomerID != customer.CustomerID or detail.OrderID != order.OrderID or detail.ProductID != product.ProductID or product.SupplierID != db_supplier.SupplierID:
        raise HTTPException(status_code=400, detail="Mismatched Customer, Order, OrderDetail, Product, or Supplier")
    return crud.update_supplier(db, supplier_id, **supplier.dict(exclude_unset=True, by_alias=True))


@router.delete("/customer/{customer_id}/orders/{order_id}/orderdetail/{detail_id}/product/{product_id}/supplier/{supplier_id}")
def delete_supplier_for_product(customer_id: int, order_id: int, detail_id: int, product_id: int, supplier_id: int, db: Session = Depends(get_db)):
    customer = crud.get_customer(db, customer_id)
    order = crud.get_order(db, order_id)
    detail = crud.get_order_detail(db, detail_id)
    product = crud.get_product(db, product_id)
    db_supplier = crud.get_supplier(db, supplier_id)
    if not customer or not order or not detail or not product or not db_supplier:
        raise HTTPException(status_code=404, detail="Resource not found")
    if order.CustomerID != customer.CustomerID or detail.OrderID != order.OrderID or detail.ProductID != product.ProductID or product.SupplierID != db_supplier.SupplierID:
        raise HTTPException(status_code=400, detail="Mismatched Customer, Order, OrderDetail, Product, or Supplier")
    if not crud.delete_supplier(db, supplier_id):
        raise HTTPException(status_code=404, detail="Supplier not found")
    return {"message": "Supplier deleted successfully"}
