from fastapi import FastAPI
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
    analytics
)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Electron-Shop API",
    description="Магазин електроніки, API для керування клієнтами, замовленнями, товарами та постачальниками.",
    version="1.0.0"
)

# Підключення всіх роутерів
app.include_router(customer.router, tags=["Customer"])
app.include_router(order.router, tags=["Order"])
app.include_router(orderdetail.router, tags=["Order Detail"])
app.include_router(payment.router, tags=["Payment"])
app.include_router(gift.router, tags=["Gift"])
app.include_router(courier.router, tags=["Courier"])
app.include_router(product.router, tags=["Product"])
app.include_router(supplier.router, tags=["Supplier"])
app.include_router(analytics.router, tags=["Analytics"])

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
