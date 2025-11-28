from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import crud
from pydantic import BaseModel, constr, condecimal, Field
from typing import List

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
        "from_attributes": True
    }


# ---------- ROUTES ----------

@router.get("/product", response_model=List[ProductRead])
def read_products(db: Session = Depends(get_db)):
    return crud.get_products(db)


@router.get("/product/{product_id}", response_model=ProductRead)
def read_product(product_id: int, db: Session = Depends(get_db)):
    product = crud.get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.post("/product", response_model=ProductRead)
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    if product.SupplierID and not crud.get_supplier(db, product.SupplierID):
        raise HTTPException(status_code=404, detail="Supplier not found")

    new_product = crud.create_product(
        db,
        product.ProductName,
        product.Price,
        product.SupplierID
    )
    db.refresh(new_product)
    return new_product


@router.put("/product/{product_id}", response_model=ProductRead)
def update_product(product_id: int, product: ProductBase, db: Session = Depends(get_db)):
    db_product = crud.get_product(db, product_id)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    update_data = product.model_dump(exclude_unset=True)
    updated = crud.update_product(db, product_id, **update_data)

    db.refresh(updated)

    return ProductRead.from_orm(updated).model_dump()



@router.delete("/product/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    if not crud.delete_product(db, product_id):
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product deleted successfully"}


# ---------- HIERARCHICAL ----------

@router.get("/customer/{customer_id}/orders/{order_id}/orderdetail/{detail_id}/product",
            response_model=ProductRead)
def get_product_by_order_detail(customer_id: int, order_id: int, detail_id: int,
                                db: Session = Depends(get_db)):
    customer = crud.get_customer(db, customer_id)
    order = crud.get_order(db, order_id)
    detail = crud.get_order_detail(db, detail_id)

    if not customer or not order or not detail:
        raise HTTPException(status_code=404,
                            detail="Customer, Order, or OrderDetail not found")

    if order.CustomerID != customer_id or detail.OrderID != order_id:
        raise HTTPException(status_code=400,
                            detail="Mismatched Customer, Order, or OrderDetail")

    product = crud.get_product(db, detail.ProductID)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return product


@router.post("/customer/{customer_id}/orders/{order_id}/orderdetail/{detail_id}/product",
             response_model=ProductRead)
def create_product_for_order_detail(customer_id: int, order_id: int, detail_id: int,
                                    product: ProductCreate,
                                    db: Session = Depends(get_db)):
    customer = crud.get_customer(db, customer_id)
    order = crud.get_order(db, order_id)
    detail = crud.get_order_detail(db, detail_id)

    if not customer or not order or not detail:
        raise HTTPException(status_code=404,
                            detail="Customer, Order, or OrderDetail not found")

    if order.CustomerID != customer_id or detail.OrderID != order_id:
        raise HTTPException(status_code=400,
                            detail="Mismatched Customer, Order, or OrderDetail")

    new_product = crud.create_product(
        db,
        product.ProductName,
        product.Price,
        product.SupplierID
    )

    crud.update_order_detail(db, detail_id, ProductID=new_product.ProductID)
    return new_product


@router.put("/customer/{customer_id}/orders/{order_id}/orderdetail/{detail_id}/product",
            response_model=ProductRead)
def update_product_for_order_detail(customer_id: int, order_id: int, detail_id: int,
                                    product: ProductBase,
                                    db: Session = Depends(get_db)):
    customer = crud.get_customer(db, customer_id)
    order = crud.get_order(db, order_id)
    detail = crud.get_order_detail(db, detail_id)

    if not customer or not order or not detail:
        raise HTTPException(status_code=404,
                            detail="Customer, Order, or OrderDetail not found")

    if order.CustomerID != customer_id or detail.OrderID != order_id:
        raise HTTPException(status_code=400,
                            detail="Mismatched Customer, Order, or OrderDetail")

    db_product = crud.get_product(db, detail.ProductID)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    updated = crud.update_product(
        db,
        db_product.ProductID,
        **product.dict(exclude_unset=True)
    )
    return updated


@router.delete("/customer/{customer_id}/orders/{order_id}/orderdetail/{detail_id}/product")
def delete_product_for_order_detail(customer_id: int, order_id: int, detail_id: int,
                                    db: Session = Depends(get_db)):
    customer = crud.get_customer(db, customer_id)
    order = crud.get_order(db, order_id)
    detail = crud.get_order_detail(db, detail_id)

    if not customer or not order or not detail:
        raise HTTPException(status_code=404,
                            detail="Customer, Order, or OrderDetail not found")

    if order.CustomerID != customer_id or detail.OrderID != order_id:
        raise HTTPException(status_code=400,
                            detail="Mismatched Customer, Order, or OrderDetail")

    db_product = crud.get_product(db, detail.ProductID)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    crud.update_order_detail(db, detail_id, ProductID=None)

    if not crud.delete_product(db, db_product.ProductID):
        raise HTTPException(status_code=404, detail="Product not found")

    return {"message": "Product deleted successfully"}