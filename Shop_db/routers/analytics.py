from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.post("/create-random-order/{customer_id}")
def create_random_order(customer_id: int, db: Session = Depends(get_db)):
    try:
        
        query = text(f"CALL CreateRandomOrderForCustomer(:customer_id)")
        db.execute(query, {"customer_id": customer_id})
        db.commit()

        result = db.execute(text("SELECT * FROM Orders WHERE CustomerID = :id ORDER BY OrderID DESC LIMIT 1"),
                            {"id": customer_id}).mappings().first()

        if not result:
            raise HTTPException(status_code=404, detail="Order not created")

        return {"message": "Random order created successfully ✅", "order": dict(result)}
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
