"""OTD ERP 模擬層 - FastAPI 主程式 (v2.0)

完整 OTD (On-Time Delivery) 流程的 ERP 系統模擬介面，供各 Agent 統一讀寫。

模組覆蓋：
- Item / Customer / PO / SO（基礎資料 + 訂單）
- ATP / CTP（交期試算）
- Shipping（出貨：pack_detail + partial + deliver + attachments）
- Invoice（發票：draft→issued→sent→paid→overdue→void→credit_note）
- Logistics（物流：booked→depart→customs→arrive→deliver_sign + events trail）

執行：python3 -m uvicorn main:app --host 0.0.0.0 --port 8001
API 文件：http://localhost:8001/docs

v2.0 (2026-05-21): Shipping/Invoice/Logistics 深化 — 28 新端點，3 status enums 擴充，4 新表
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query

from models import (
    ATPCheck,
    ATPResult,
    Base,
    CTPCheck,
    Customer,
    Invoice,
    InvoiceLine,
    InvoiceStatus,
    Item,
    Logistics,
    LogisticsEvent,
    LogisticsStatus,
    POLine,
    POStatus,
    PurchaseOrder,
    SalesOrder,
    SessionLocal,
    Shipping,
    ShippingAttachment,
    ShippingPackDetail,
    ShippingStatus,
    SOLine,
    SOStatus,
    engine,
)
from schemas import (
    ATPRequest,
    ATPResponse,
    CTPResponse,
    CustomerCreate,
    CustomerRead,
    InvoiceCreate,
    InvoiceCreditNoteRequest,
    InvoiceIssueRequest,
    InvoiceLineRead,
    InvoicePaymentRequest,
    InvoiceRead,
    InvoiceVoidRequest,
    ItemCreate,
    ItemRead,
    LogisticsArriveRequest,
    LogisticsCreate,
    LogisticsCustomsClearRequest,
    LogisticsCustomsHoldRequest,
    LogisticsCustomsRequest,
    LogisticsDeliverSignRequest,
    LogisticsDepartRequest,
    LogisticsEventCreate,
    LogisticsEventRead,
    LogisticsFailedRequest,
    LogisticsPartialArriveRequest,
    LogisticsRead,
    LogisticsRerouteRequest,
    OkResponse,
    PartialDeliverRequest,
    PartialShipRequest,
    POCreate,
    POLineRead,
    PORead,
    ShippingAttachmentCreate,
    ShippingAttachmentRead,
    ShippingCreate,
    ShippingDeliverRequest,
    ShippingPackDetailCreate,
    ShippingPackDetailRead,
    ShippingPackPartialRequest,
    ShippingRead,
    SOCreate,
    SOLineRead,
    SORead,
)

# ── Init ────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="OTD ERP 模擬層",
    description="OTD 流程之 ERP 系統模擬介面，供各 Agent 統一讀寫",
    version="1.0.0",
)

Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def gen_id(prefix: str) -> str:
    return f"{prefix}-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"


# ════════════════════════════════════════════════════════════════════════════
# 1. Item（料號）
# ════════════════════════════════════════════════════════════════════════════

@app.get("/api/v1/items", response_model=list[ItemRead])
def list_items(db=Depends(get_db)):
    return db.query(Item).filter(Item.is_active).all()


@app.get("/api/v1/items/{item_code}", response_model=ItemRead)
def get_item(item_code: str, db=Depends(get_db)):
    item = db.query(Item).filter(Item.item_code == item_code, Item.is_active).first()
    if not item:
        raise HTTPException(404, f"料號 {item_code} 不存在")
    return item


@app.post("/api/v1/items", response_model=ItemRead)
def create_item(data: ItemCreate, db=Depends(get_db)):
    if db.query(Item).filter(Item.item_code == data.item_code).first():
        raise HTTPException(400, f"料號 {data.item_code} 已存在")
    item = Item(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


# ════════════════════════════════════════════════════════════════════════════
# 2. Customer（客戶）
# ════════════════════════════════════════════════════════════════════════════

@app.get("/api/v1/customers", response_model=list[CustomerRead])
def list_customers(db=Depends(get_db)):
    return db.query(Customer).filter(Customer.is_active).all()


@app.get("/api/v1/customers/{customer_id}", response_model=CustomerRead)
def get_customer(customer_id: str, db=Depends(get_db)):
    c = db.query(Customer).filter(Customer.customer_id == customer_id, Customer.is_active).first()
    if not c:
        raise HTTPException(404, f"客戶 {customer_id} 不存在")
    return c


@app.post("/api/v1/customers", response_model=CustomerRead)
def create_customer(data: CustomerCreate, db=Depends(get_db)):
    if db.query(Customer).filter(Customer.customer_id == data.customer_id).first():
        raise HTTPException(400, f"客戶 {data.customer_id} 已存在")
    c = Customer(**data.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


# ════════════════════════════════════════════════════════════════════════════
# 3. PO（採購單）
# ════════════════════════════════════════════════════════════════════════════

@app.get("/api/v1/po", response_model=list[PORead])
def list_pos(db=Depends(get_db)):
    return db.query(PurchaseOrder).all()


@app.get("/api/v1/po/{po_id}", response_model=PORead)
def get_po(po_id: str, db=Depends(get_db)):
    po = db.query(PurchaseOrder).filter(PurchaseOrder.po_id == po_id).first()
    if not po:
        raise HTTPException(404, f"PO {po_id} 不存在")
    return po


@app.get("/api/v1/po/{po_id}/lines", response_model=list[POLineRead])
def get_po_lines(po_id: str, db=Depends(get_db)):
    po = db.query(PurchaseOrder).filter(PurchaseOrder.po_id == po_id).first()
    if not po:
        raise HTTPException(404, f"PO {po_id} 不存在")
    return po.lines


@app.post("/api/v1/po", response_model=PORead)
def create_po(data: POCreate, db=Depends(get_db)):
    if db.query(PurchaseOrder).filter(PurchaseOrder.po_id == data.po_id).first():
        raise HTTPException(400, f"PO {data.po_id} 已存在")

    if not db.query(Customer).filter(Customer.customer_id == data.customer_id).first():
        raise HTTPException(400, f"客戶 {data.customer_id} 不存在，請先建立客戶")

    po = PurchaseOrder(
        po_id=data.po_id,
        customer_id=data.customer_id,
        remarks=data.remarks,
    )
    db.add(po)
    for i, line in enumerate(data.lines, 1):
        if not db.query(Item).filter(Item.item_code == line.item_code).first():
            raise HTTPException(400, f"料號 {line.item_code} 不存在，請先建立料號")
        pol = POLine(
            po_id=data.po_id,
            item_code=line.item_code,
            qty=line.qty,
            unit_price=line.unit_price,
            delivery_date=line.delivery_date,
            line_no=line.line_no or i,
        )
        db.add(pol)
    db.commit()
    db.refresh(po)
    return po


@app.post("/api/v1/po/{po_id}/convert", response_model=SORead)
def convert_po_to_so(po_id: str, so_id: Optional[str] = None, db=Depends(get_db)):
    po = db.query(PurchaseOrder).filter(PurchaseOrder.po_id == po_id).first()
    if not po:
        raise HTTPException(404, f"PO {po_id} 不存在")
    if po.status == POStatus.CONVERTED:
        raise HTTPException(400, f"PO {po_id} 已轉換為 SO")
    if po.status == POStatus.CANCELLED:
        raise HTTPException(400, f"PO {po_id} 已取消")

    so_id = so_id or gen_id("SO")
    so = SalesOrder(
        so_id=so_id,
        po_id=po_id,
        customer_id=po.customer_id,
    )
    db.add(so)
    for pol in po.lines:
        sol = SOLine(
            so_id=so_id,
            item_code=pol.item_code,
            qty=pol.qty,
            unit_price=pol.unit_price,
            delivery_date=pol.delivery_date,
            line_no=pol.line_no,
        )
        db.add(sol)

    po.status = POStatus.CONVERTED
    db.commit()
    db.refresh(so)
    return so


# ════════════════════════════════════════════════════════════════════════════
# 4. SO（銷貨單）
# ════════════════════════════════════════════════════════════════════════════

@app.get("/api/v1/so", response_model=list[SORead])
def list_sos(db=Depends(get_db)):
    return db.query(SalesOrder).all()


@app.get("/api/v1/so/{so_id}", response_model=SORead)
def get_so(so_id: str, db=Depends(get_db)):
    so = db.query(SalesOrder).filter(SalesOrder.so_id == so_id).first()
    if not so:
        raise HTTPException(404, f"SO {so_id} 不存在")
    return so


@app.get("/api/v1/so/{so_id}/lines", response_model=list[SOLineRead])
def get_so_lines(so_id: str, db=Depends(get_db)):
    so = db.query(SalesOrder).filter(SalesOrder.so_id == so_id).first()
    if not so:
        raise HTTPException(404, f"SO {so_id} 不存在")
    return so.lines


@app.post("/api/v1/so", response_model=SORead)
def create_so(data: SOCreate, db=Depends(get_db)):
    if db.query(SalesOrder).filter(SalesOrder.so_id == data.so_id).first():
        raise HTTPException(400, f"SO {data.so_id} 已存在")

    if data.po_id:
        po = db.query(PurchaseOrder).filter(PurchaseOrder.po_id == data.po_id).first()
        if po and po.customer_id != data.customer_id:
            raise HTTPException(400, "SO 客戶與 PO 客戶不符")

    so = SalesOrder(
        so_id=data.so_id,
        po_id=data.po_id,
        customer_id=data.customer_id,
        remarks=data.remarks,
        status=SOStatus.DRAFT,
    )
    db.add(so)
    for i, line in enumerate(data.lines, 1):
        if not db.query(Item).filter(Item.item_code == line.item_code).first():
            raise HTTPException(400, f"料號 {line.item_code} 不存在")
        sol = SOLine(
            so_id=data.so_id,
            item_code=line.item_code,
            qty=line.qty,
            unit_price=line.unit_price,
            delivery_date=line.delivery_date,
            delivery_location=line.delivery_location,
            line_no=line.line_no or i,
        )
        db.add(sol)
    db.commit()
    db.refresh(so)
    return so


@app.patch("/api/v1/so/{so_id}", response_model=SORead)
def update_so(
    so_id: str,
    status: Optional[SOStatus] = None,
    remarks: Optional[str] = None,
    db=Depends(get_db),
):
    so = db.query(SalesOrder).filter(SalesOrder.so_id == so_id).first()
    if not so:
        raise HTTPException(404, f"SO {so_id} 不存在")
    if status:
        so.status = status
    if remarks is not None:
        so.remarks = remarks
    db.commit()
    db.refresh(so)
    return so


# ════════════════════════════════════════════════════════════════════════════
# 5. ATP / CTP（交期試算）
# ════════════════════════════════════════════════════════════════════════════

@app.post("/api/v1/atp/check", response_model=ATPResponse)
def atp_check(
    req: ATPRequest,
    force_insufficient: bool = Query(False),
    force_delay: bool = Query(False),
    db=Depends(get_db),
):
    item = db.query(Item).filter(Item.item_code == req.item_code, Item.is_active).first()
    if not item:
        raise HTTPException(404, f"料號 {req.item_code} 不存在")

    check_id = gen_id("ATP")
    now = datetime.now(timezone.utc)
    available_qty = item.safety_stock
    lead_days = item.lead_time_days

    if force_insufficient:
        available_qty = req.qty // 2
    available_date = req.request_date + timedelta(days=lead_days)

    if force_delay:
        available_date += timedelta(days=5)
        result = ATPResult.DELAYED
        remarks = "模擬延遲：供應商交期延後"
    elif available_qty >= req.qty:
        result = ATPResult.ON_TIME
        remarks = f"可承諾 {available_qty} 件，預計 {available_date.strftime('%Y-%m-%d')} 交貨"
    else:
        result = ATPResult.INSUFFICIENT
        remarks = f"庫存不足（可承諾 {available_qty}，需求 {req.qty}），建議分批或尋找替代料"

    record = ATPCheck(
        check_id=check_id,
        item_code=req.item_code,
        qty=req.qty,
        request_date=req.request_date,
        available_date=available_date,
        available_qty=available_qty,
        result=result,
        remarks=remarks,
    )
    db.add(record)
    db.commit()
    return ATPResponse(
        check_id=check_id,
        item_code=req.item_code,
        qty=req.qty,
        request_date=req.request_date,
        available_date=available_date,
        available_qty=available_qty,
        result=result,
        remarks=remarks,
        checked_at=now,
    )


@app.post("/api/v1/ctp/check", response_model=CTPResponse)
def ctp_check(
    req: ATPRequest,
    force_insufficient: bool = Query(False),
    force_delay: bool = Query(False),
    db=Depends(get_db),
):
    item = db.query(Item).filter(Item.item_code == req.item_code, Item.is_active).first()
    if not item:
        raise HTTPException(404, f"料號 {req.item_code} 不存在")

    check_id = gen_id("CTP")
    now = datetime.now(timezone.utc)
    available_qty = item.safety_stock
    lead_days = item.lead_time_days
    daily_cap = item.daily_capacity

    batches_needed = max(1, (req.qty + daily_cap - 1) // daily_cap)
    production_days = batches_needed * lead_days

    if force_insufficient:
        available_qty = req.qty // 2
    available_date = req.request_date + timedelta(days=production_days)

    if force_delay:
        available_date += timedelta(days=5)
        result = ATPResult.DELAYED
        remarks = f"模擬延遲：產能瓶頸，預計需要 {batches_needed} 批次"
    elif available_qty >= req.qty:
        result = ATPResult.ON_TIME
        remarks = f"可交付 {available_qty} 件，預計 {available_date.strftime('%Y-%m-%d')}，需 {batches_needed} 批次"
    else:
        result = ATPResult.INSUFFICIENT
        remarks = f"產能不足（可交付 {available_qty}，需求 {req.qty}），建議 {batches_needed} 批次交貨"

    record = CTPCheck(
        check_id=check_id,
        item_code=req.item_code,
        qty=req.qty,
        request_date=req.request_date,
        available_date=available_date,
        available_qty=available_qty,
        result=result,
        batch_recommended=batches_needed,
        remarks=remarks,
    )
    db.add(record)
    db.commit()
    return CTPResponse(
        check_id=check_id,
        item_code=req.item_code,
        qty=req.qty,
        request_date=req.request_date,
        available_date=available_date,
        available_qty=available_qty,
        result=result,
        batch_recommended=batches_needed,
        remarks=remarks,
        checked_at=now,
    )


# ════════════════════════════════════════════════════════════════════════════
# 6. Shipping（出貨）v2.0 — Deepened
# ════════════════════════════════════════════════════════════════════════════

@app.post("/api/v1/shipping/create", response_model=ShippingRead)
def create_shipping(data: ShippingCreate, db=Depends(get_db)):
    so = db.query(SalesOrder).filter(SalesOrder.so_id == data.so_id).first()
    if not so:
        raise HTTPException(404, f"SO {data.so_id} 不存在")
    if db.query(Shipping).filter(Shipping.shipping_id == data.shipping_id).first():
        raise HTTPException(400, f"出貨單 {data.shipping_id} 已存在")

    shipping = Shipping(
        shipping_id=data.shipping_id,
        so_id=data.so_id,
        pallet_count=data.pallet_count,
        container_type=data.container_type,
        customs_date=data.customs_date,
        ship_from_location=data.ship_from_location,
        ship_to_address=data.ship_to_address or so.lines[0].delivery_location if so.lines else None,
    )
    db.add(shipping)
    db.commit()
    db.refresh(shipping)
    return shipping


@app.get("/api/v1/shipping/{shipping_id}", response_model=ShippingRead)
def get_shipping(shipping_id: str, db=Depends(get_db)):
    s = db.query(Shipping).filter(Shipping.shipping_id == shipping_id).first()
    if not s:
        raise HTTPException(404, f"出貨單 {shipping_id} 不存在")
    return s


@app.patch("/api/v1/shipping/{shipping_id}/pack", response_model=ShippingRead)
def do_pack(shipping_id: str, pallet_count: int = Query(1, ge=0), db=Depends(get_db)):
    s = db.query(Shipping).filter(Shipping.shipping_id == shipping_id).first()
    if not s:
        raise HTTPException(404, f"出貨單 {shipping_id} 不存在")
    if s.status != ShippingStatus.PENDING:
        raise HTTPException(400, f"出貨單 {shipping_id} 狀態為 {s.status}，無法包裝")
    s.status = ShippingStatus.PACKING
    s.pallet_count = pallet_count
    db.commit()
    db.refresh(s)
    return s


@app.patch("/api/v1/shipping/{shipping_id}/ship", response_model=ShippingRead)
def do_ship(shipping_id: str, tracking_no: Optional[str] = None, db=Depends(get_db)):
    s = db.query(Shipping).filter(Shipping.shipping_id == shipping_id).first()
    if not s:
        raise HTTPException(404, f"出貨單 {shipping_id} 不存在")
    if s.status not in (ShippingStatus.PACKED, ShippingStatus.PACKING, ShippingStatus.PARTIAL_PACKED):
        raise HTTPException(400, f"出貨單 {shipping_id} 狀態為 {s.status}，需先完成包裝")
    # auto-transition: packing/partial_packed → shipped if pack_details exist
    has_details = db.query(ShippingPackDetail).filter(ShippingPackDetail.shipping_id == shipping_id).first()
    s.status = ShippingStatus.PACKED if has_details and s.status != ShippingStatus.PACKED else s.status
    s.status = ShippingStatus.SHIPPED
    s.tracking_no = tracking_no or gen_id("TRK")
    s.actual_ship_date = datetime.now(timezone.utc)
    db.commit()
    db.refresh(s)
    return s


# ── v2.0 Pack Detail ───────────────────────────────────────────────────────

@app.patch("/api/v1/shipping/{shipping_id}/pack_detail", response_model=ShippingRead)
def update_pack_detail(shipping_id: str, details: list[ShippingPackDetailCreate], db=Depends(get_db)):
    s = db.query(Shipping).filter(Shipping.shipping_id == shipping_id).first()
    if not s:
        raise HTTPException(404, f"出貨單 {shipping_id} 不存在")
    if s.status not in (ShippingStatus.PENDING, ShippingStatus.PACKING):
        raise HTTPException(400, f"出貨單 {shipping_id} 狀態為 {s.status}，無法更新包裝明細")

    # clear existing and replace
    db.query(ShippingPackDetail).filter(ShippingPackDetail.shipping_id == shipping_id).delete()
    for d in details:
        pd = ShippingPackDetail(
            shipping_id=shipping_id,
            pallet_no=d.pallet_no,
            line_no=d.line_no,
            item_code=d.item_code,
            qty_packed=d.qty_packed,
            qty_shipped=d.qty_shipped,
            weight_kg=d.weight_kg,
            dimensions_cm=d.dimensions_cm,
            remarks=d.remarks,
        )
        db.add(pd)

    if s.status == ShippingStatus.PENDING:
        s.status = ShippingStatus.PACKING
    s.pallet_count = max((d.pallet_no for d in details), default=s.pallet_count)
    db.commit()
    db.refresh(s)
    return s


@app.get("/api/v1/shipping/{shipping_id}/pack_detail", response_model=list[ShippingPackDetailRead])
def get_pack_detail(shipping_id: str, db=Depends(get_db)):
    s = db.query(Shipping).filter(Shipping.shipping_id == shipping_id).first()
    if not s:
        raise HTTPException(404, f"出貨單 {shipping_id} 不存在")
    return s.pack_details


@app.get("/api/v1/shipping/{shipping_id}/lines", response_model=list[SOLineRead])
def get_shipping_lines(shipping_id: str, db=Depends(get_db)):
    s = db.query(Shipping).filter(Shipping.shipping_id == shipping_id).first()
    if not s:
        raise HTTPException(404, f"出貨單 {shipping_id} 不存在")
    so = db.query(SalesOrder).filter(SalesOrder.so_id == s.so_id).first()
    return so.lines if so else []


# ── v2.0 Partial Pack ──────────────────────────────────────────────────────

@app.patch("/api/v1/shipping/{shipping_id}/pack_partial", response_model=ShippingRead)
def do_pack_partial(shipping_id: str, items: list[ShippingPackPartialRequest], db=Depends(get_db)):
    s = db.query(Shipping).filter(Shipping.shipping_id == shipping_id).first()
    if not s:
        raise HTTPException(404, f"出貨單 {shipping_id} 不存在")
    if s.status not in (ShippingStatus.PENDING, ShippingStatus.PACKING, ShippingStatus.PARTIAL_PACKED):
        raise HTTPException(400, f"出貨單 {shipping_id} 狀態為 {s.status}，無法部分包裝")

    for item in items:
        pd = ShippingPackDetail(
            shipping_id=shipping_id,
            pallet_no=item.pallet_no,
            line_no=item.line_no,
            item_code=item.item_code,
            qty_packed=item.qty_packed,
            weight_kg=item.weight_kg,
            dimensions_cm=item.dimensions_cm,
            remarks=item.remarks,
        )
        db.add(pd)

    s.status = ShippingStatus.PARTIAL_PACKED
    db.commit()
    db.refresh(s)
    return s


# ── v2.0 Partial Ship ──────────────────────────────────────────────────────

@app.patch("/api/v1/shipping/{shipping_id}/partial_ship", response_model=ShippingRead)
def do_partial_ship(shipping_id: str, data: PartialShipRequest, db=Depends(get_db)):
    s = db.query(Shipping).filter(Shipping.shipping_id == shipping_id).first()
    if not s:
        raise HTTPException(404, f"出貨單 {shipping_id} 不存在")
    if s.status not in (ShippingStatus.PACKED, ShippingStatus.PARTIAL_PACKED, ShippingStatus.SHIPPED):
        raise HTTPException(400, f"出貨單 {shipping_id} 狀態為 {s.status}，無法部分出貨")

    s.status = ShippingStatus.SHIPPED
    s.remaining_qty = data.remaining_qty
    s.remarks = data.remarks or s.remarks
    s.actual_ship_date = s.actual_ship_date or datetime.now(timezone.utc)
    if data.remaining_qty > 0:
        s.partial_delivery = True
    db.commit()
    db.refresh(s)
    return s


# ── v2.0 Partial Deliver ───────────────────────────────────────────────────

@app.patch("/api/v1/shipping/{shipping_id}/partial_deliver", response_model=ShippingRead)
def do_partial_deliver(shipping_id: str, data: PartialDeliverRequest, db=Depends(get_db)):
    s = db.query(Shipping).filter(Shipping.shipping_id == shipping_id).first()
    if not s:
        raise HTTPException(404, f"出貨單 {shipping_id} 不存在")
    if s.status not in (ShippingStatus.SHIPPED, ShippingStatus.PARTIAL_DELIVERY):
        raise HTTPException(400, f"出貨單 {shipping_id} 狀態為 {s.status}，無法部分到貨")

    s.status = ShippingStatus.PARTIAL_DELIVERY
    s.remaining_qty = data.remaining_qty
    s.delivery_proof_url = data.delivery_proof_url or s.delivery_proof_url
    s.is_delivery_signed = data.is_delivery_signed
    s.remarks = data.remarks or s.remarks
    db.commit()
    db.refresh(s)
    return s


# ── v2.0 Deliver (簽收完成) ────────────────────────────────────────────────

@app.patch("/api/v1/shipping/{shipping_id}/deliver", response_model=ShippingRead)
def do_deliver(shipping_id: str, data: ShippingDeliverRequest = None, db=Depends(get_db)):
    s = db.query(Shipping).filter(Shipping.shipping_id == shipping_id).first()
    if not s:
        raise HTTPException(404, f"出貨單 {shipping_id} 不存在")
    if s.status not in (ShippingStatus.SHIPPED, ShippingStatus.PARTIAL_DELIVERY):
        raise HTTPException(400, f"出貨單 {shipping_id} 狀態為 {s.status}，需先出貨")

    s.status = ShippingStatus.DELIVERED
    s.actual_arrive_date = datetime.now(timezone.utc)
    s.is_delivery_signed = True
    if data:
        s.delivery_proof_url = data.delivery_proof_url or s.delivery_proof_url
        s.remarks = data.remarks or s.remarks

    # sync SO status to completed if all shippings delivered
    so_shippings = db.query(Shipping).filter(Shipping.so_id == s.so_id).all()
    if all(sh.status == ShippingStatus.DELIVERED for sh in so_shippings):
        so = db.query(SalesOrder).filter(SalesOrder.so_id == s.so_id).first()
        if so:
            so.status = SOStatus.COMPLETED

    db.commit()
    db.refresh(s)
    return s


# ── v2.0 Attachments ───────────────────────────────────────────────────────

@app.post("/api/v1/shipping/{shipping_id}/attach", response_model=ShippingAttachmentRead)
def attach_shipping_doc(shipping_id: str, data: ShippingAttachmentCreate, db=Depends(get_db)):
    s = db.query(Shipping).filter(Shipping.shipping_id == shipping_id).first()
    if not s:
        raise HTTPException(404, f"出貨單 {shipping_id} 不存在")
    if db.query(ShippingAttachment).filter(ShippingAttachment.attachment_id == data.attachment_id).first():
        raise HTTPException(400, f"附件 {data.attachment_id} 已存在")

    att = ShippingAttachment(
        attachment_id=data.attachment_id,
        shipping_id=shipping_id,
        type=data.type,
        filename=data.filename,
        url=data.url,
        uploaded_by=data.uploaded_by,
    )
    db.add(att)
    db.commit()
    db.refresh(att)
    return att


@app.get("/api/v1/shipping/{shipping_id}/attachments", response_model=list[ShippingAttachmentRead])
def get_shipping_attachments(shipping_id: str, db=Depends(get_db)):
    s = db.query(Shipping).filter(Shipping.shipping_id == shipping_id).first()
    if not s:
        raise HTTPException(404, f"出貨單 {shipping_id} 不存在")
    return s.attachments


# ════════════════════════════════════════════════════════════════════════════
# 7. Invoice（發票）v2.0 — Deepened
# ════════════════════════════════════════════════════════════════════════════

@app.post("/api/v1/invoice/create", response_model=InvoiceRead)
def create_invoice(data: InvoiceCreate, db=Depends(get_db)):
    so = db.query(SalesOrder).filter(SalesOrder.so_id == data.so_id).first()
    if not so:
        raise HTTPException(404, f"SO {data.so_id} 不存在")
    if db.query(Invoice).filter(Invoice.invoice_id == data.invoice_id).first():
        raise HTTPException(400, f"發票 {data.invoice_id} 已存在")

    net = data.net_amount or (data.amount - data.tax_amount)
    invoice = Invoice(
        invoice_id=data.invoice_id,
        shipping_id=data.shipping_id,
        so_id=data.so_id,
        amount=data.amount,
        issue_date=datetime.now(timezone.utc),
        status=InvoiceStatus.DRAFT,
        invoice_no=data.invoice_no,
        invoice_type=data.invoice_type,
        tax_amount=data.tax_amount,
        net_amount=net,
        currency=data.currency,
        due_date=data.due_date,
        grace_days=data.grace_days,
    )
    db.add(invoice)
    db.flush()

    # invoice lines
    for i, line in enumerate(data.lines, 1):
        il = InvoiceLine(
            invoice_id=data.invoice_id,
            line_no=line.line_no or i,
            item_code=line.item_code,
            description=line.description,
            qty=line.qty,
            unit_price=line.unit_price,
            amount=line.amount or (line.qty * line.unit_price),
            so_line_id=line.so_line_id,
        )
        db.add(il)

    db.commit()
    db.refresh(invoice)
    return invoice


@app.get("/api/v1/invoice/by_so/{so_id}", response_model=list[InvoiceRead])
def get_invoices_by_so(so_id: str, db=Depends(get_db)):
    so = db.query(SalesOrder).filter(SalesOrder.so_id == so_id).first()
    if not so:
        raise HTTPException(404, f"SO {so_id} 不存在")
    return so.invoices


@app.get("/api/v1/invoice/overdue", response_model=list[InvoiceRead])
def get_overdue_invoices(
    days_overdue: int = Query(1, ge=0),
    include_dunning: bool = Query(True),
    db=Depends(get_db),
):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_overdue)
    statuses = [InvoiceStatus.SENT]
    if include_dunning:
        statuses.append(InvoiceStatus.DUNNING)

    overdue = db.query(Invoice).filter(
        Invoice.status.in_(statuses),
        Invoice.due_date < cutoff,
    ).all()

    # auto-mark as overdue
    for inv in overdue:
        if inv.status == InvoiceStatus.SENT:
            inv.status = InvoiceStatus.OVERDUE
    db.commit()
    return overdue


@app.get("/api/v1/invoice/{invoice_id}", response_model=InvoiceRead)
def get_invoice(invoice_id: str, db=Depends(get_db)):
    inv = db.query(Invoice).filter(Invoice.invoice_id == invoice_id).first()
    if not inv:
        raise HTTPException(404, f"發票 {invoice_id} 不存在")
    return inv


@app.patch("/api/v1/invoice/{invoice_id}/issue", response_model=InvoiceRead)
def issue_invoice(invoice_id: str, data: InvoiceIssueRequest = None, db=Depends(get_db)):
    inv = db.query(Invoice).filter(Invoice.invoice_id == invoice_id).first()
    if not inv:
        raise HTTPException(404, f"發票 {invoice_id} 不存在")
    if inv.status != InvoiceStatus.DRAFT:
        raise HTTPException(400, f"發票 {invoice_id} 狀態為 {inv.status}，無法開立")

    inv.status = InvoiceStatus.ISSUED
    inv.issue_date = datetime.now(timezone.utc)
    if data:
        inv.invoice_no = data.invoice_no or inv.invoice_no
        inv.due_date = data.due_date or inv.due_date
    db.commit()
    db.refresh(inv)
    return inv


@app.post("/api/v1/invoice/{invoice_id}/send", response_model=InvoiceRead)
def send_invoice(invoice_id: str, db=Depends(get_db)):
    inv = db.query(Invoice).filter(Invoice.invoice_id == invoice_id).first()
    if not inv:
        raise HTTPException(404, f"發票 {invoice_id} 不存在")
    if inv.status != InvoiceStatus.ISSUED:
        raise HTTPException(400, f"發票 {invoice_id} 狀態為 {inv.status}，需先開立")

    inv.status = InvoiceStatus.SENT
    db.commit()
    db.refresh(inv)
    return inv


@app.post("/api/v1/invoice/{invoice_id}/payment", response_model=InvoiceRead)
def receive_payment(invoice_id: str, data: InvoicePaymentRequest = None, db=Depends(get_db)):
    inv = db.query(Invoice).filter(Invoice.invoice_id == invoice_id).first()
    if not inv:
        raise HTTPException(404, f"發票 {invoice_id} 不存在")
    if inv.status in (InvoiceStatus.PAID, InvoiceStatus.RECONCILED):
        raise HTTPException(400, f"發票 {invoice_id} 已收款")

    inv.status = InvoiceStatus.PAID
    inv.payment_date = datetime.now(timezone.utc)
    if data:
        inv.payment_ref = data.payment_ref or inv.payment_ref
        if data.payment_date:
            inv.payment_date = data.payment_date
    db.commit()
    db.refresh(inv)
    return inv


@app.patch("/api/v1/invoice/{invoice_id}/void", response_model=InvoiceRead)
def void_invoice(invoice_id: str, data: InvoiceVoidRequest, db=Depends(get_db)):
    inv = db.query(Invoice).filter(Invoice.invoice_id == invoice_id).first()
    if not inv:
        raise HTTPException(404, f"發票 {invoice_id} 不存在")
    if inv.status in (InvoiceStatus.VOID, InvoiceStatus.PAID, InvoiceStatus.RECONCILED):
        raise HTTPException(400, f"發票 {invoice_id} 狀態為 {inv.status}，無法作廢")

    inv.status = InvoiceStatus.VOID
    inv.void_reason = data.void_reason
    db.commit()
    db.refresh(inv)
    return inv


@app.post("/api/v1/invoice/{invoice_id}/credit", response_model=InvoiceRead)
def issue_credit_note(invoice_id: str, data: InvoiceCreditNoteRequest, db=Depends(get_db)):
    inv = db.query(Invoice).filter(Invoice.invoice_id == invoice_id).first()
    if not inv:
        raise HTTPException(404, f"發票 {invoice_id} 不存在")

    # create credit note
    cn_id = gen_id("CN")
    cn = Invoice(
        invoice_id=cn_id,
        so_id=inv.so_id,
        amount=data.amount,
        status=InvoiceStatus.CREDIT_NOTE,
        invoice_type="credit_note",
        credit_note_for=invoice_id,
        currency=inv.currency,
    )
    db.add(cn)

    # mark original as credit_note
    inv.status = InvoiceStatus.CREDIT_NOTE
    inv.credit_note_for = cn_id
    db.commit()
    db.refresh(cn)
    return cn


@app.get("/api/v1/invoice/{invoice_id}/lines", response_model=list[InvoiceLineRead])
def get_invoice_lines(invoice_id: str, db=Depends(get_db)):
    inv = db.query(Invoice).filter(Invoice.invoice_id == invoice_id).first()
    if not inv:
        raise HTTPException(404, f"發票 {invoice_id} 不存在")
    return inv.lines


# ════════════════════════════════════════════════════════════════════════════
# 8. Logistics（物流）v2.0 — Deepened
# ════════════════════════════════════════════════════════════════════════════

def _write_logistics_event(tracking_no: str, status: str, location: Optional[str],
                           note: Optional[str], created_by: Optional[str], db):
    event = LogisticsEvent(
        event_id=gen_id("LEV"),
        tracking_no=tracking_no,
        status=status,
        location=location,
        note=note,
        event_at=datetime.now(timezone.utc),
        created_by=created_by or "system",
    )
    db.add(event)
    return event


@app.post("/api/v1/logistics/arrange", response_model=LogisticsRead)
def arrange_logistics(data: LogisticsCreate, db=Depends(get_db)):
    shipping = db.query(Shipping).filter(Shipping.shipping_id == data.shipping_id).first()
    if not shipping:
        raise HTTPException(404, f"出貨單 {data.shipping_id} 不存在")
    if db.query(Logistics).filter(Logistics.tracking_no == data.tracking_no).first():
        raise HTTPException(400, f"物流單 {data.tracking_no} 已存在")

    logistics = Logistics(
        tracking_no=data.tracking_no,
        shipping_id=data.shipping_id,
        carrier=data.carrier,
        eta=data.eta,
        origin_port=data.origin_port,
        dest_port=data.dest_port,
        vessel_flight=data.vessel_flight,
        bl_number=data.bl_number,
        booking_ref=data.booking_ref,
    )
    db.add(logistics)
    _write_logistics_event(data.tracking_no, "booked", None, "物流已預約", "system", db)

    # sync carrier to shipping
    if data.carrier:
        shipping.carrier = data.carrier

    db.commit()
    db.refresh(logistics)
    return logistics


# ── v2.0 Logistics Queries (must be BEFORE /{tracking_no} to avoid route conflicts) ──

@app.get("/api/v1/logistics/by_shipping/{shipping_id}", response_model=LogisticsRead)
def get_logistics_by_shipping(shipping_id: str, db=Depends(get_db)):
    lg = db.query(Logistics).filter(Logistics.shipping_id == shipping_id).first()
    if not lg:
        raise HTTPException(404, f"出貨單 {shipping_id} 尚無物流記錄")
    return lg


@app.get("/api/v1/logistics/active", response_model=list[LogisticsRead])
def get_active_logistics(
    carrier: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db=Depends(get_db),
):
    q = db.query(Logistics).filter(
        Logistics.status.notin_([LogisticsStatus.DELIVERED, LogisticsStatus.FAILED])
    )
    if carrier:
        q = q.filter(Logistics.carrier == carrier)
    return q.limit(limit).all()


@app.get("/api/v1/logistics/{tracking_no}", response_model=LogisticsRead)
def get_logistics(tracking_no: str, db=Depends(get_db)):
    lg = db.query(Logistics).filter(Logistics.tracking_no == tracking_no).first()
    if not lg:
        raise HTTPException(404, f"物流單 {tracking_no} 不存在")
    return lg


@app.post("/api/v1/logistics/{tracking_no}/depart", response_model=LogisticsRead)
def logistics_depart(tracking_no: str, data: LogisticsDepartRequest = None, db=Depends(get_db)):
    lg = db.query(Logistics).filter(Logistics.tracking_no == tracking_no).first()
    if not lg:
        raise HTTPException(404, f"物流單 {tracking_no} 不存在")
    if lg.status not in (LogisticsStatus.BOOKED, LogisticsStatus.REROUTE):
        raise HTTPException(400, f"物流單 {tracking_no} 狀態為 {lg.status}，無法出發")

    lg.status = LogisticsStatus.IN_TRANSIT
    lg.departure_date = datetime.now(timezone.utc)
    if data:
        if data.departure_date:
            lg.departure_date = data.departure_date
        if data.vessel_flight:
            lg.vessel_flight = data.vessel_flight
        if data.origin_port:
            lg.origin_port = data.origin_port
        _write_logistics_event(tracking_no, "in_transit", data.origin_port, data.note or "已出發", "system", db)
    else:
        _write_logistics_event(tracking_no, "in_transit", None, "已出發", "system", db)

    db.commit()
    db.refresh(lg)
    return lg


@app.post("/api/v1/logistics/{tracking_no}/customs", response_model=LogisticsRead)
def logistics_customs(tracking_no: str, data: LogisticsCustomsRequest = None, db=Depends(get_db)):
    lg = db.query(Logistics).filter(Logistics.tracking_no == tracking_no).first()
    if not lg:
        raise HTTPException(404, f"物流單 {tracking_no} 不存在")
    if lg.status not in (LogisticsStatus.BOOKED, LogisticsStatus.IN_TRANSIT):
        raise HTTPException(400, f"物流單 {tracking_no} 狀態為 {lg.status}，無法進入通關")

    if data:
        lg.customs_status = data.customs_status
        if data.bl_number:
            lg.bl_number = data.bl_number
        if data.dest_port:
            lg.dest_port = data.dest_port
        lg.status = LogisticsStatus.CUSTOMS_HOLD if data.customs_status == "held" else LogisticsStatus.CUSTOMS
        _write_logistics_event(tracking_no, lg.status.value, data.dest_port, data.note or "通關程序", "system", db)
    else:
        lg.status = LogisticsStatus.CUSTOMS
        _write_logistics_event(tracking_no, "customs", None, "進入通關", "system", db)

    db.commit()
    db.refresh(lg)
    return lg


@app.post("/api/v1/logistics/{tracking_no}/customs_hold", response_model=LogisticsRead)
def logistics_customs_hold(tracking_no: str, data: LogisticsCustomsHoldRequest, db=Depends(get_db)):
    lg = db.query(Logistics).filter(Logistics.tracking_no == tracking_no).first()
    if not lg:
        raise HTTPException(404, f"物流單 {tracking_no} 不存在")

    lg.status = LogisticsStatus.CUSTOMS_HOLD
    lg.customs_status = "held"
    _write_logistics_event(tracking_no, "customs_hold", None, data.reason, "system", db)

    db.commit()
    db.refresh(lg)
    return lg


@app.post("/api/v1/logistics/{tracking_no}/customs_clear", response_model=LogisticsRead)
def logistics_customs_clear(tracking_no: str, data: LogisticsCustomsClearRequest = None, db=Depends(get_db)):
    lg = db.query(Logistics).filter(Logistics.tracking_no == tracking_no).first()
    if not lg:
        raise HTTPException(404, f"物流單 {tracking_no} 不存在")
    if lg.status not in (LogisticsStatus.CUSTOMS, LogisticsStatus.CUSTOMS_HOLD, LogisticsStatus.CLEARED_RETRY):
        raise HTTPException(400, f"物流單 {tracking_no} 狀態為 {lg.status}，無法清關")

    lg.status = LogisticsStatus.IN_TRANSIT
    lg.customs_status = "cleared"
    note = (data.note if data else None) or "清關完成，繼續運輸"
    _write_logistics_event(tracking_no, "in_transit", None, note, "system", db)

    db.commit()
    db.refresh(lg)
    return lg


@app.post("/api/v1/logistics/{tracking_no}/arrive", response_model=LogisticsRead)
def confirm_arrival(tracking_no: str, data: LogisticsArriveRequest = None, db=Depends(get_db)):
    lg = db.query(Logistics).filter(Logistics.tracking_no == tracking_no).first()
    if not lg:
        raise HTTPException(404, f"物流單 {tracking_no} 不存在")
    if lg.status == LogisticsStatus.DELIVERED:
        raise HTTPException(400, f"物流單 {tracking_no} 已送達")

    lg.status = LogisticsStatus.ARRIVED
    lg.actual_arrival = datetime.now(timezone.utc)
    if data:
        if data.actual_arrival:
            lg.actual_arrival = data.actual_arrival
        lg.delivery_note = data.delivery_note or lg.delivery_note

    _write_logistics_event(tracking_no, "arrived", None, lg.delivery_note or "已送達", "system", db)

    # update shipping status
    shipping = db.query(Shipping).filter(Shipping.shipping_id == lg.shipping_id).first()
    if shipping:
        shipping.status = ShippingStatus.DELIVERED
        shipping.actual_arrive_date = lg.actual_arrival
        shipping.carrier = lg.carrier or shipping.carrier

    db.commit()
    db.refresh(lg)
    return lg


@app.post("/api/v1/logistics/{tracking_no}/partial_arrive", response_model=LogisticsRead)
def logistics_partial_arrive(tracking_no: str, data: LogisticsPartialArriveRequest, db=Depends(get_db)):
    lg = db.query(Logistics).filter(Logistics.tracking_no == tracking_no).first()
    if not lg:
        raise HTTPException(404, f"物流單 {tracking_no} 不存在")
    if lg.status in (LogisticsStatus.DELIVERED, LogisticsStatus.FAILED):
        raise HTTPException(400, f"物流單 {tracking_no} 狀態為 {lg.status}，無法部分到貨")

    lg.status = LogisticsStatus.PARTIAL_DELIVERY
    _write_logistics_event(
        tracking_no, "partial_delivery", None,
        f"部分到貨：已送達 {data.delivered_qty}，剩餘 {data.remaining_qty}", "system", db,
    )

    shipping = db.query(Shipping).filter(Shipping.shipping_id == lg.shipping_id).first()
    if shipping:
        shipping.status = ShippingStatus.PARTIAL_DELIVERY
        shipping.remaining_qty = data.remaining_qty
        shipping.partial_delivery = True

    db.commit()
    db.refresh(lg)
    return lg


@app.post("/api/v1/logistics/{tracking_no}/deliver_sign", response_model=LogisticsRead)
def logistics_deliver_sign(tracking_no: str, data: LogisticsDeliverSignRequest, db=Depends(get_db)):
    lg = db.query(Logistics).filter(Logistics.tracking_no == tracking_no).first()
    if not lg:
        raise HTTPException(404, f"物流單 {tracking_no} 不存在")
    if lg.status == LogisticsStatus.DELIVERED:
        raise HTTPException(400, f"物流單 {tracking_no} 已簽收")

    lg.status = LogisticsStatus.DELIVERED
    lg.actual_arrival = lg.actual_arrival or datetime.now(timezone.utc)
    lg.delivery_signed_by = data.signed_by
    lg.delivery_note = data.delivery_note or lg.delivery_note
    lg.is_final_delivery = data.is_final

    _write_logistics_event(
        tracking_no, "delivered", None,
        f"簽收人：{data.signed_by}" + (f" ({data.delivery_note})" if data.delivery_note else ""),
        "system", db,
    )

    # sync shipping
    shipping = db.query(Shipping).filter(Shipping.shipping_id == lg.shipping_id).first()
    if shipping:
        shipping.status = ShippingStatus.DELIVERED
        shipping.is_delivery_signed = True
        shipping.actual_arrive_date = lg.actual_arrival
        # sync SO to completed if all shipped
        so_shippings = db.query(Shipping).filter(Shipping.so_id == shipping.so_id).all()
        if all(sh.status == ShippingStatus.DELIVERED for sh in so_shippings):
            so = db.query(SalesOrder).filter(SalesOrder.so_id == shipping.so_id).first()
            if so:
                so.status = SOStatus.COMPLETED

    db.commit()
    db.refresh(lg)
    return lg


@app.post("/api/v1/logistics/{tracking_no}/failed", response_model=LogisticsRead)
def logistics_failed(tracking_no: str, data: LogisticsFailedRequest, db=Depends(get_db)):
    lg = db.query(Logistics).filter(Logistics.tracking_no == tracking_no).first()
    if not lg:
        raise HTTPException(404, f"物流單 {tracking_no} 不存在")
    if lg.status == LogisticsStatus.DELIVERED:
        raise HTTPException(400, f"物流單 {tracking_no} 已送達")

    lg.status = LogisticsStatus.FAILED
    _write_logistics_event(tracking_no, "failed", None, f"{data.reason}" + (f" ({data.note})" if data.note else ""), "system", db)

    db.commit()
    db.refresh(lg)
    return lg


@app.post("/api/v1/logistics/{tracking_no}/reroute", response_model=LogisticsRead)
def logistics_reroute(tracking_no: str, data: LogisticsRerouteRequest, db=Depends(get_db)):
    lg = db.query(Logistics).filter(Logistics.tracking_no == tracking_no).first()
    if not lg:
        raise HTTPException(404, f"物流單 {tracking_no} 不存在")
    if lg.status not in (LogisticsStatus.FAILED, LogisticsStatus.CUSTOMS_HOLD):
        raise HTTPException(400, f"物流單 {tracking_no} 狀態為 {lg.status}，無法重新安排")

    lg.status = LogisticsStatus.REROUTE
    if data.new_carrier:
        lg.carrier = data.new_carrier
    if data.new_eta:
        lg.eta = data.new_eta
    _write_logistics_event(tracking_no, "reroute", None, data.note or "重新安排路線", "system", db)

    db.commit()
    db.refresh(lg)
    return lg


# ── Events / Manual ───────────────────────────────────────────────────

@app.post("/api/v1/logistics/{tracking_no}/event", response_model=LogisticsEventRead)
def write_logistics_event_manual(tracking_no: str, data: LogisticsEventCreate, db=Depends(get_db)):
    lg = db.query(Logistics).filter(Logistics.tracking_no == tracking_no).first()
    if not lg:
        raise HTTPException(404, f"物流單 {tracking_no} 不存在")

    event = LogisticsEvent(
        event_id=data.event_id or gen_id("LEV"),
        tracking_no=tracking_no,
        status=data.status,
        location=data.location,
        note=data.note,
        event_at=data.event_at or datetime.now(timezone.utc),
        created_by=data.created_by or "agent",
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@app.get("/api/v1/logistics/{tracking_no}/events", response_model=list[LogisticsEventRead])
def get_logistics_events(tracking_no: str, db=Depends(get_db)):
    lg = db.query(Logistics).filter(Logistics.tracking_no == tracking_no).first()
    if not lg:
        raise HTTPException(404, f"物流單 {tracking_no} 不存在")
    return sorted(lg.events, key=lambda e: e.event_at)


# ════════════════════════════════════════════════════════════════════════════
# Health & Info
# ════════════════════════════════════════════════════════════════════════════

@app.get("/healthz", response_model=OkResponse)
def healthz():
    return OkResponse(ok=True, message="OTD ERP Simulator is running")


@app.get("/", response_model=OkResponse)
def root():
    return OkResponse(ok=True, message="OTD ERP 模擬層 — 請參閱 /docs 取得完整 API 文件")
