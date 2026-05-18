"""OTD ERP 模擬層 - 資料模型"""

from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Boolean, Text, Enum as SAEnum, create_engine
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker
import enum


DATABASE_URL = "sqlite:///./otd_erp.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


# ── Enums ──────────────────────────────────────────────────────────────────

class POStatus(str, enum.Enum):
    PENDING = "pending"
    CONVERTED = "converted"
    CANCELLED = "cancelled"


class SOStatus(str, enum.Enum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    PARTIAL = "partial"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ShippingStatus(str, enum.Enum):
    PENDING = "pending"
    PACKING = "packing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"


class InvoiceStatus(str, enum.Enum):
    DRAFT = "draft"
    ISSUED = "issued"
    PAID = "paid"


class LogisticsStatus(str, enum.Enum):
    BOOKED = "booked"
    IN_TRANSIT = "in_transit"
    ARRIVED = "arrived"
    DELIVERED = "delivered"


class ATPResult(str, enum.Enum):
    ON_TIME = "on_time"
    DELAYED = "delayed"
    INSUFFICIENT = "insufficient"


# ── Models ─────────────────────────────────────────────────────────────────

class Item(Base):
    __tablename__ = "items"

    item_code = Column(String(50), primary_key=True)
    description = Column(String(200), nullable=False)
    unit = Column(String(10), nullable=False, default="PC")
    category = Column(String(50), default="general")
    lead_time_days = Column(Integer, default=7)
    safety_stock = Column(Integer, default=0)
    daily_capacity = Column(Integer, default=1000)  # 每日最大產能
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # relationships
    so_lines = relationship("SOLine", back_populates="item")
    po_lines = relationship("POLine", back_populates="item")


class Customer(Base):
    __tablename__ = "customers"

    customer_id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    terms = Column(String(50), default="Net30")
    contact_email = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # relationships
    purchase_orders = relationship("PurchaseOrder", back_populates="customer")
    sales_orders = relationship("SalesOrder", back_populates="customer")


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    po_id = Column(String(50), primary_key=True)
    customer_id = Column(String(50), ForeignKey("customers.customer_id"), nullable=False)
    po_date = Column(DateTime, default=datetime.utcnow)
    status = Column(SAEnum(POStatus), default=POStatus.PENDING)
    remarks = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # relationships
    customer = relationship("Customer", back_populates="purchase_orders")
    lines = relationship("POLine", back_populates="po", cascade="all, delete-orphan")
    so = relationship("SalesOrder", back_populates="po", uselist=False)


class POLine(Base):
    __tablename__ = "po_lines"

    line_id = Column(Integer, primary_key=True, autoincrement=True)
    po_id = Column(String(50), ForeignKey("purchase_orders.po_id"), nullable=False)
    item_code = Column(String(50), ForeignKey("items.item_code"), nullable=False)
    qty = Column(Integer, nullable=False)
    unit_price = Column(Float, default=0.0)
    delivery_date = Column(DateTime)
    line_no = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # relationships
    po = relationship("PurchaseOrder", back_populates="lines")
    item = relationship("Item", back_populates="po_lines")


class SalesOrder(Base):
    __tablename__ = "sales_orders"

    so_id = Column(String(50), primary_key=True)
    po_id = Column(String(50), ForeignKey("purchase_orders.po_id"), nullable=True)
    customer_id = Column(String(50), ForeignKey("customers.customer_id"), nullable=False)
    so_date = Column(DateTime, default=datetime.utcnow)
    status = Column(SAEnum(SOStatus), default=SOStatus.DRAFT)
    remarks = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # relationships
    po = relationship("PurchaseOrder", back_populates="so")
    customer = relationship("Customer", back_populates="sales_orders")
    lines = relationship("SOLine", back_populates="so", cascade="all, delete-orphan")
    shippings = relationship("Shipping", back_populates="so")
    invoices = relationship("Invoice", back_populates="so")


class SOLine(Base):
    __tablename__ = "so_lines"

    line_id = Column(Integer, primary_key=True, autoincrement=True)
    so_id = Column(String(50), ForeignKey("sales_orders.so_id"), nullable=False)
    item_code = Column(String(50), ForeignKey("items.item_code"), nullable=False)
    qty = Column(Integer, nullable=False)
    unit_price = Column(Float, default=0.0)
    delivery_date = Column(DateTime)
    delivery_location = Column(String(200))
    line_no = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # relationships
    so = relationship("SalesOrder", back_populates="lines")
    item = relationship("Item", back_populates="so_lines")


class ATPCheck(Base):
    __tablename__ = "atp_checks"

    check_id = Column(String(50), primary_key=True)
    item_code = Column(String(50), nullable=False)
    qty = Column(Integer, nullable=False)
    request_date = Column(DateTime, nullable=False)
    available_date = Column(DateTime)
    available_qty = Column(Integer)
    result = Column(SAEnum(ATPResult), nullable=False)
    remarks = Column(Text)
    checked_at = Column(DateTime, default=datetime.utcnow)


class CTPCheck(Base):
    __tablename__ = "ctp_checks"

    check_id = Column(String(50), primary_key=True)
    item_code = Column(String(50), nullable=False)
    qty = Column(Integer, nullable=False)
    request_date = Column(DateTime, nullable=False)
    available_date = Column(DateTime)
    available_qty = Column(Integer)
    result = Column(SAEnum(ATPResult), nullable=False)
    batch_recommended = Column(Integer, default=0)
    remarks = Column(Text)
    checked_at = Column(DateTime, default=datetime.utcnow)


class Shipping(Base):
    __tablename__ = "shippings"

    shipping_id = Column(String(50), primary_key=True)
    so_id = Column(String(50), ForeignKey("sales_orders.so_id"), nullable=False)
    status = Column(SAEnum(ShippingStatus), default=ShippingStatus.PENDING)
    pallet_count = Column(Integer, default=0)
    container_type = Column(String(50))
    customs_date = Column(DateTime)          # 結關日
    tracking_no = Column(String(50), unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # relationships
    so = relationship("SalesOrder", back_populates="shippings")
    invoices = relationship("Invoice", back_populates="shipping")
    logistics = relationship("Logistics", back_populates="shipping", uselist=False)


class Invoice(Base):
    __tablename__ = "invoices"

    invoice_id = Column(String(50), primary_key=True)
    shipping_id = Column(String(50), ForeignKey("shippings.shipping_id"), nullable=True)
    so_id = Column(String(50), ForeignKey("sales_orders.so_id"), nullable=False)
    amount = Column(Float, nullable=False, default=0.0)
    issue_date = Column(DateTime)
    status = Column(SAEnum(InvoiceStatus), default=InvoiceStatus.DRAFT)
    created_at = Column(DateTime, default=datetime.utcnow)

    # relationships
    shipping = relationship("Shipping", back_populates="invoices")
    so = relationship("SalesOrder", back_populates="invoices")


class Logistics(Base):
    __tablename__ = "logistics"

    tracking_no = Column(String(50), primary_key=True)
    shipping_id = Column(String(50), ForeignKey("shippings.shipping_id"), nullable=False)
    status = Column(SAEnum(LogisticsStatus), default=LogisticsStatus.BOOKED)
    carrier = Column(String(100))
    eta = Column(DateTime)
    actual_arrival = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # relationships
    shipping = relationship("Shipping", back_populates="logistics")
