"""OTD ERP 模擬層 - FastAPI 主程式"""

import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.responses import JSONResponse

from models import (
    Base, SessionLocal, engine,
    Item, Customer, PurchaseOrder, POLine,
    SalesOrder, SOLine, ATPCheck, CTPCheck,
    Shipping, Invoice, Logistics,
    POStatus, SOStatus, ATPResult, ShippingStatus, InvoiceStatus, LogisticsStatus
)
from schemas import (
    ItemCreate, ItemRead,
    CustomerCreate, CustomerRead,
    POCreate, PORead, POLineRead,
    SOCreate, SORead, SOLineRead,
    ATPRequest, ATPResponse,
    CTPResponse,
    ShippingCreate, ShippingRead,
    InvoiceCreate, InvoiceRead,
    LogisticsCreate, LogisticsRead,
    OkResponse
)

# ── Init ────────────────────────────────────────────────────────────────────

from sqlalchemy.orm import Session

app = FastAPI(
    title="OTD ERP 模擬層",
    description="OTD 流程之 ERP 系統模擬介面，供各 Agent 統一讀寫",
    version="1.1.0",
)

# ── CORS — 允許前端面板跨域存取 ──
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8040",
        "http://localhost:3000",
        "http://localhost:5173",
        "http://100.107.36.80:8040",
        "http://100.107.36.80:8004",
        "http://100.107.36.80:8000",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    return db.query(Item).filter(Item.is_active == True).all()


@app.get("/api/v1/items/{item_code}", response_model=ItemRead)
def get_item(item_code: str, db=Depends(get_db)):
    item = db.query(Item).filter(Item.item_code == item_code, Item.is_active == True).first()
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
    return db.query(Customer).filter(Customer.is_active == True).all()


@app.get("/api/v1/customers/{customer_id}", response_model=CustomerRead)
def get_customer(customer_id: str, db=Depends(get_db)):
    c = db.query(Customer).filter(Customer.customer_id == customer_id, Customer.is_active == True).first()
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


@app.get("/api/v1/po/count")
def po_count(db=Depends(get_db)):
    return {"count": db.query(PurchaseOrder).count()}


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


@app.get("/api/v1/so/count")
def so_count(db=Depends(get_db)):
    return {"count": db.query(SalesOrder).count()}


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
    item = db.query(Item).filter(Item.item_code == req.item_code, Item.is_active == True).first()
    if not item:
        raise HTTPException(404, f"料號 {req.item_code} 不存在")

    check_id = gen_id("ATP")
    now = datetime.utcnow()
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
    item = db.query(Item).filter(Item.item_code == req.item_code, Item.is_active == True).first()
    if not item:
        raise HTTPException(404, f"料號 {req.item_code} 不存在")

    check_id = gen_id("CTP")
    now = datetime.utcnow()
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
# 6. Shipping（出貨）
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
    )
    db.add(shipping)
    db.commit()
    db.refresh(shipping)
    return shipping


@app.get("/api/v1/shipping", response_model=list[ShippingRead])
def list_shippings(db=Depends(get_db)):
    return db.query(Shipping).all()


@app.get("/api/v1/shipping/count")
def shipping_count(db=Depends(get_db)):
    return {"count": db.query(Shipping).count()}


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
    s.status = ShippingStatus.SHIPPED
    s.tracking_no = tracking_no or gen_id("TRK")
    db.commit()
    db.refresh(s)
    return s


# ════════════════════════════════════════════════════════════════════════════
# 7. Invoice（發票）
# ════════════════════════════════════════════════════════════════════════════

@app.post("/api/v1/invoice/create", response_model=InvoiceRead)
def create_invoice(data: InvoiceCreate, db=Depends(get_db)):
    so = db.query(SalesOrder).filter(SalesOrder.so_id == data.so_id).first()
    if not so:
        raise HTTPException(404, f"SO {data.so_id} 不存在")
    if db.query(Invoice).filter(Invoice.invoice_id == data.invoice_id).first():
        raise HTTPException(400, f"發票 {data.invoice_id} 已存在")

    invoice = Invoice(
        invoice_id=data.invoice_id,
        shipping_id=data.shipping_id,
        so_id=data.so_id,
        amount=data.amount,
        issue_date=datetime.utcnow(),
        status=InvoiceStatus.ISSUED,
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice


@app.get("/api/v1/invoice", response_model=list[InvoiceRead])
def list_invoices(db=Depends(get_db)):
    return db.query(Invoice).all()


@app.get("/api/v1/invoice/count")
def invoice_count(db=Depends(get_db)):
    return {"count": db.query(Invoice).count()}


@app.get("/api/v1/invoice/{invoice_id}", response_model=InvoiceRead)


# ════════════════════════════════════════════════════════════════════════════
# 8. Logistics（物流）
# ════════════════════════════════════════════════════════════════════════════

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
    )
    db.add(logistics)
    db.commit()
    db.refresh(logistics)
    return logistics


@app.get("/api/v1/logistics", response_model=list[LogisticsRead])
def list_logistics(db=Depends(get_db)):
    return db.query(Logistics).all()


@app.get("/api/v1/logistics/count")
def logistics_count(db=Depends(get_db)):
    return {"count": db.query(Logistics).count()}


@app.get("/api/v1/logistics/{tracking_no}", response_model=LogisticsRead)


@app.post("/api/v1/logistics/{tracking_no}/arrive", response_model=LogisticsRead)
def confirm_arrival(tracking_no: str, db=Depends(get_db)):
    lg = db.query(Logistics).filter(Logistics.tracking_no == tracking_no).first()
    if not lg:
        raise HTTPException(404, f"物流單 {tracking_no} 不存在")
    lg.status = LogisticsStatus.ARRIVED
    lg.actual_arrival = datetime.utcnow()

    shipping = db.query(Shipping).filter(Shipping.shipping_id == lg.shipping_id).first()
    if shipping:
        shipping.status = ShippingStatus.DELIVERED

    db.commit()
    db.refresh(lg)
    return lg


# ════════════════════════════════════════════════════════════════════════════
# Health & Info
# ════════════════════════════════════════════════════════════════════════════

import pathlib as _pl
_GIT_COMMIT_FILE = _pl.Path(__file__).parent / "GIT_COMMIT"
_GIT_COMMIT = _GIT_COMMIT_FILE.read_text().strip() if _GIT_COMMIT_FILE.exists() else "unknown"


@app.get("/healthz", response_model=OkResponse)
def healthz():
    return OkResponse(ok=True, message="OTD ERP Simulator is running")


@app.get("/health")
def health():
    """Standard health endpoint — status + commit hash + DB check"""
    db_ok = False
    try:
        db = next(get_db())
        db.execute(Base.metadata.tables["items"].select().limit(1))
        db_ok = True
    except Exception:
        pass
    return {
        "status": "ok" if db_ok else "degraded",
        "commit": _GIT_COMMIT,
        "db": "ok" if db_ok else "error",
        "version": "1.0.0",
    }


# ════════════════════════════════════════════════════════════════════════════
# Count Endpoints (moved inline above ID-parameter routes)
# ════════════════════════════════════════════════════════════════════════════

@app.get("/", response_model=OkResponse)
def root():
    return OkResponse(ok=True, message="OTD ERP 模擬層 — 請參閱 /docs 取得完整 API 文件")
