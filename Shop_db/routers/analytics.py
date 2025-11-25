import random
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from database import get_db
from models import OrderDetail, Product, Orders, Customer

router = APIRouter(prefix="/analytics", tags=["Analytics"])

def create_random_order_for_customer(db: Session, customer_id: int):
    """Твоя існуюча функція без змін"""
    order = Orders(
        CustomerID=customer_id,
        OrderDate=datetime.now(),
        ShippingAddress=f"Address {random.randint(1,1000)}",
        Status="Pending"
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    product = db.query(Product).order_by(func.random()).first()
    if product:
        order_detail = OrderDetail(
            OrderID=order.OrderID,
            ProductID=product.ProductID,
            Quantity=random.randint(1, 5)
        )
        db.add(order_detail)
        db.commit()
        db.refresh(order_detail)

    return order

@router.post("/create-random-order/{customer_id}")
def create_random_order_endpoint(customer_id: int, db: Session = Depends(get_db)):
    """Endpoint для тесту, який викликає твою функцію"""
    customer = db.query(Customer).filter(Customer.CustomerID == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    order = create_random_order_for_customer(db, customer_id)
    return {
        "message": "Random order created successfully ✅",
        "order": {
            "OrderID": order.OrderID,
            "CustomerID": order.CustomerID,
            "CustomerName": customer.Name,
            "CustomerEmail": customer.Email,
            "OrderDate": order.OrderDate.isoformat(),
            "Status": order.Status,
            "ShippingAddress": order.ShippingAddress
        }
    }


@router.get("/orders-summary")
def get_order_summary(db: Session = Depends(get_db)):
    try:
        results = (
            db.query(
                Orders.OrderID,
                Orders.OrderDate,
                Customer.Name.label("CustomerName"),
                Orders.Status,
                func.sum(OrderDetail.Quantity * Product.Price).label("total_amount")
            )
            .join(OrderDetail, OrderDetail.OrderID == Orders.OrderID)
            .join(Product, Product.ProductID == OrderDetail.ProductID)
            .join(Customer, Customer.CustomerID == Orders.CustomerID)
            .group_by(Orders.OrderID, Orders.OrderDate, Customer.Name, Orders.Status)
            .all()
        )

        summary = [
            {
                "OrderID": r.OrderID,
                "OrderDate": r.OrderDate.isoformat(),
                "CustomerName": r.CustomerName,
                "Status": r.Status,
                "total_amount": float(r.total_amount)
            }
            for r in results
        ]
        return {"order_summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))