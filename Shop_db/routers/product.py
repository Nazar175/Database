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
class ProductBase(BaseModel):
    ProductName: constr(min_length=2, max_length=100)
    Price: condecimal(gt=0)
    SupplierID: int | None = None


class ProductCreate(ProductBase):
    pass


class ProductRead(ProductBase):
    ProductID: int

    model_config = {
        "from_attributes": True,
    }

# ---------- ROUTES ----------
@router.get("/product", response_model=List[ProductRead])
def read_products(
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    return crud.get_products(db, owner_customer_id=current_user.CustomerID)


@router.get("/product/{product_id}", response_model=ProductRead)
def read_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    product = crud.get_product(db, product_id, owner_customer_id=current_user.CustomerID)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.post("/product", response_model=ProductRead)
def create_product(
    product: ProductCreate,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    if product.SupplierID:
        supplier = crud.get_supplier(db, product.SupplierID, owner_customer_id=current_user.CustomerID)
        if not supplier:
            raise HTTPException(status_code=404, detail="Supplier not found")

    new_product = crud.create_product(
        db,
        product.ProductName,
        product.Price,
        product.SupplierID,
        owner_customer_id=current_user.CustomerID,
    )
    db.refresh(new_product)
    return new_product


@router.put("/product/{product_id}", response_model=ProductRead)
def update_product(
    product_id: int,
    product: ProductBase,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    db_product = crud.get_product(db, product_id, owner_customer_id=current_user.CustomerID)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    update_data = product.model_dump(exclude_unset=True)

    if "SupplierID" in update_data and update_data["SupplierID"] is not None:
        supplier = crud.get_supplier(db, update_data["SupplierID"], owner_customer_id=current_user.CustomerID)
        if not supplier:
            raise HTTPException(status_code=404, detail="Supplier not found")

    updated = crud.update_product(
        db,
        product_id,
        owner_customer_id=current_user.CustomerID,
        **update_data,
    )
    db.refresh(updated)
    return ProductRead.from_orm(updated).model_dump()


@router.delete("/product/{product_id}")
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    if not crud.delete_product(db, product_id, owner_customer_id=current_user.CustomerID):
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product deleted successfully"}


# ---------- HIERARCHICAL ----------
@router.get("/customer/{customer_id}/orders/{order_id}/orderdetail/{detail_id}/product", response_model=ProductRead)
def get_product_by_order_detail(
    customer_id: int,
    order_id: int,
    detail_id: int,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    ensure_customer_scope(customer_id, current_user)

    order = crud.get_order(db, order_id, customer_id=customer_id)
    detail = crud.get_order_detail(db, detail_id, customer_id=customer_id)

    if not order or not detail or detail.OrderID != order_id:
        raise HTTPException(status_code=404, detail="Customer, Order, or OrderDetail not found")

    product = crud.get_product(db, detail.ProductID, owner_customer_id=current_user.CustomerID)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return product


@router.post("/customer/{customer_id}/orders/{order_id}/orderdetail/{detail_id}/product", response_model=ProductRead)
def create_product_for_order_detail(
    customer_id: int,
    order_id: int,
    detail_id: int,
    product: ProductCreate,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    ensure_customer_scope(customer_id, current_user)

    order = crud.get_order(db, order_id, customer_id=customer_id)
    detail = crud.get_order_detail(db, detail_id, customer_id=customer_id)

    if not order or not detail or detail.OrderID != order_id:
        raise HTTPException(status_code=404, detail="Customer, Order, or OrderDetail not found")

    if product.SupplierID is not None:
        supplier = crud.get_supplier(db, product.SupplierID, owner_customer_id=current_user.CustomerID)
        if not supplier:
            raise HTTPException(status_code=404, detail="Supplier not found")

    new_product = crud.create_product(
        db,
        product.ProductName,
        product.Price,
        product.SupplierID,
        owner_customer_id=current_user.CustomerID,
    )

    crud.update_order_detail(db, detail_id, customer_id=customer_id, ProductID=new_product.ProductID)
    return new_product


@router.put("/customer/{customer_id}/orders/{order_id}/orderdetail/{detail_id}/product", response_model=ProductRead)
def update_product_for_order_detail(
    customer_id: int,
    order_id: int,
    detail_id: int,
    product: ProductBase,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    ensure_customer_scope(customer_id, current_user)

    order = crud.get_order(db, order_id, customer_id=customer_id)
    detail = crud.get_order_detail(db, detail_id, customer_id=customer_id)

    if not order or not detail or detail.OrderID != order_id:
        raise HTTPException(status_code=404, detail="Customer, Order, or OrderDetail not found")

    db_product = crud.get_product(db, detail.ProductID, owner_customer_id=current_user.CustomerID)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    update_data = product.dict(exclude_unset=True)

    if "SupplierID" in update_data and update_data["SupplierID"] is not None:
        supplier = crud.get_supplier(db, update_data["SupplierID"], owner_customer_id=current_user.CustomerID)
        if not supplier:
            raise HTTPException(status_code=404, detail="Supplier not found")

    updated = crud.update_product(
        db,
        db_product.ProductID,
        owner_customer_id=current_user.CustomerID,
        **update_data,
    )
    return updated


@router.delete("/customer/{customer_id}/orders/{order_id}/orderdetail/{detail_id}/product")
def delete_product_for_order_detail(
    customer_id: int,
    order_id: int,
    detail_id: int,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    ensure_customer_scope(customer_id, current_user)

    order = crud.get_order(db, order_id, customer_id=customer_id)
    detail = crud.get_order_detail(db, detail_id, customer_id=customer_id)

    if not order or not detail or detail.OrderID != order_id:
        raise HTTPException(status_code=404, detail="Customer, Order, or OrderDetail not found")

    db_product = crud.get_product(db, detail.ProductID, owner_customer_id=current_user.CustomerID)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    crud.update_order_detail(db, detail_id, customer_id=customer_id, ProductID=None)

    if not crud.delete_product(db, db_product.ProductID, owner_customer_id=current_user.CustomerID):
        raise HTTPException(status_code=404, detail="Product not found")

    return {"message": "Product deleted successfully"}
