from sqlalchemy import Column, Integer, String, DECIMAL, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
import enum


class OrderStatus(str, enum.Enum):
    Pending = "Pending"
    Shipped = "Shipped"
    Completed = "Completed"
    Cancelled = "Cancelled"


class PaymentStatus(str, enum.Enum):
    Pending = "Pending"
    Paid = "Paid"
    Refunded = "Refunded"


class GiftType(str, enum.Enum):
    Certificate = "Certificate"
    Gift = "Gift"


class GiftUnit(str, enum.Enum):
    USD = "USD"
    Percent = "%"


class Customer(Base):
    __tablename__ = "Customer"

    CustomerID = Column(Integer, primary_key=True, index=True)
    Name = Column(String(100), nullable=False)
    Email = Column(String(100), unique=True, nullable=False)
    Phone = Column(String(20))
    Country = Column(String(50))

    orders = relationship("Orders", back_populates="customer")


class Supplier(Base):
    __tablename__ = "Supplier"

    SupplierID = Column(Integer, primary_key=True, index=True)
    SupplierName = Column(String(100), nullable=False)
    Address = Column(String(200))
    Phone = Column(String(20))
    DeliveryDate = Column(DateTime)

    products = relationship("Product", back_populates="supplier")


class Product(Base):
    __tablename__ = "Product"

    ProductID = Column(Integer, primary_key=True, index=True)
    ProductName = Column(String(100), nullable=False)
    Price = Column(DECIMAL(10, 2), nullable=False)
    SupplierID = Column(Integer, ForeignKey("Supplier.SupplierID"))

    supplier = relationship("Supplier", back_populates="products")
    order_details = relationship("OrderDetail", back_populates="product")


class Orders(Base):
    __tablename__ = "Orders"

    OrderID = Column(Integer, primary_key=True, index=True)
    OrderDate = Column(DateTime, nullable=False)
    CustomerID = Column(Integer, ForeignKey("Customer.CustomerID"))
    ShippingAddress = Column(String(200), nullable=False)
    Status = Column(Enum(OrderStatus), default=OrderStatus.Pending)

    customer = relationship("Customer", back_populates="orders")
    details = relationship("OrderDetail", back_populates="order")
    courier = relationship("Courier", back_populates="order", uselist=False)
    payment = relationship("Payment", back_populates="order", uselist=False)


class OrderDetail(Base):
    __tablename__ = "OrderDetail"

    OrderDetailID = Column(Integer, primary_key=True, index=True)
    OrderID = Column(Integer, ForeignKey("Orders.OrderID"), nullable=False)
    ProductID = Column(Integer, ForeignKey("Product.ProductID"), nullable=False)
    Quantity = Column(Integer, nullable=False, default=1)

    order = relationship("Orders", back_populates="details")
    product = relationship("Product", back_populates="order_details")


class Courier(Base):
    __tablename__ = "Courier"

    CourierID = Column(Integer, primary_key=True, index=True)
    Name = Column(String(100), nullable=False)
    Country = Column(String(50))
    Price = Column(DECIMAL(10, 2))
    OrderID = Column(Integer, ForeignKey("Orders.OrderID"), unique=True)

    order = relationship("Orders", back_populates="courier")


class Payment(Base):
    __tablename__ = "Payment"

    PaymentID = Column(Integer, primary_key=True, index=True)
    OrderID = Column(Integer, ForeignKey("Orders.OrderID"), unique=True)
    Status = Column(Enum(PaymentStatus), default=PaymentStatus.Pending)
    Amount = Column(DECIMAL(10, 2), nullable=False)
    PaymentDate = Column(DateTime)

    order = relationship("Orders", back_populates="payment")
    gifts = relationship("Gifts", back_populates="payment")


class Gifts(Base):
    __tablename__ = "Gifts"

    GiftID = Column(Integer, primary_key=True, index=True)
    Amount = Column(DECIMAL(10, 2))
    ExparesDate = Column(DateTime)
    Type = Column(Enum(GiftType))
    Unit = Column(Enum(GiftUnit), nullable=False)
    PaymentID = Column(Integer, ForeignKey("Payment.PaymentID"))

    payment = relationship("Payment", back_populates="gifts")
