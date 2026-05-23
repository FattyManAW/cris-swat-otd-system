"""OTD ERP 模擬層 - 資料模型 (v2.0 — Shipping/Invoice/Logistics Deepened)"""

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker

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
    """v2.0: 7 狀態（pending→packing→packed→shipped→delivered + partial variants）"""
    PENDING = "pending"
    PACKING = "packing"
    PACKED = "packed"
    PARTIAL_PACKED = "partial_packed"
    SHIPPED = "shipped"
    PARTIAL_DELIVERY = "partial_delivery"
    DELIVERED = "delivered"


class InvoiceStatus(str, enum.Enum):
    """v2.0: 9 狀態（draft→issued→sent→paid→overdue→dunning→reconciled→void→credit_note）"""
    DRAFT = "draft"
    ISSUED = "issued"
    SENT = "sent"
    PAID = "paid"
    OVERDUE = "overdue"
    DUNNING = "dunning"
    RECONCILED = "reconciled"
    VOID = "void"
    CREDIT_NOTE = "credit_note"


class LogisticsStatus(str, enum.Enum):
    """v2.0: 11 狀態（booked→customs→in_transit→arrived→delivered + 異常路徑）"""
    BOOKED = "booked"
    CUSTOMS = "customs"
    CUSTOMS_HOLD = "customs_hold"
    CLEARED_RETRY = "cleared_retry"
    IN_TRANSIT = "in_transit"
    ARRIVED = "arrived"
    PARTIAL_DELIVERY = "partial_delivery"
    DELIVERED = "delivered"
    FAILED = "failed"
    REROUTE = "reroute"


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


# ════════════════════════════════════════════════════════════════════════════
# v2.0 — Shipping / Invoice / Logistics Deepened
# ════════════════════════════════════════════════════════════════════════════

class Shipping(Base):
    """v2.0: +9 新欄位（carrier→ship_to_address）+ 3 relationships"""
    __tablename__ = "shippings"

    shipping_id = Column(String(50), primary_key=True)
    so_id = Column(String(50), ForeignKey("sales_orders.so_id"), nullable=False)
    status = Column(SAEnum(ShippingStatus), default=ShippingStatus.PENDING)
    pallet_count = Column(Integer, default=0)
    container_type = Column(String(50))
    customs_date = Column(DateTime)          # 結關日
    tracking_no = Column(String(50), unique=True)

    # ── v2.0 新增 ──────────────────────────────────────────────────
    carrier = Column(String(100))            # 實際出貨承運商（複寫自 Logistics）
    actual_ship_date = Column(DateTime)      # 實際出貨日
    actual_arrive_date = Column(DateTime)    # 實際到貨日
    partial_delivery = Column(Boolean, default=False)  # 是否為分批到貨
    remaining_qty = Column(Integer, default=0)        # 未送達數量
    delivery_proof_url = Column(Text)        # 簽收證明 URL
    is_delivery_signed = Column(Boolean, default=False)  # 是否已簽收
    remarks = Column(Text)                   # 出貨備註
    ship_from_location = Column(String(200)) # 出貨地點
    ship_to_address = Column(Text)           # 送達地址（同步自 SO）

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # relationships
    so = relationship("SalesOrder", back_populates="shippings")
    invoices = relationship("Invoice", back_populates="shipping")
    logistics = relationship("Logistics", back_populates="shipping", uselist=False)
    pack_details = relationship("ShippingPackDetail", back_populates="shipping", cascade="all, delete-orphan")
    attachments = relationship("ShippingAttachment", back_populates="shipping", cascade="all, delete-orphan")


class ShippingPackDetail(Base):
    """v2.0 新表: 棧板級包裝明細"""
    __tablename__ = "shipping_pack_details"

    detail_id = Column(Integer, primary_key=True, autoincrement=True)
    shipping_id = Column(String(50), ForeignKey("shippings.shipping_id"), nullable=False)
    pallet_no = Column(Integer, nullable=False)
    line_no = Column(Integer, nullable=False)
    item_code = Column(String(50), nullable=False)
    qty_packed = Column(Integer, default=0)
    qty_shipped = Column(Integer, default=0)
    weight_kg = Column(Float)
    dimensions_cm = Column(String(50))
    remarks = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # relationship
    shipping = relationship("Shipping", back_populates="pack_details")


class ShippingAttachment(Base):
    """v2.0 新表: 出貨附件（簽單/照片/文件）"""
    __tablename__ = "shipping_attachments"

    attachment_id = Column(String(50), primary_key=True)
    shipping_id = Column(String(50), ForeignKey("shippings.shipping_id"), nullable=False)
    type = Column(String(20), nullable=False)  # pod/photo/doc/other
    filename = Column(String(200), nullable=False)
    url = Column(Text)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    uploaded_by = Column(String(50))          # agent id

    # relationship
    shipping = relationship("Shipping", back_populates="attachments")


class Invoice(Base):
    """v2.0: +10 新欄位 + relationship to InvoiceLine"""
    __tablename__ = "invoices"

    invoice_id = Column(String(50), primary_key=True)
    shipping_id = Column(String(50), ForeignKey("shippings.shipping_id"), nullable=True)
    so_id = Column(String(50), ForeignKey("sales_orders.so_id"), nullable=False)
    amount = Column(Float, nullable=False, default=0.0)
    issue_date = Column(DateTime)
    status = Column(SAEnum(InvoiceStatus), default=InvoiceStatus.DRAFT)

    # ── v2.0 新增 ──────────────────────────────────────────────────
    invoice_no = Column(String(50), unique=True)    # 發票號碼（商業實際號碼）
    invoice_type = Column(String(20), default="tax") # tax/proforma/credit_note
    due_date = Column(DateTime)                     # 付款到期日
    grace_days = Column(Integer, default=0)          # 寬限期（天）
    tax_amount = Column(Float, default=0.0)          # 稅額
    net_amount = Column(Float)                       # 未稅金額
    payment_date = Column(DateTime)                  # 實際付款日
    payment_ref = Column(String(100))                # 付款參考號
    currency = Column(String(3), default="USD")      # 幣別
    void_reason = Column(Text)                       # 作廢原因
    credit_note_for = Column(String(50))             # 關聯折讓單號

    created_at = Column(DateTime, default=datetime.utcnow)

    # relationships
    shipping = relationship("Shipping", back_populates="invoices")
    so = relationship("SalesOrder", back_populates="invoices")
    lines = relationship("InvoiceLine", back_populates="invoice", cascade="all, delete-orphan")


class InvoiceLine(Base):
    """v2.0 新表: 發票品項明細"""
    __tablename__ = "invoice_lines"

    line_id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_id = Column(String(50), ForeignKey("invoices.invoice_id"), nullable=False)
    line_no = Column(Integer, nullable=False)
    item_code = Column(String(50))
    description = Column(String(200))
    qty = Column(Float)
    unit_price = Column(Float)
    amount = Column(Float)                     # qty × unit_price
    so_line_id = Column(Integer)               # 關聯 SO 單身
    created_at = Column(DateTime, default=datetime.utcnow)

    # relationship
    invoice = relationship("Invoice", back_populates="lines")


class Logistics(Base):
    """v2.0: +11 新欄位 + relationship to LogisticsEvent"""
    __tablename__ = "logistics"

    tracking_no = Column(String(50), primary_key=True)
    shipping_id = Column(String(50), ForeignKey("shippings.shipping_id"), nullable=False)
    status = Column(SAEnum(LogisticsStatus), default=LogisticsStatus.BOOKED)
    carrier = Column(String(100))
    eta = Column(DateTime)
    actual_arrival = Column(DateTime)

    # ── v2.0 新增 ──────────────────────────────────────────────────
    origin_port = Column(String(50))             # 起運港/機場
    dest_port = Column(String(50))               # 目的港/機場
    vessel_flight = Column(String(100))          # 船名/航班
    bl_number = Column(String(50))               # 提單號 (B/L)
    booking_ref = Column(String(100))            # 貨運預約號
    departure_date = Column(DateTime)            # 實際開船日
    customs_status = Column(String(50))          # 通關狀態 cleared/held/partial
    delivery_signed_by = Column(String(100))     # 簽收人
    delivery_note = Column(Text)                 # 送達備註
    multi_leg = Column(Boolean, default=False)    # 是否多段運輸
    is_final_delivery = Column(Boolean, default=False)  # 是否最終送達

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # relationships
    shipping = relationship("Shipping", back_populates="logistics")
    events = relationship("LogisticsEvent", back_populates="logistics", cascade="all, delete-orphan")


class LogisticsEvent(Base):
    """v2.0 新表: 物流事件軌跡"""
    __tablename__ = "logistics_events"

    event_id = Column(String(50), primary_key=True)
    tracking_no = Column(String(50), ForeignKey("logistics.tracking_no"), nullable=False)
    status = Column(String(50), nullable=False)
    location = Column(String(200))
    note = Column(Text)
    event_at = Column(DateTime, nullable=False)
    created_by = Column(String(50))              # agent id
    created_at = Column(DateTime, default=datetime.utcnow)

    # relationship
    logistics = relationship("Logistics", back_populates="events")
