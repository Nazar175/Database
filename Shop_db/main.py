from fastapi import FastAPI, Depends
from sqlalchemy import inspect, text
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
from routers.customer import auth_router, get_current_user

Base.metadata.create_all(bind=engine)


def _ensure_column(table_name: str, column_name: str, ddl: str) -> None:
    inspector = inspect(engine)
    if not inspector.has_table(table_name):
        return

    columns = {column["name"] for column in inspector.get_columns(table_name)}
    if column_name in columns:
        return

    with engine.begin() as connection:
        connection.execute(text(ddl))


_ensure_column(
    table_name="Customer",
    column_name="password_hash",
    ddl="ALTER TABLE Customer ADD COLUMN password_hash VARCHAR(128) NULL",
)
_ensure_column(
    table_name="Customer",
    column_name="Role",
    ddl="ALTER TABLE Customer ADD COLUMN Role VARCHAR(20) NOT NULL DEFAULT 'user'",
)
_ensure_column(
    table_name="Supplier",
    column_name="OwnerCustomerID",
    ddl="ALTER TABLE Supplier ADD COLUMN OwnerCustomerID INT NULL",
)
_ensure_column(
    table_name="Product",
    column_name="OwnerCustomerID",
    ddl="ALTER TABLE Product ADD COLUMN OwnerCustomerID INT NULL",
)

app = FastAPI(
    title="Electron-Shop API",
    description="Магазин електроніки, API для керування клієнтами, замовленнями, товарами та постачальниками.",
    version="1.0.0"
)

app.include_router(auth_router, tags=["Auth"])

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
