"""Models + schemas validation tests"""
from datetime import datetime

import pytest
from pydantic import ValidationError

from models import (
    ATPCheck,
    ATPResult,
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
    Shipping,
    ShippingAttachment,
    ShippingPackDetail,
    ShippingStatus,
    SOLine,
    SOStatus,
)
from schemas import (
    ATPRequest,
    ATPResponse,
    CustomerCreate,
    CustomerRead,
    InvoiceCreate,
    InvoiceLineCreate,
    ItemCreate,
    ItemRead,
    LogisticsCreate,
    LogisticsDepartRequest,
    OkResponse,
    POCreate,
    POLineCreate,
    POLineRead,
    PORead,
    ShippingCreate,
    ShippingPackDetailCreate,
    ShippingPackPartialRequest,
    SOCreate,
    SOLineCreate,
    SOLineRead,
    SORead,
)


class TestItemSchema:
    def test_item_create_valid(self):
        d = ItemCreate(item_code="CPU-001", description="Test", unit="PC",
                       lead_time_days=7, safety_stock=100, daily_capacity=500)
        assert d.item_code == "CPU-001"

    def test_item_create_missing_description(self):
        with pytest.raises(ValidationError):
            ItemCreate(item_code="CPU-001", unit="PC")

    def test_item_read_fields(self):
        d = ItemRead(item_code="CPU-001", description="Test", unit="PC", category="cpu",
                     lead_time_days=7, safety_stock=100, daily_capacity=500, is_active=True)
        assert d.description == "Test"
        assert d.is_active is True
        assert d.item_code == "CPU-001"


class TestCustomerSchema:
    def test_customer_create_valid(self):
        d = CustomerCreate(customer_id="C-001", name="Acme")
        assert d.customer_id == "C-001"

    def test_customer_create_missing_name(self):
        with pytest.raises(ValidationError):
            CustomerCreate(customer_id="C-001")


class TestPOSchema:
    def test_po_create_valid(self):
        d = POCreate(
            po_id="PO-001",
            customer_id="C-001",
            lines=[POLineCreate(item_code="CPU-001", qty=10, unit_price=99.0, line_no=1)]
        )
        assert len(d.lines) == 1

    def test_po_create_minimal(self):
        # lines with default blank list is acceptable
        d = POCreate(po_id="PO-001", customer_id="C-001")
        assert d.po_id == "PO-001"
        assert d.lines == []


class TestSOSchema:
    def test_so_create_valid(self):
        d = SOCreate(
            so_id="SO-001",
            customer_id="C-001",
            lines=[SOLineCreate(item_code="CPU-001", qty=5, unit_price=99.0, line_no=1)]
        )
        assert d.so_id == "SO-001"

    def test_so_read_fields(self):
        import datetime as dt
        d = SORead(so_id="SO-001", customer_id="C-001", status=SOStatus.DRAFT,
                   so_date=dt.datetime(2026, 5, 24), po_id=None, remarks=None)
        assert d.status == SOStatus.DRAFT
        assert d.po_id is None


class TestATPCTPSchema:
    def test_atp_request_valid(self):
        d = ATPRequest(item_code="CPU-001", qty=10, request_date="2026-06-01T00:00:00")
        assert d.qty == 10

    def test_atp_request_missing_qty(self):
        with pytest.raises(ValidationError):
            ATPRequest(item_code="CPU-001", request_date="2026-06-01T00:00:00")


class TestModelEnums:
    def test_po_status_values(self):
        assert POStatus.PENDING.value == "pending"
        assert POStatus.CONVERTED.value == "converted"
        assert POStatus.CANCELLED.value == "cancelled"

    def test_so_status_values(self):
        assert SOStatus.DRAFT.value == "draft"
        assert SOStatus.CONFIRMED.value == "confirmed"
        assert SOStatus.COMPLETED.value == "completed"

    def test_shipping_status_values(self):
        assert ShippingStatus.PENDING.value == "pending"
        assert ShippingStatus.PACKING.value == "packing"
        assert ShippingStatus.PACKED.value == "packed"
        assert ShippingStatus.SHIPPED.value == "shipped"
        assert ShippingStatus.DELIVERED.value == "delivered"

    def test_invoice_status_values(self):
        assert InvoiceStatus.DRAFT.value == "draft"
        assert InvoiceStatus.ISSUED.value == "issued"
        assert InvoiceStatus.SENT.value == "sent"
        assert InvoiceStatus.PAID.value == "paid"
        assert InvoiceStatus.VOID.value == "void"

    def test_logistics_status_values(self):
        assert LogisticsStatus.BOOKED.value == "booked"
        assert LogisticsStatus.IN_TRANSIT.value == "in_transit"
        assert LogisticsStatus.DELIVERED.value == "delivered"


class TestOkResponse:
    def test_ok_response(self):
        d = OkResponse(ok=True, message="hello")
        assert d.ok is True
        assert d.message == "hello"


class TestShippingSchema:
    def test_shipping_create_valid(self):
        d = ShippingCreate(shipping_id="SH-001", so_id="SO-001", pallet_count=2, container_type="20GP")
        assert d.shipping_id == "SH-001"

    def test_pack_detail_create(self):
        d = ShippingPackDetailCreate(pallet_no=1, line_no=1, item_code="CPU-001", qty_packed=5)
        assert d.qty_packed == 5

    def test_pack_partial_request(self):
        d = ShippingPackPartialRequest(pallet_no=1, line_no=1, item_code="CPU-001", qty_packed=3)
        assert d.qty_packed == 3


class TestInvoiceSchema:
    def test_invoice_create_valid(self):
        d = InvoiceCreate(
            invoice_id="INV-001", so_id="SO-001", amount=1000.0,
            lines=[InvoiceLineCreate(line_no=1, item_code="CPU-001", description="CPU", qty=1.0, unit_price=1000.0)]
        )
        assert d.amount == 1000.0

    def test_invoice_create_defaults(self):
        d = InvoiceCreate(invoice_id="INV-001", so_id="SO-001", amount=0.0)
        assert d.currency == "USD"
        assert d.invoice_type == "tax"


class TestLogisticsSchema:
    def test_logistics_create_valid(self):
        d = LogisticsCreate(
            tracking_no="TRK-001", shipping_id="SH-001", carrier="DHL",
            eta="2026-06-15T00:00:00", origin_port="KHH", dest_port="LAX"
        )
        assert d.carrier == "DHL"

    def test_logistics_depart_request(self):
        d = LogisticsDepartRequest(departure_date="2026-06-10T00:00:00", vessel_flight="EVA-123")
        assert d.vessel_flight == "EVA-123"


class TestModelDefaults:
    def test_item_defaults(self):
        item = Item(item_code="CODE", description="Desc", unit="PC",
                    lead_time_days=7, safety_stock=100, daily_capacity=500, is_active=True)
        assert item.unit == "PC"
        assert item.is_active is True

    def test_customer_defaults(self):
        c = Customer(customer_id="C", name="N", terms="Net30", is_active=True)
        assert c.terms == "Net30"
        assert c.is_active is True

    def test_po_defaults(self):
        # 只測 constructor 接受的值，default 由 DB column default 設定
        po = PurchaseOrder(po_id="P", customer_id="C", status=POStatus.PENDING)
        assert po.po_id == "P"
        assert po.customer_id == "C"

    def test_so_defaults(self):
        so = SalesOrder(so_id="S", customer_id="C", status=SOStatus.DRAFT)
        assert so.so_id == "S"

    def test_shipping_id_field(self):
        s = Shipping(shipping_id="SH")
        assert s.shipping_id == "SH"

    def test_invoice_id_field(self):
        inv = Invoice(invoice_id="INV", so_id="SO", amount=100.0)
        assert inv.amount == 100.0

    def test_logistics_tracking_no_field(self):
        lg = Logistics(tracking_no="T", shipping_id="S")
        assert lg.tracking_no == "T"

    def test_atp_result_string(self):
        # (str, enum.Enum) — value is the string, name is the key
        assert ATPResult.ON_TIME.value == "on_time"
        assert ATPResult.ON_TIME == "on_time"
