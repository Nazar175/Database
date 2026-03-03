from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, constr
from sqlalchemy.orm import Session

import crud
import models
from database import get_db
from .customer import get_current_user
from .product import ProductRead

router = APIRouter()


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


def _ensure_customer_scope(customer_id: int, current_user: models.Customer) -> None:
    if customer_id != current_user.CustomerID:
        raise HTTPException(status_code=403, detail="Access denied")


# ---------- ROUTES ----------
@router.get("/supplier", response_model=List[SupplierRead])
def read_suppliers(
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    return crud.get_suppliers(db, owner_customer_id=current_user.CustomerID)


@router.get("/supplier/{supplier_id}", response_model=SupplierRead)
def read_supplier(
    supplier_id: int,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    supplier = crud.get_supplier(db, supplier_id, owner_customer_id=current_user.CustomerID)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return supplier


@router.post("/supplier", response_model=SupplierRead)
def create_supplier(
    supplier: SupplierCreate,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    new_supplier = crud.create_supplier(
        db,
        supplier_name=supplier.SupplierName,
        address=supplier.Address,
        phone=supplier.Phone,
        delivery_date=supplier.DeliveryDate,
        owner_customer_id=current_user.CustomerID,
    )
    db.refresh(new_supplier)
    return new_supplier


@router.put("/supplier/{supplier_id}", response_model=SupplierRead)
def update_supplier(
    supplier_id: int,
    supplier: SupplierBase,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    db_supplier = crud.get_supplier(db, supplier_id, owner_customer_id=current_user.CustomerID)
    if not db_supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    update_data = supplier.model_dump(exclude_unset=True)
    updated = crud.update_supplier(
        db,
        supplier_id,
        owner_customer_id=current_user.CustomerID,
        **update_data,
    )

    return SupplierRead.from_orm(updated)


@router.delete("/supplier/{supplier_id}")
def delete_supplier(
    supplier_id: int,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    if not crud.delete_supplier(db, supplier_id, owner_customer_id=current_user.CustomerID):
        raise HTTPException(status_code=404, detail="Supplier not found")
    return {"message": "Supplier deleted successfully"}


# ---------- HIERARCHICAL ----------
@router.get(
    "/customer/{customer_id}/orders/{order_id}/orderdetail/{detail_id}/product/{product_id}/supplier",
    response_model=SupplierRead,
)
def get_supplier_by_product(
    customer_id: int,
    order_id: int,
    detail_id: int,
    product_id: int,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    _ensure_customer_scope(customer_id, current_user)

    order = crud.get_order(db, order_id, customer_id=current_user.CustomerID)
    detail = crud.get_order_detail(db, detail_id, customer_id=current_user.CustomerID)
    product = crud.get_product(db, product_id, owner_customer_id=current_user.CustomerID)

    if not order or not detail or not product:
        raise HTTPException(status_code=404, detail="Resource not found")

    if detail.OrderID != order.OrderID or detail.ProductID != product.ProductID:
        raise HTTPException(status_code=400, detail="Mismatched Customer, Order, OrderDetail, or Product")

    supplier = crud.get_supplier(db, product.SupplierID, owner_customer_id=current_user.CustomerID)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    return supplier


@router.post(
    "/customer/{customer_id}/orders/{order_id}/orderdetail/{detail_id}/product/{product_id}/supplier",
    response_model=SupplierRead,
)
def create_supplier_for_product(
    customer_id: int,
    order_id: int,
    detail_id: int,
    product_id: int,
    supplier: SupplierCreate,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    _ensure_customer_scope(customer_id, current_user)

    order = crud.get_order(db, order_id, customer_id=current_user.CustomerID)
    detail = crud.get_order_detail(db, detail_id, customer_id=current_user.CustomerID)
    product = crud.get_product(db, product_id, owner_customer_id=current_user.CustomerID)

    if not order or not detail or not product:
        raise HTTPException(status_code=404, detail="Resource not found")

    if detail.OrderID != order.OrderID or detail.ProductID != product.ProductID:
        raise HTTPException(status_code=400, detail="Mismatched Customer, Order, OrderDetail, or Product")

    new_supplier = crud.create_supplier(
        db,
        supplier_name=supplier.SupplierName,
        address=supplier.Address,
        phone=supplier.Phone,
        delivery_date=supplier.DeliveryDate,
        owner_customer_id=current_user.CustomerID,
    )

    product.SupplierID = new_supplier.SupplierID
    db.commit()
    db.refresh(new_supplier)
    return new_supplier


@router.put(
    "/customer/{customer_id}/orders/{order_id}/orderdetail/{detail_id}/product/{product_id}/supplier/{supplier_id}",
    response_model=SupplierRead,
)
def update_supplier_for_product(
    customer_id: int,
    order_id: int,
    detail_id: int,
    product_id: int,
    supplier_id: int,
    supplier: SupplierBase,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    _ensure_customer_scope(customer_id, current_user)

    order = crud.get_order(db, order_id, customer_id=current_user.CustomerID)
    detail = crud.get_order_detail(db, detail_id, customer_id=current_user.CustomerID)
    product = crud.get_product(db, product_id, owner_customer_id=current_user.CustomerID)
    db_supplier = crud.get_supplier(db, supplier_id, owner_customer_id=current_user.CustomerID)

    if not order or not detail or not product or not db_supplier:
        raise HTTPException(status_code=404, detail="Resource not found")

    if detail.OrderID != order.OrderID or detail.ProductID != product.ProductID or product.SupplierID != db_supplier.SupplierID:
        raise HTTPException(status_code=400, detail="Mismatched Customer, Order, OrderDetail, Product, or Supplier")

    update_data = supplier.dict(exclude_unset=True)
    updated = crud.update_supplier(
        db,
        supplier_id,
        owner_customer_id=current_user.CustomerID,
        **update_data,
    )
    return updated


@router.delete(
    "/customer/{customer_id}/orders/{order_id}/orderdetail/{detail_id}/product/{product_id}/supplier/{supplier_id}"
)
def delete_supplier_for_product(
    customer_id: int,
    order_id: int,
    detail_id: int,
    product_id: int,
    supplier_id: int,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    _ensure_customer_scope(customer_id, current_user)

    order = crud.get_order(db, order_id, customer_id=current_user.CustomerID)
    detail = crud.get_order_detail(db, detail_id, customer_id=current_user.CustomerID)
    product = crud.get_product(db, product_id, owner_customer_id=current_user.CustomerID)
    db_supplier = crud.get_supplier(db, supplier_id, owner_customer_id=current_user.CustomerID)

    if not order or not detail or not product or not db_supplier:
        raise HTTPException(status_code=404, detail="Resource not found")

    if detail.OrderID != order.OrderID or detail.ProductID != product.ProductID or product.SupplierID != db_supplier.SupplierID:
        raise HTTPException(status_code=400, detail="Mismatched Customer, Order, OrderDetail, Product, or Supplier")

    if not crud.delete_supplier(db, supplier_id, owner_customer_id=current_user.CustomerID):
        raise HTTPException(status_code=404, detail="Supplier not found")

    return {"message": "Supplier deleted successfully"}


@router.get("/supplier/{supplier_id}/products", response_model=List[ProductRead])
def get_products_by_supplier(
    supplier_id: int,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    supplier = crud.get_supplier(db, supplier_id, owner_customer_id=current_user.CustomerID)
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    products = (
        db.query(models.Product)
        .filter(models.Product.SupplierID == supplier_id)
        .filter(models.Product.OwnerCustomerID == current_user.CustomerID)
        .all()
    )
    return products
