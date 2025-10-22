from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import crud, models
from pydantic import BaseModel, constr
from datetime import datetime
from typing import List

router = APIRouter()


def _map_supplier_fields_to_crud(data: dict) -> dict:
    mapping = {
        "SupplierName": "supplier_name",
        "Address": "address",
        "Phone": "phone",
        "DeliveryDate": "delivery_date",
    }

    return {
        new_key: data[old_key]
        for old_key, new_key in mapping.items()
        if old_key in data and data[old_key] is not None
    }


# ---------- SCHEMAS ----------
class Supplier(BaseModel):
    SupplierID: int | None = None
    SupplierName: constr(min_length=2, max_length=100) | None = None
    Address: str | None = None
    Phone: str | None = None
    DeliveryDate: datetime | None = None

    model_config = {
        "from_attributes": True,
        "validate_by_name": True
    }

# ---------- ROUTES ----------
@router.get("/supplier", response_model=List[Supplier])
def read_suppliers(db: Session = Depends(get_db)):
    return crud.get_suppliers(db)


@router.get("/supplier/{supplier_id}", response_model=Supplier)
def read_supplier(supplier_id: int, db: Session = Depends(get_db)):
    supplier = crud.get_supplier(db, supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return supplier


@router.post("/supplier", response_model=Supplier)
def create_supplier(supplier: Supplier, db: Session = Depends(get_db)):
    data = supplier.dict(exclude_unset=True, by_alias=False)
    data.pop("SupplierID", None)

    crud_data = {
        "supplier_name": data.get("SupplierName"),
        "address": data.get("Address"),
        "phone": data.get("Phone"),
        "delivery_date": data.get("DeliveryDate"),
    }

    new_supplier = crud.create_supplier(
        db, **{k: v for k, v in crud_data.items() if v is not None}
    )
    db.commit()
    db.refresh(new_supplier)
    return new_supplier


@router.put("/supplier/{supplier_id}", response_model=Supplier)
def update_supplier(supplier_id: int, supplier: Supplier, db: Session = Depends(get_db)):
    db_supplier = crud.get_supplier(db, supplier_id)
    if not db_supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    data = supplier.dict(exclude_unset=True, by_alias=False)
    data.pop("SupplierID", None)

    crud_data = {
        "SupplierName": data.get("SupplierName"),
        "Address": data.get("Address"),
        "Phone": data.get("Phone"),
        "DeliveryDate": data.get("DeliveryDate"),
    }

    return crud.update_supplier(
        db, supplier_id, **{k: v for k, v in crud_data.items() if v is not None}
    )


@router.delete("/supplier/{supplier_id}")
def delete_supplier(supplier_id: int, db: Session = Depends(get_db)):
    if not crud.delete_supplier(db, supplier_id):
        raise HTTPException(status_code=404, detail="Supplier not found")
    return {"message": "Supplier deleted successfully"}


# ---------- HIERARCHICAL ----------
@router.get("/customer/{customer_id}/orders/{order_id}/orderdetail/{detail_id}/product/{product_id}/supplier", response_model=Supplier)
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


@router.post("/customer/{customer_id}/orders/{order_id}/orderdetail/{detail_id}/product/{product_id}/supplier", response_model=Supplier)
def create_supplier_for_product(customer_id: int, order_id: int, detail_id: int, product_id: int, supplier: Supplier, db: Session = Depends(get_db)):
    customer = crud.get_customer(db, customer_id)
    order = crud.get_order(db, order_id)
    detail = crud.get_order_detail(db, detail_id)
    product = crud.get_product(db, product_id)
    if not customer or not order or not detail or not product:
        raise HTTPException(status_code=404, detail="Resource not found")
    if order.CustomerID != customer.CustomerID or detail.OrderID != order.OrderID or detail.ProductID != product.ProductID:
        raise HTTPException(status_code=400, detail="Mismatched Customer, Order, OrderDetail, or Product")
    supplier_data = supplier.dict(by_alias=False, exclude_unset=True)
    supplier_data.pop("SupplierID", None)
    crud_kwargs = _map_supplier_fields_to_crud(supplier_data)
    new_supplier = crud.create_supplier(db, **crud_kwargs)
    product.SupplierID = new_supplier.SupplierID
    db.commit()
    db.refresh(new_supplier)
    return new_supplier


@router.put("/customer/{customer_id}/orders/{order_id}/orderdetail/{detail_id}/product/{product_id}/supplier/{supplier_id}", response_model=Supplier)
def update_supplier_for_product(customer_id: int, order_id: int, detail_id: int, product_id: int, supplier_id: int, supplier: Supplier, db: Session = Depends(get_db)):
    customer = crud.get_customer(db, customer_id)
    order = crud.get_order(db, order_id)
    detail = crud.get_order_detail(db, detail_id)
    product = crud.get_product(db, product_id)
    db_supplier = crud.get_supplier(db, supplier_id)
    if not customer or not order or not detail or not product or not db_supplier:
        raise HTTPException(status_code=404, detail="Resource not found")
    if order.CustomerID != customer.CustomerID or detail.OrderID != order.OrderID or detail.ProductID != product.ProductID or product.SupplierID != db_supplier.SupplierID:
        raise HTTPException(status_code=400, detail="Mismatched Customer, Order, OrderDetail, Product, or Supplier")
    update_data = supplier.dict(by_alias=False, exclude_unset=True)
    crud_kwargs = _map_supplier_fields_to_crud(update_data)
    return crud.update_supplier(db, supplier_id, **crud_kwargs)


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
