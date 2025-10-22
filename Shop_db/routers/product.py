from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import crud, models
from pydantic import BaseModel, constr, condecimal, Field
from typing import List

router = APIRouter()

# ---------- SCHEMAS ----------
class Product(BaseModel):
    ProductID: int | None = None
    ProductName: constr(min_length=2, max_length=100) | None = None
    Price: condecimal(gt=0) | None = Field(None, alias="Price")
    SupplierID: int | None = Field(None, alias="SupplierID")

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "validate_by_name": True,
    }

# ---------- ROUTES ----------

@router.get("/product", response_model=List[Product])
def read_products(db: Session = Depends(get_db)):
    return crud.get_products(db)


@router.get("/product/{product_id}", response_model=Product)
def read_product(product_id: int, db: Session = Depends(get_db)):
    product = crud.get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.post("/product", response_model=Product)
def create_product(product: Product, db: Session = Depends(get_db)):
    if product.SupplierID and not crud.get_supplier(db, product.SupplierID):
        raise HTTPException(status_code=404, detail="Supplier not found")
    return crud.create_product(db, product.ProductName, product.Price, product.SupplierID)


@router.put("/product/{product_id}", response_model=Product)
def update_product(product_id: int, product: Product, db: Session = Depends(get_db)):
    db_product = crud.get_product(db, product_id)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    return crud.update_product(db, product_id, **product.dict(exclude_unset=True))


@router.delete("/product/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    if not crud.delete_product(db, product_id):
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product deleted successfully"}


# ---------- HIERARCHICAL ----------
@router.get("/customer/{customer_id}/orders/{order_id}/orderdetail/{detail_id}/product")
def get_product_by_order_detail(customer_id: int, order_id: int, detail_id: int, db: Session = Depends(get_db)):
    customer = crud.get_customer(db, customer_id)
    order = crud.get_order(db, order_id)
    detail = crud.get_order_detail(db, detail_id)
    if not customer or not order or not detail:
        raise HTTPException(status_code=404, detail="Customer, Order, or OrderDetail not found")
    if order.CustomerID != customer_id or detail.OrderID != order_id:
        raise HTTPException(status_code=400, detail="Mismatched Customer, Order, or OrderDetail")
    product = crud.get_product(db, detail.ProductID)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.post("/customer/{customer_id}/orders/{order_id}/orderdetail/{detail_id}/product", response_model=Product)
def create_product_for_order_detail(customer_id: int, order_id: int, detail_id: int, product: Product, db: Session = Depends(get_db)):
    customer = crud.get_customer(db, customer_id)
    order = crud.get_order(db, order_id)
    detail = crud.get_order_detail(db, detail_id)
    if not customer or not order or not detail:
        raise HTTPException(status_code=404, detail="Customer, Order, or OrderDetail not found")
    if order.CustomerID != customer_id or detail.OrderID != order_id:
        raise HTTPException(status_code=400, detail="Mismatched Customer, Order, or OrderDetail")
    new_product = crud.create_product(db, product.productName, product.Price, product.supplierID)
    crud.update_order_detail(db, detail_id, ProductID=new_product.ProductID)
    return new_product

@router.put("/customer/{customer_id}/orders/{order_id}/orderdetail/{detail_id}/product", response_model=Product)
def update_product_for_order_detail(customer_id: int, order_id: int, detail_id: int, product: Product, db: Session = Depends(get_db)):
    customer = crud.get_customer(db, customer_id)
    order = crud.get_order(db, order_id)
    detail = crud.get_order_detail(db, detail_id)
    if not customer or not order or not detail:
        raise HTTPException(status_code=404, detail="Customer, Order, or OrderDetail not found")
    if order.CustomerID != customer_id or detail.OrderID != order_id:
        raise HTTPException(status_code=400, detail="Mismatched Customer, Order, or OrderDetail")
    db_product = crud.get_product(db, detail.ProductID)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    return crud.update_product(db, db_product.ProductID, **product.dict(exclude_unset=True))

@router.delete("/customer/{customer_id}/orders/{order_id}/orderdetail/{detail_id}/product")
def delete_product_for_order_detail(customer_id: int, order_id: int, detail_id: int, db: Session = Depends(get_db)):
    customer = crud.get_customer(db, customer_id)
    order = crud.get_order(db, order_id)
    detail = crud.get_order_detail(db, detail_id)
    if not customer or not order or not detail:
        raise HTTPException(status_code=404, detail="Customer, Order, or OrderDetail not found")
    if order.CustomerID != customer_id or detail.OrderID != order_id:
        raise HTTPException(status_code=400, detail="Mismatched Customer, Order, or OrderDetail")
    db_product = crud.get_product(db, detail.ProductID)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    crud.update_order_detail(db, detail_id, ProductID=None)
    if not crud.delete_product(db, db_product.ProductID):
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product deleted successfully"}