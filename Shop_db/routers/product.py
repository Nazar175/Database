import json
import time
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import List
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, condecimal, constr
from sqlalchemy.orm import Session

import crud
import models
from database import get_db
from .customer import ensure_customer_scope, ensure_seller_or_admin, get_current_user, is_admin, is_seller

router = APIRouter()

PRIVAT24_EXCHANGE_URL = "https://api.privatbank.ua/p24api/pubinfo?json&exchange&coursid=5"
_RATES_CACHE_TTL_SECONDS = 300
_rates_cache: dict[str, float | dict[str, Decimal] | None] = {
    "timestamp": 0.0,
    "rates": None,
}


def _fetch_privat24_rates() -> dict[str, Decimal] | None:
    try:
        with urlopen(PRIVAT24_EXCHANGE_URL, timeout=2) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, UnicodeDecodeError):
        return None

    if not isinstance(payload, list):
        return None

    rates: dict[str, Decimal] = {}
    for item in payload:
        if not isinstance(item, dict):
            continue

        currency = (item.get("ccy") or "").upper()
        if currency not in {"USD", "EUR"}:
            continue

        try:
            sale_rate = Decimal(str(item.get("sale")))
        except (InvalidOperation, TypeError, ValueError):
            continue

        if sale_rate > 0:
            rates[currency] = sale_rate

    return rates or None


def _get_privat24_rates() -> dict[str, Decimal] | None:
    now = time.monotonic()
    cached_timestamp = _rates_cache["timestamp"]
    if isinstance(cached_timestamp, float) and (now - cached_timestamp) < _RATES_CACHE_TTL_SECONDS:
        cached_rates = _rates_cache["rates"]
        if isinstance(cached_rates, dict):
            return cached_rates
        return None

    rates = _fetch_privat24_rates()
    _rates_cache["timestamp"] = now
    _rates_cache["rates"] = rates
    return rates


def _as_decimal(value: Decimal | float | int | str) -> Decimal | None:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _convert_from_uah(price_uah: Decimal, rate: Decimal | None) -> Decimal | None:
    if rate is None or rate <= 0:
        return None
    return (price_uah / rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _calculate_approx_prices(price_uah: Decimal | float | int | str) -> tuple[Decimal | None, Decimal | None]:
    normalized_price = _as_decimal(price_uah)
    if normalized_price is None or normalized_price <= 0:
        return None, None

    rates = _get_privat24_rates()
    if not rates:
        return None, None

    approx_usd = _convert_from_uah(normalized_price, rates.get("USD"))
    approx_eur = _convert_from_uah(normalized_price, rates.get("EUR"))
    return approx_usd, approx_eur


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


class ProductReadWithApprox(ProductRead):
    ApproxPriceUSD: Decimal | None = None
    ApproxPriceEUR: Decimal | None = None


# ---------- ROUTES ----------
@router.get("/product", response_model=List[ProductRead])
def read_products(
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    if is_admin(current_user):
        return crud.get_products(db)
    if is_seller(db, current_user):
        return crud.get_products(db, owner_customer_id=current_user.CustomerID)
    return crud.get_products(db)


@router.get("/product/{product_id}", response_model=ProductReadWithApprox)
def read_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    owner_scope = current_user.CustomerID if is_seller(db, current_user) and not is_admin(current_user) else None
    product = crud.get_product(db, product_id, owner_customer_id=owner_scope)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    approx_usd, approx_eur = _calculate_approx_prices(product.Price)
    product_payload = ProductReadWithApprox.model_validate(product)
    return product_payload.model_copy(
        update={
            "ApproxPriceUSD": approx_usd,
            "ApproxPriceEUR": approx_eur,
        }
    )


@router.post("/product", response_model=ProductRead)
def create_product(
    product: ProductCreate,
    db: Session = Depends(get_db),
    current_user: models.Customer = Depends(get_current_user),
):
    ensure_seller_or_admin(db, current_user)
    owner_scope = None if is_admin(current_user) else current_user.CustomerID

    if product.SupplierID:
        supplier = crud.get_supplier(db, product.SupplierID, owner_customer_id=owner_scope)
        if not supplier:
            raise HTTPException(status_code=404, detail="Supplier not found")

    new_product = crud.create_product(
        db,
        product.ProductName,
        product.Price,
        product.SupplierID,
        owner_customer_id=owner_scope if is_admin(current_user) else current_user.CustomerID,
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
    ensure_seller_or_admin(db, current_user)
    owner_scope = None if is_admin(current_user) else current_user.CustomerID
    db_product = crud.get_product(db, product_id, owner_customer_id=owner_scope)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    update_data = product.model_dump(exclude_unset=True)

    if "SupplierID" in update_data and update_data["SupplierID"] is not None:
        supplier = crud.get_supplier(db, update_data["SupplierID"], owner_customer_id=owner_scope)
        if not supplier:
            raise HTTPException(status_code=404, detail="Supplier not found")

    updated = crud.update_product(
        db,
        product_id,
        owner_customer_id=owner_scope,
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
    ensure_seller_or_admin(db, current_user)
    owner_scope = None if is_admin(current_user) else current_user.CustomerID
    if not crud.delete_product(db, product_id, owner_customer_id=owner_scope):
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

    product = crud.get_product(db, detail.ProductID)
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
    ensure_seller_or_admin(db, current_user)
    owner_scope = None if is_admin(current_user) else current_user.CustomerID

    order = crud.get_order(db, order_id, customer_id=customer_id)
    detail = crud.get_order_detail(db, detail_id, customer_id=customer_id)

    if not order or not detail or detail.OrderID != order_id:
        raise HTTPException(status_code=404, detail="Customer, Order, or OrderDetail not found")

    if product.SupplierID is not None:
        supplier = crud.get_supplier(db, product.SupplierID, owner_customer_id=owner_scope)
        if not supplier:
            raise HTTPException(status_code=404, detail="Supplier not found")

    new_product = crud.create_product(
        db,
        product.ProductName,
        product.Price,
        product.SupplierID,
        owner_customer_id=owner_scope if is_admin(current_user) else current_user.CustomerID,
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
    ensure_seller_or_admin(db, current_user)
    owner_scope = None if is_admin(current_user) else current_user.CustomerID

    order = crud.get_order(db, order_id, customer_id=customer_id)
    detail = crud.get_order_detail(db, detail_id, customer_id=customer_id)

    if not order or not detail or detail.OrderID != order_id:
        raise HTTPException(status_code=404, detail="Customer, Order, or OrderDetail not found")

    db_product = crud.get_product(db, detail.ProductID, owner_customer_id=owner_scope)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    update_data = product.dict(exclude_unset=True)

    if "SupplierID" in update_data and update_data["SupplierID"] is not None:
        supplier = crud.get_supplier(db, update_data["SupplierID"], owner_customer_id=owner_scope)
        if not supplier:
            raise HTTPException(status_code=404, detail="Supplier not found")

    updated = crud.update_product(
        db,
        db_product.ProductID,
        owner_customer_id=owner_scope,
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
    ensure_seller_or_admin(db, current_user)
    owner_scope = None if is_admin(current_user) else current_user.CustomerID

    order = crud.get_order(db, order_id, customer_id=customer_id)
    detail = crud.get_order_detail(db, detail_id, customer_id=customer_id)

    if not order or not detail or detail.OrderID != order_id:
        raise HTTPException(status_code=404, detail="Customer, Order, or OrderDetail not found")

    db_product = crud.get_product(db, detail.ProductID, owner_customer_id=owner_scope)
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    crud.update_order_detail(db, detail_id, customer_id=customer_id, ProductID=None)

    if not crud.delete_product(db, db_product.ProductID, owner_customer_id=owner_scope):
        raise HTTPException(status_code=404, detail="Product not found")

    return {"message": "Product deleted successfully"}
