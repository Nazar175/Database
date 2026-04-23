import random
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

import crud
from database import get_db
from models import Customer, OrderDetail, Orders, Product
from .customer import ensure_customer_scope, get_current_user, is_admin, is_seller

router = APIRouter(prefix="/analytics", tags=["Analytics"])


class SellerAnalyticsSummary(BaseModel):
    SellerCustomerID: int
    OwnedProductsCount: int
    SoldUnits: int
    SalesAmount: float
    OrdersWithSales: int
    CompletedOrders: int
    PendingOrders: int
    ShippedOrders: int
    CancelledOrders: int


class SellerTopProduct(BaseModel):
    ProductID: int
    ProductName: str
    SoldUnits: int
    SalesAmount: float


def _ensure_seller_only(db: Session, current_user: Customer) -> None:
    if not is_seller(db, current_user):
        raise HTTPException(status_code=403, detail="Only sellers can access seller analytics")


def create_random_order_for_customer(db: Session, customer_id: int):
    order = Orders(
        CustomerID=customer_id,
        OrderDate=datetime.now(),
        Status="Pending",
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    product = (
        db.query(Product)
        .filter(Product.AvailableQuantity > 0)
        .order_by(func.random())
        .first()
    )

    order_detail = None
    if product:
        target_quantity = min(random.randint(1, 5), int(product.AvailableQuantity or 0))
        if target_quantity > 0:
            try:
                order_detail = crud.create_order_detail(
                    db=db,
                    order_id=order.OrderID,
                    product_id=product.ProductID,
                    quantity=target_quantity,
                    shipping_address=f"Address {random.randint(1,1000)}",
                )
            except ValueError:
                order_detail = None

    return order, order_detail


@router.get("/seller/summary", response_model=SellerAnalyticsSummary)
def get_seller_summary(
    db: Session = Depends(get_db),
    current_user: Customer = Depends(get_current_user),
):
    _ensure_seller_only(db, current_user)
    seller_id = current_user.CustomerID

    owned_products_count = (
        db.query(func.count(Product.ProductID))
        .filter(Product.OwnerCustomerID == seller_id)
        .scalar()
        or 0
    )

    sales_totals = (
        db.query(
            func.coalesce(func.sum(OrderDetail.Quantity), 0).label("sold_units"),
            func.coalesce(func.sum(OrderDetail.Quantity * Product.Price), 0).label("sales_amount"),
            func.count(func.distinct(Orders.OrderID)).label("orders_with_sales"),
        )
        .join(Product, Product.ProductID == OrderDetail.ProductID)
        .join(Orders, Orders.OrderID == OrderDetail.OrderID)
        .filter(Product.OwnerCustomerID == seller_id)
        .first()
    )

    sold_units = int(sales_totals.sold_units or 0)
    sales_amount = float(sales_totals.sales_amount or 0.0)
    orders_with_sales = int(sales_totals.orders_with_sales or 0)

    status_rows = (
        db.query(
            Orders.Status.label("status"),
            func.count(func.distinct(Orders.OrderID)).label("orders_count"),
        )
        .join(OrderDetail, OrderDetail.OrderID == Orders.OrderID)
        .join(Product, Product.ProductID == OrderDetail.ProductID)
        .filter(Product.OwnerCustomerID == seller_id)
        .group_by(Orders.Status)
        .all()
    )

    status_counts = {
        "pending": 0,
        "shipped": 0,
        "completed": 0,
        "cancelled": 0,
    }
    for row in status_rows:
        status_value = row.status.value if hasattr(row.status, "value") else str(row.status)
        normalized_status = status_value.lower()
        if normalized_status in status_counts:
            status_counts[normalized_status] = int(row.orders_count or 0)

    return SellerAnalyticsSummary(
        SellerCustomerID=seller_id,
        OwnedProductsCount=int(owned_products_count),
        SoldUnits=sold_units,
        SalesAmount=sales_amount,
        OrdersWithSales=orders_with_sales,
        CompletedOrders=status_counts["completed"],
        PendingOrders=status_counts["pending"],
        ShippedOrders=status_counts["shipped"],
        CancelledOrders=status_counts["cancelled"],
    )


@router.get("/seller/top-products", response_model=list[SellerTopProduct])
def get_seller_top_products(
    limit: int = Query(default=5, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: Customer = Depends(get_current_user),
):
    _ensure_seller_only(db, current_user)
    seller_id = current_user.CustomerID

    sold_units_expr = func.coalesce(func.sum(OrderDetail.Quantity), 0)
    sales_amount_expr = func.coalesce(func.sum(OrderDetail.Quantity * Product.Price), 0)

    top_products = (
        db.query(
            Product.ProductID,
            Product.ProductName,
            sold_units_expr.label("sold_units"),
            sales_amount_expr.label("sales_amount"),
        )
        .outerjoin(OrderDetail, OrderDetail.ProductID == Product.ProductID)
        .filter(Product.OwnerCustomerID == seller_id)
        .group_by(Product.ProductID, Product.ProductName)
        .order_by(sold_units_expr.desc(), Product.ProductID.asc())
        .limit(limit)
        .all()
    )

    return [
        SellerTopProduct(
            ProductID=row.ProductID,
            ProductName=row.ProductName,
            SoldUnits=int(row.sold_units or 0),
            SalesAmount=float(row.sales_amount or 0.0),
        )
        for row in top_products
    ]


@router.post("/create-random-order/{customer_id}")
def create_random_order_endpoint(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: Customer = Depends(get_current_user),
):
    ensure_customer_scope(customer_id, current_user)
    customer = db.query(Customer).filter(Customer.CustomerID == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    order, order_detail = create_random_order_for_customer(db, customer_id)
    return {
        "message": "Random order created successfully ✅",
        "order": {
            "OrderID": order.OrderID,
            "CustomerID": order.CustomerID,
            "CustomerName": customer.Name,
            "CustomerEmail": customer.Email,
            "OrderDate": order.OrderDate.isoformat(),
            "Status": order.Status,
            "ShippingAddress": order_detail.ShippingAddress if order_detail else None,
        },
    }


@router.get("/orders-summary")
def get_order_summary(
    db: Session = Depends(get_db),
    current_user: Customer = Depends(get_current_user),
):
    try:
        query = (
            db.query(
                Orders.OrderID,
                Orders.OrderDate,
                Customer.Name.label("CustomerName"),
                Orders.Status,
                func.sum(OrderDetail.Quantity * Product.Price).label("total_amount"),
            )
            .join(OrderDetail, OrderDetail.OrderID == Orders.OrderID)
            .join(Product, Product.ProductID == OrderDetail.ProductID)
            .join(Customer, Customer.CustomerID == Orders.CustomerID)
            .group_by(Orders.OrderID, Orders.OrderDate, Customer.Name, Orders.Status)
        )
        if not is_admin(current_user):
            query = query.filter(Orders.CustomerID == current_user.CustomerID)
        results = query.all()

        summary = [
            {
                "OrderID": r.OrderID,
                "OrderDate": r.OrderDate.isoformat(),
                "CustomerName": r.CustomerName,
                "Status": r.Status,
                "total_amount": float(r.total_amount),
            }
            for r in results
        ]
        return {"order_summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
