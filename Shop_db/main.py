from fastapi import FastAPI, Depends
from database import Base, engine
from routers import (
    customer,
    order,
    orderdetail,
    payment,
    gift,
    courier,
    product,
    supplier,
    analytics,
    auth
)
from routers.auth import get_current_user

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Electron-Shop API",
    description="Магазин електроніки, API для керування клієнтами, замовленнями, товарами та постачальниками.",
    version="1.0.0"
)

app.include_router(auth.router, tags=["Auth"])

app.include_router(customer.router, tags=["Customer"], dependencies=[Depends(get_current_user)])
app.include_router(order.router, tags=["Order"], dependencies=[Depends(get_current_user)])
app.include_router(orderdetail.router, tags=["Order Detail"], dependencies=[Depends(get_current_user)])
app.include_router(payment.router, tags=["Payment"], dependencies=[Depends(get_current_user)])
app.include_router(gift.router, tags=["Gift"], dependencies=[Depends(get_current_user)])
app.include_router(courier.router, tags=["Courier"], dependencies=[Depends(get_current_user)])
app.include_router(product.router, tags=["Product"], dependencies=[Depends(get_current_user)])
app.include_router(supplier.router, tags=["Supplier"], dependencies=[Depends(get_current_user)])
app.include_router(analytics.router, tags=["Analytics"], dependencies=[Depends(get_current_user)])

@app.get("/")
def root():
    return {
        "message": "Welcome to Electron-Shop API 🚀",
        "docs": "/docs",
        "redoc": "/redoc"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
