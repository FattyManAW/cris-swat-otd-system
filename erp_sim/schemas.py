"""OTD ERP 模擬層 - Pydantic Schemas"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from models import (
    POStatus, SOStatus, ShippingStatus, InvoiceStatus, LogisticsStatus, ATPResult,
    Item, Customer, PurchaseOrder, POLine, SalesOrder, SOLine, ATPCheck, CTPCheck,
    Shipping, Invoice, Logistics
)


# ── Item ────────────────────────────────────────────────────────────────────

class ItemCreate(BaseModel):
    item_code: str
    description: str
    unit: str = "PC"
    category: str = "general"
    lead_time_days: int = 7
    safety_stock: int = 0
    daily_capacity: int = 1000


class ItemRead(BaseModel):
    item_code: str
    description: str
    unit: str
    category: str
    lead_time_days: int
    safety_stock: int
    daily_capacity: int
    is_active: bool

    class Config:
        from_attributes = True


# ── Customer ────────────────────────────────────────────────────────────────

class CustomerCreate(BaseModel):
    customer_id: str
    name: str
    terms: str = "Net30"
    contact_email: Optional[str] = None


class CustomerRead(BaseModel):
    customer_id: str
    name: str
    terms: str
    contact_email: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True


# ── PO ──────────────────────────────────────────────────────────────────────

class POLineCreate(BaseModel):
    item_code: str
    qty: int = Field(gt=0)
    unit_price: float = 0.0
    delivery_date: Optional[datetime] = None
    line_no: int = 1


class POCreate(BaseModel):
    po_id: str
    customer_id: str
    remarks: Optional[str] = None
    lines: list[POLineCreate] = []


class PORead(BaseModel):
    po_id: str
    customer_id: str
    po_date: datetime
    status: POStatus
    remarks: Optional[str]

    class Config:
        from_attributes = True


class POLineRead(BaseModel):
    line_id: int
    po_id: str
    item_code: str
    qty: int
    unit_price: float
    delivery_date: Optional[datetime]
    line_no: int

    class Config:
        from_attributes = True


# ── SO ──────────────────────────────────────────────────────────────────────

class SOLineCreate(BaseModel):
    item_code: str
    qty: int = Field(gt=0)
    unit_price: float = 0.0
    delivery_date: Optional[datetime] = None
    delivery_location: Optional[str] = None
    line_no: int = 1


class SOCreate(BaseModel):
    so_id: str
    po_id: Optional[str] = None
    customer_id: str
    remarks: Optional[str] = None
    lines: list[SOLineCreate] = []


class SORead(BaseModel):
    so_id: str
    po_id: Optional[str]
    customer_id: str
    so_date: datetime
    status: SOStatus
    remarks: Optional[str]

    class Config:
        from_attributes = True


class SOLineRead(BaseModel):
    line_id: int
    so_id: str
    item_code: str
    qty: int
    unit_price: float
    delivery_date: Optional[datetime]
    delivery_location: Optional[str]
    line_no: int

    class Config:
        from_attributes = True


# ── ATP / CTP ───────────────────────────────────────────────────────────────

class ATPRequest(BaseModel):
    item_code: str
    qty: int = Field(gt=0)
    request_date: datetime


class ATPResponse(BaseModel):
    check_id: str
    item_code: str
    qty: int
    request_date: datetime
    available_date: Optional[datetime]
    available_qty: Optional[int]
    result: ATPResult
    remarks: str
    checked_at: datetime


class CTPResponse(BaseModel):
    check_id: str
    item_code: str
    qty: int
    request_date: datetime
    available_date: Optional[datetime]
    available_qty: Optional[int]
    result: ATPResult
    batch_recommended: int
    remarks: str
    checked_at: datetime


# ── Shipping ────────────────────────────────────────────────────────────────

class ShippingCreate(BaseModel):
    shipping_id: str
    so_id: str
    pallet_count: int = 0
    container_type: Optional[str] = None
    customs_date: Optional[datetime] = None


class ShippingRead(BaseModel):
    shipping_id: str
    so_id: str
    status: ShippingStatus
    pallet_count: int
    container_type: Optional[str]
    customs_date: Optional[datetime]
    tracking_no: Optional[str]

    class Config:
        from_attributes = True


# ── Invoice ─────────────────────────────────────────────────────────────────

class InvoiceCreate(BaseModel):
    invoice_id: str
    shipping_id: Optional[str] = None
    so_id: str
    amount: float = Field(ge=0)


class InvoiceRead(BaseModel):
    invoice_id: str
    shipping_id: Optional[str]
    so_id: str
    amount: float
    issue_date: Optional[datetime]
    status: InvoiceStatus

    class Config:
        from_attributes = True


# ── Logistics ───────────────────────────────────────────────────────────────

class LogisticsCreate(BaseModel):
    tracking_no: str
    shipping_id: str
    carrier: Optional[str] = None
    eta: Optional[datetime] = None


class LogisticsRead(BaseModel):
    tracking_no: str
    shipping_id: str
    status: LogisticsStatus
    carrier: Optional[str]
    eta: Optional[datetime]
    actual_arrival: Optional[datetime]

    class Config:
        from_attributes = True


# ── Generic ─────────────────────────────────────────────────────────────────

class OkResponse(BaseModel):
    ok: bool = True
    message: Optional[str] = None
