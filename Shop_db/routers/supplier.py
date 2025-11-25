from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import crud
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
class SupplierBase(BaseModel):
    SupplierName: constr(min_length=2, max_length=100)
    Address: str | None = None
    Phone: str | None = None
    DeliveryDate: datetime | None = None


class SupplierCreate(SupplierBase):
    pass


class SupplierRead(SupplierBase):
    SupplierID: int
    model_config = {"from_attributes": True}


# ---------- ROUTES ----------

@router.get("/supplier", response_model=List[SupplierRead])
def read_suppliers(db: Session = Depends(get_db)):
    return crud.get_suppliers(db)


@router.get("/supplier/{supplier_id}", response_model=SupplierRead)
def read_supplier(supplier_id: int, db: Session = Depends(get_db)):
    supplier = crud.get_supplier(db, supplier_id)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return supplier


@router.post("/supplier", response_model=SupplierRead)
def create_supplier(supplier: SupplierCreate, db: Session = Depends(get_db)):
    new_supplier = crud.create_supplier(
        db,
        supplier_name=supplier.SupplierName,
        address=supplier.Address,
        phone=supplier.Phone,
        delivery_date=supplier.DeliveryDate
    )
    db.refresh(new_supplier)
    return new_supplier


@router.put("/supplier/{supplier_id}", response_model=SupplierRead)
def update_supplier(supplier_id: int, supplier: SupplierBase, db: Session = Depends(get_db)):
    db_supplier = crud.get_supplier(db, supplier_id)
    if not db_supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    update_data = supplier.model_dump(exclude_unset=True)

    updated = crud.update_supplier(db, supplier_id, **update_data)

    return SupplierRead.from_orm(updated)



@router.delete("/supplier/{supplier_id}")
def delete_supplier(supplier_id: int, db: Session = Depends(get_db)):
    if not crud.delete_supplier(db, supplier_id):
        raise HTTPException(status_code=404, detail="Supplier not found")
    return {"message": "Supplier deleted successfully"}


# ---------- HIERARCHICAL ----------

@router.get(
    "/customer/{customer_id}/orders/{order_id}/orderdetail/{detail_id}/product/{product_id}/supplier",
    response_model=SupplierRead,
)
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


@router.post(
    "/customer/{customer_id}/orders/{order_id}/orderdetail/{detail_id}/product/{product_id}/supplier",
    response_model=SupplierRead,
)
def create_supplier_for_product(customer_id: int, order_id: int, detail_id: int, product_id: int, supplier: SupplierCreate, db: Session = Depends(get_db)):
    customer = crud.get_customer(db, customer_id)
    order = crud.get_order(db, order_id)
    detail = crud.get_order_detail(db, detail_id)
    product = crud.get_product(db, product_id)
    if not customer or not order or not detail or not product:
        raise HTTPException(status_code=404, detail="Resource not found")
    if order.CustomerID != customer.CustomerID or detail.OrderID != order.OrderID or detail.ProductID != product.ProductID:
        raise HTTPException(status_code=400, detail="Mismatched Customer, Order, OrderDetail, or Product")

    supplier_data = supplier.dict(exclude_unset=True)
    crud_kwargs = _map_supplier_fields_to_crud(supplier_data)
    new_supplier = crud.create_supplier(db, **crud_kwargs)
    product.SupplierID = new_supplier.SupplierID
    db.commit()
    db.refresh(new_supplier)
    return new_supplier


@router.put(
    "/customer/{customer_id}/orders/{order_id}/orderdetail/{detail_id}/product/{product_id}/supplier/{supplier_id}",
    response_model=SupplierRead,
)
def update_supplier_for_product(customer_id: int, order_id: int, detail_id: int, product_id: int, supplier_id: int, supplier: SupplierBase, db: Session = Depends(get_db)):
    customer = crud.get_customer(db, customer_id)
    order = crud.get_order(db, order_id)
    detail = crud.get_order_detail(db, detail_id)
    product = crud.get_product(db, product_id)
    db_supplier = crud.get_supplier(db, supplier_id)
    if not customer or not order or not detail or not product or not db_supplier:
        raise HTTPException(status_code=404, detail="Resource not found")
    if order.CustomerID != customer.CustomerID or detail.OrderID != order.OrderID or detail.ProductID != product.ProductID or product.SupplierID != db_supplier.SupplierID:
        raise HTTPException(status_code=400, detail="Mismatched Customer, Order, OrderDetail, Product, or Supplier")
    update_data = supplier.dict(exclude_unset=True)
    crud_kwargs = _map_supplier_fields_to_crud(update_data)
    updated = crud.update_supplier(db, supplier_id, **crud_kwargs)
    return updated


@router.delete(
    "/customer/{customer_id}/orders/{order_id}/orderdetail/{detail_id}/product/{product_id}/supplier/{supplier_id}"
)
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
