import logging
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, text

from database import Base, engine
from routers import (
    analytics,
    courier,
    customer,
    gift,
    order,
    orderdetail,
    payment,
    product,
    supplier,
)
from routers.customer import auth_router, get_current_user

logger = logging.getLogger(__name__)


def _ensure_column(table_name: str, column_name: str, ddl: str) -> None:
    inspector = inspect(engine)
    if not inspector.has_table(table_name):
        return

    columns = {column["name"] for column in inspector.get_columns(table_name)}
    if column_name in columns:
        return

    with engine.begin() as connection:
        connection.execute(text(ddl))


def _migrate_shipping_address_to_order_detail() -> None:
    inspector = inspect(engine)
    if not inspector.has_table("Orders") or not inspector.has_table("OrderDetail"):
        return

    orders_columns = {column["name"] for column in inspector.get_columns("Orders")}
    details_columns = {column["name"] for column in inspector.get_columns("OrderDetail")}

    if "ShippingAddress" in orders_columns and "ShippingAddress" in details_columns:
        dialect = engine.dialect.name
        with engine.begin() as connection:
            if dialect == "mysql":
                connection.execute(
                    text(
                        """
                        UPDATE OrderDetail od
                        JOIN Orders o ON o.OrderID = od.OrderID
                        SET od.ShippingAddress = o.ShippingAddress
                        WHERE od.ShippingAddress IS NULL
                        """
                    )
                )
            else:
                connection.execute(
                    text(
                        """
                        UPDATE OrderDetail
                        SET ShippingAddress = (
                            SELECT Orders.ShippingAddress
                            FROM Orders
                            WHERE Orders.OrderID = OrderDetail.OrderID
                        )
                        WHERE ShippingAddress IS NULL
                        """
                    )
                )

    if "ShippingAddress" in orders_columns:
        try:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE Orders DROP COLUMN ShippingAddress"))
        except Exception:
            # Some engines or versions may not support DROP COLUMN directly.
            pass


def initialize_database_schema() -> None:
    Base.metadata.create_all(bind=engine)

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
        table_name="Supplier",
        column_name="Role",
        ddl="ALTER TABLE Supplier ADD COLUMN Role VARCHAR(20) NOT NULL DEFAULT 'seller'",
    )
    _ensure_column(
        table_name="Product",
        column_name="OwnerCustomerID",
        ddl="ALTER TABLE Product ADD COLUMN OwnerCustomerID INT NULL",
    )
    _ensure_column(
        table_name="Product",
        column_name="AvailableQuantity",
        ddl="ALTER TABLE Product ADD COLUMN AvailableQuantity INT NOT NULL DEFAULT 0",
    )
    _ensure_column(
        table_name="OrderDetail",
        column_name="ShippingAddress",
        ddl="ALTER TABLE OrderDetail ADD COLUMN ShippingAddress VARCHAR(200) NULL",
    )

    _migrate_shipping_address_to_order_detail()

app = FastAPI(
    title="Electron-Shop API",
    description="Магазин електроніки, API для керування клієнтами, замовленнями, товарами та постачальниками.",
    version="1.0.0",
)

website_dir = Path(__file__).resolve().parent / "Website"

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


@app.on_event("startup")
def on_startup() -> None:
    try:
        initialize_database_schema()
    except Exception as exc:
        logger.warning("Database schema initialization skipped: %s", exc)


@app.get("/")
def root():
    return {
        "message": "Welcome to Electron-Shop API",
        "docs": "/docs",
        "redoc": "/redoc",
        "website": "/site/main.html",
    }


@app.get("/site", include_in_schema=False)
def website_root():
    return RedirectResponse(url="/site/main.html")


app.mount("/site", StaticFiles(directory=website_dir, html=True), name="website")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
