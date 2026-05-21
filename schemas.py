"""OTD ERP 模擬層 - Pydantic Schemas (v2.0 — Shipping/Invoice/Logistics Deepened)"""

from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field
from models import (
    POStatus, SOStatus, ShippingStatus, InvoiceStatus, LogisticsStatus, ATPResult,
    ShippingPackDetail, ShippingAttachment, InvoiceLine, LogisticsEvent,
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


# ════════════════════════════════════════════════════════════════════════════
# v2.0 — Shipping Deepened
# ════════════════════════════════════════════════════════════════════════════

class ShippingCreate(BaseModel):
    shipping_id: str
    so_id: str
    pallet_count: int = 0
    container_type: Optional[str] = None
    customs_date: Optional[datetime] = None
    # v2.0
    ship_from_location: Optional[str] = None
    ship_to_address: Optional[str] = None


class ShippingRead(BaseModel):
    shipping_id: str
    so_id: str
    status: ShippingStatus
    pallet_count: int
    container_type: Optional[str]
    customs_date: Optional[datetime]
    tracking_no: Optional[str]
    # v2.0
    carrier: Optional[str] = None
    actual_ship_date: Optional[datetime] = None
    actual_arrive_date: Optional[datetime] = None
    partial_delivery: bool = False
    remaining_qty: int = 0
    delivery_proof_url: Optional[str] = None
    is_delivery_signed: bool = False
    remarks: Optional[str] = None
    ship_from_location: Optional[str] = None
    ship_to_address: Optional[str] = None

    class Config:
        from_attributes = True


# ── Shipping Pack Detail ────────────────────────────────────────────────────

class ShippingPackDetailCreate(BaseModel):
    pallet_no: int
    line_no: int
    item_code: str
    qty_packed: int = Field(ge=0)
    qty_shipped: int = 0
    weight_kg: Optional[float] = None
    dimensions_cm: Optional[str] = None
    remarks: Optional[str] = None


class ShippingPackDetailRead(BaseModel):
    detail_id: int
    shipping_id: str
    pallet_no: int
    line_no: int
    item_code: str
    qty_packed: int
    qty_shipped: int
    weight_kg: Optional[float]
    dimensions_cm: Optional[str]
    remarks: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Shipping Pack Partial ───────────────────────────────────────────────────

class ShippingPackPartialRequest(BaseModel):
    """部分包裝：指定品項與數量"""
    pallet_no: int = 1
    line_no: int
    item_code: str
    qty_packed: int = Field(gt=0)
    weight_kg: Optional[float] = None
    dimensions_cm: Optional[str] = None
    remarks: Optional[str] = None


# ── Shipping Attachment ─────────────────────────────────────────────────────

class ShippingAttachmentCreate(BaseModel):
    attachment_id: str
    type: Literal["pod", "photo", "doc", "other"]
    filename: str
    url: Optional[str] = None
    uploaded_by: Optional[str] = None


class ShippingAttachmentRead(BaseModel):
    attachment_id: str
    shipping_id: str
    type: str
    filename: str
    url: Optional[str]
    uploaded_at: datetime
    uploaded_by: Optional[str]

    class Config:
        from_attributes = True


# ── Shipping Partial Ship/Deliver ───────────────────────────────────────────

class PartialShipRequest(BaseModel):
    """部分出貨"""
    remaining_qty: int = Field(ge=0)
    remarks: Optional[str] = None


class PartialDeliverRequest(BaseModel):
    """部分到貨"""
    delivered_qty: int = Field(ge=0)
    remaining_qty: int = Field(ge=0)
    delivery_proof_url: Optional[str] = None
    is_delivery_signed: bool = False
    remarks: Optional[str] = None


# ── Shipping Deliver (簽收) ─────────────────────────────────────────────────

class ShippingDeliverRequest(BaseModel):
    delivery_proof_url: Optional[str] = None
    signed_by: Optional[str] = None
    remarks: Optional[str] = None


# ════════════════════════════════════════════════════════════════════════════
# v2.0 — Invoice Deepened
# ════════════════════════════════════════════════════════════════════════════

class InvoiceCreate(BaseModel):
    invoice_id: str
    shipping_id: Optional[str] = None
    so_id: str
    amount: float = Field(ge=0)
    # v2.0
    invoice_type: str = "tax"                # tax / proforma / credit_note
    tax_amount: float = 0.0
    net_amount: Optional[float] = None       # 預設 = amount - tax_amount
    currency: str = "USD"
    due_date: Optional[datetime] = None
    grace_days: int = 14
    invoice_no: Optional[str] = None
    lines: list["InvoiceLineCreate"] = []


class InvoiceRead(BaseModel):
    invoice_id: str
    shipping_id: Optional[str]
    so_id: str
    amount: float
    issue_date: Optional[datetime]
    status: InvoiceStatus
    # v2.0
    invoice_no: Optional[str] = None
    invoice_type: str = "tax"
    due_date: Optional[datetime] = None
    grace_days: int = 0
    tax_amount: float = 0.0
    net_amount: Optional[float] = None
    payment_date: Optional[datetime] = None
    payment_ref: Optional[str] = None
    currency: str = "USD"
    void_reason: Optional[str] = None
    credit_note_for: Optional[str] = None

    class Config:
        from_attributes = True


# ── Invoice Line ────────────────────────────────────────────────────────────

class InvoiceLineCreate(BaseModel):
    line_no: int
    item_code: str
    description: str
    qty: float = Field(gt=0)
    unit_price: float = Field(ge=0)
    amount: Optional[float] = None  # auto-calc qty × unit_price
    so_line_id: Optional[int] = None


class InvoiceLineRead(BaseModel):
    line_id: int
    invoice_id: str
    line_no: int
    item_code: str
    description: str
    qty: float
    unit_price: float
    amount: float
    so_line_id: Optional[int]

    class Config:
        from_attributes = True


# ── Invoice Issue / Payment / Void ──────────────────────────────────────────

class InvoiceIssueRequest(BaseModel):
    invoice_no: Optional[str] = None
    due_date: Optional[datetime] = None


class InvoicePaymentRequest(BaseModel):
    payment_ref: Optional[str] = None
    payment_date: Optional[datetime] = None


class InvoiceVoidRequest(BaseModel):
    void_reason: str


class InvoiceCreditNoteRequest(BaseModel):
    credit_note_for: str  # 原 invoice_id
    amount: float = Field(ge=0)
    reason: Optional[str] = None


# ════════════════════════════════════════════════════════════════════════════
# v2.0 — Logistics Deepened
# ════════════════════════════════════════════════════════════════════════════

class LogisticsCreate(BaseModel):
    tracking_no: str
    shipping_id: str
    carrier: Optional[str] = None
    eta: Optional[datetime] = None
    # v2.0
    origin_port: Optional[str] = None
    dest_port: Optional[str] = None
    vessel_flight: Optional[str] = None
    bl_number: Optional[str] = None
    booking_ref: Optional[str] = None


class LogisticsRead(BaseModel):
    tracking_no: str
    shipping_id: str
    status: LogisticsStatus
    carrier: Optional[str]
    eta: Optional[datetime]
    actual_arrival: Optional[datetime]
    # v2.0
    origin_port: Optional[str] = None
    dest_port: Optional[str] = None
    vessel_flight: Optional[str] = None
    bl_number: Optional[str] = None
    booking_ref: Optional[str] = None
    departure_date: Optional[datetime] = None
    customs_status: Optional[str] = None
    delivery_signed_by: Optional[str] = None
    delivery_note: Optional[str] = None
    multi_leg: bool = False
    is_final_delivery: bool = False

    class Config:
        from_attributes = True


# ── Logistics Status Transition ─────────────────────────────────────────────

class LogisticsDepartRequest(BaseModel):
    departure_date: Optional[datetime] = None
    vessel_flight: Optional[str] = None
    origin_port: Optional[str] = None
    note: Optional[str] = None


class LogisticsCustomsRequest(BaseModel):
    customs_status: str = "cleared"   # cleared / held
    bl_number: Optional[str] = None
    dest_port: Optional[str] = None
    note: Optional[str] = None


class LogisticsCustomsHoldRequest(BaseModel):
    reason: str
    note: Optional[str] = None


class LogisticsCustomsClearRequest(BaseModel):
    note: Optional[str] = None


class LogisticsArriveRequest(BaseModel):
    actual_arrival: Optional[datetime] = None
    delivery_note: Optional[str] = None


class LogisticsPartialArriveRequest(BaseModel):
    delivered_qty: int = Field(gt=0)
    remaining_qty: int = Field(ge=0)
    note: Optional[str] = None


class LogisticsDeliverSignRequest(BaseModel):
    signed_by: str
    delivery_note: Optional[str] = None
    is_final: bool = True


class LogisticsFailedRequest(BaseModel):
    reason: str
    note: Optional[str] = None


class LogisticsRerouteRequest(BaseModel):
    new_carrier: Optional[str] = None
    new_eta: Optional[datetime] = None
    note: Optional[str] = None


# ── Logistics Event ─────────────────────────────────────────────────────────

class LogisticsEventCreate(BaseModel):
    event_id: str
    status: str
    location: Optional[str] = None
    note: Optional[str] = None
    event_at: Optional[datetime] = None
    created_by: Optional[str] = None


class LogisticsEventRead(BaseModel):
    event_id: str
    tracking_no: str
    status: str
    location: Optional[str]
    note: Optional[str]
    event_at: datetime
    created_by: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ════════════════════════════════════════════════════════════════════════════
# Generic
# ════════════════════════════════════════════════════════════════════════════

class OkResponse(BaseModel):
    ok: bool = True
    message: Optional[str] = None


class OverdueFilter(BaseModel):
    """GET /invoice/overdue query params"""
    days_overdue: int = 1
    include_dunning: bool = True


class ActiveLogisticsFilter(BaseModel):
    """GET /logistics/active query params"""
    carrier: Optional[str] = None
    limit: int = 50