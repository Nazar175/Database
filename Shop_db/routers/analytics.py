from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.post("/create-random-order/{customer_id}")
def create_random_order(customer_id: int, db: Session = Depends(get_db)):
    try:
        db.execute(text("CALL CreateRandomOrderForCustomer(:customer_id)"), {"customer_id": customer_id})
        db.commit()

        order = db.execute(
            text("""
                SELECT o.OrderID, o.OrderDate, o.ShippingAddress, o.Status,
                       c.Name AS CustomerName, c.Email AS CustomerEmail,
                       cr.Name, cr.Country AS CourierCountry, cr.Price AS CourierPrice,
                       pay.Amount AS PaymentAmount, pay.Status AS PaymentStatus, pay.PaymentDate
                FROM Orders o
                JOIN Customer c ON o.CustomerID = c.CustomerID
                LEFT JOIN Courier cr ON o.OrderID = cr.OrderID
                LEFT JOIN Payment pay ON o.OrderID = pay.OrderID
                WHERE o.CustomerID = :customer_id
                ORDER BY o.OrderID DESC
                LIMIT 1
            """),
            {"customer_id": customer_id}
        ).mappings().first()

        if not order:
            raise HTTPException(status_code=404, detail="Order not created")

        return {
            "message": "Random order created successfully ✅",
            "order": dict(order)
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orders-summary")
def get_order_summary(db: Session = Depends(get_db)):
    try:
        result = db.execute(text("SELECT * FROM v_OrderSummary")).mappings().all()
        return {"order_summary": [dict(r) for r in result]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
