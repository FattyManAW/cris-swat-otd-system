"""main.py (root) 完整 OTD lifecycle 測試 — TestClient (不需要真實 HTTP)"""
from datetime import datetime, timedelta

import pytest


class TestMainAppHealth:
    def test_healthz(self, client):
        r = client.get("/healthz")
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_root(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_health(self, client):
        # erp_sim/main.py only has /healthz, not /health
        r = client.get("/healthz")
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_swagger_ui(self, client):
        r = client.get("/docs")
        assert r.status_code in (200, 301, 302)

    def test_openapi_json(self, client):
        r = client.get("/openapi.json")
        assert r.status_code == 200
        schema = r.json()
        assert "openapi" in schema
        assert "paths" in schema


class TestMainItemCRUD:
    """main.py 的 item 操作"""

    def test_create_and_list(self, client):
        r = client.post("/api/v1/items", json={
            "item_code": "CPU-MAIN",
            "description": "Main CPU",
            "unit": "PC",
            "lead_time_days": 7,
            "safety_stock": 200,
            "daily_capacity": 1000,
        })
        assert r.status_code == 200
        assert r.json()["item_code"] == "CPU-MAIN"

        r = client.get("/api/v1/items")
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_get_item_not_found(self, client):
        r = client.get("/api/v1/items/NONEXIST")
        assert r.status_code == 404


class TestOrderLifecycle:
    """完整 OTD 流程: item → customer → po → so → shipping → invoice → logistics"""

    def test_full_otd_lifecycle(self, client):
        # 1. Item
        r = client.post("/api/v1/items", json={
            "item_code": "CPU-X1", "description": "旗艦 CPU", "unit": "PC",
            "lead_time_days": 5, "safety_stock": 100, "daily_capacity": 500,
        })
        assert r.status_code == 200

        # 2. Customer
        r = client.post("/api/v1/customers", json={
            "customer_id": "CUST-X1", "name": "重要客戶", "terms": "Net30",
        })
        assert r.status_code == 200

        # 3. PO
        r = client.post("/api/v1/po", json={
            "po_id": "PO-X1",
            "customer_id": "CUST-X1",
            "lines": [
                {"item_code": "CPU-X1", "qty": 100, "unit_price": 500.0, "line_no": 1},
            ]
        })
        assert r.status_code == 200

        # 4. ATP
        r = client.post("/api/v1/atp/check", json={
            "item_code": "CPU-X1", "qty": 100, "request_date": "2026-06-01T00:00:00",
        })
        assert r.status_code == 200
        assert r.json()["result"] == "on_time"

        # 5. CTP
        r = client.post("/api/v1/ctp/check", json={
            "item_code": "CPU-X1", "qty": 100, "request_date": "2026-06-01T00:00:00",
        })
        assert r.status_code == 200
        assert r.json()["result"] == "on_time"

        # 6. PO → SO
        r = client.post("/api/v1/po/PO-X1/convert")
        assert r.status_code == 200
        so_id = r.json()["so_id"]

        # 7. Confirm SO
        r = client.patch(f"/api/v1/so/{so_id}", params={"status": "confirmed"})
        assert r.status_code == 200

        # 8. Shipping
        r = client.post("/api/v1/shipping/create", json={
            "shipping_id": "SH-X1", "so_id": so_id, "pallet_count": 2, "container_type": "40HQ",
        })
        assert r.status_code == 200

        # 9. Pack detail
        r = client.patch("/api/v1/shipping/SH-X1/pack_detail", json=[
            {"pallet_no": 1, "line_no": 1, "item_code": "CPU-X1", "qty_packed": 50, "qty_shipped": 50,
             "weight_kg": 25.0, "dimensions_cm": "120x80x60"},
            {"pallet_no": 2, "line_no": 1, "item_code": "CPU-X1", "qty_packed": 50, "qty_shipped": 50,
             "weight_kg": 25.0, "dimensions_cm": "120x80x60"},
        ])
        assert r.status_code == 200

        # 10. Ship
        r = client.patch("/api/v1/shipping/SH-X1/ship?tracking_no=TRK-X1")
        assert r.status_code == 200
        assert r.json()["status"] == "shipped"

        # 11. Invoice
        r = client.post("/api/v1/invoice/create", json={
            "invoice_id": "INV-X1", "so_id": so_id,
            "amount": 52500.0, "tax_amount": 2500.0, "currency": "USD",
            "due_date": "2026-07-30T00:00:00",
            "lines": [
                {"line_no": 1, "item_code": "CPU-X1", "description": "旗艦 CPU", "qty": 100.0, "unit_price": 500.0, "amount": 50000.0},
            ],
        })
        assert r.status_code == 200

        # life: issue → send → payment
        r = client.patch("/api/v1/invoice/INV-X1/issue", json={"invoice_no": "TAX-X1"})
        assert r.status_code == 200
        r = client.post("/api/v1/invoice/INV-X1/send")
        assert r.status_code == 200
        r = client.post("/api/v1/invoice/INV-X1/payment", json={"payment_ref": "PAY-X1"})
        assert r.status_code == 200
        assert r.json()["status"] == "paid"

        # 12. Logistics
        r = client.post("/api/v1/logistics/arrange", json={
            "tracking_no": "TRK-X1", "shipping_id": "SH-X1",
            "carrier": "EVA AIR", "eta": "2026-07-15T00:00:00",
            "origin_port": "KHH", "dest_port": "LAX",
            "vessel_flight": "BR-612", "bl_number": "BL-X1",
        })
        assert r.status_code == 200

        # depart → customs → arrive → deliver
        r = client.post("/api/v1/logistics/TRK-X1/depart")
        assert r.status_code == 200
        r = client.post("/api/v1/logistics/TRK-X1/customs", json={"customs_status": "cleared"})
        assert r.status_code == 200
        r = client.post("/api/v1/logistics/TRK-X1/customs_clear")
        assert r.status_code == 200
        r = client.post("/api/v1/logistics/TRK-X1/deliver_sign", json={
            "signed_by": "李四", "is_final": True, "delivery_note": "已驗收簽收",
        })
        assert r.status_code == 200
        assert r.json()["status"] == "delivered"

        # 最終 SO 狀態檢查
        r = client.get(f"/api/v1/so/{so_id}")
        assert r.status_code == 200
        assert r.json()["status"] == "completed"

        # Verify events log
        r = client.get("/api/v1/logistics/TRK-X1/events")
        assert r.status_code == 200
        events = r.json()
        assert len(events) >= 5  # booked + in_transit(depart) + customs + in_transit(clear) + delivered


class TestMainSOCRUD:
    """main.py 直接的 SO CRUD"""

    def test_so_lifecycle(self, client):
        # seed item + customer
        client.post("/api/v1/items", json={
            "item_code": "CPU-SO", "description": "SO CPU", "unit": "PC",
            "lead_time_days": 3, "safety_stock": 50, "daily_capacity": 200,
        })
        client.post("/api/v1/customers", json={
            "customer_id": "CUST-SO", "name": "SO 客戶",
        })

        # create PO
        client.post("/api/v1/po", json={
            "po_id": "PO-SO", "customer_id": "CUST-SO",
            "lines": [{"item_code": "CPU-SO", "qty": 20, "unit_price": 200.0, "line_no": 1}],
        })

        # PO → SO
        r = client.post("/api/v1/po/PO-SO/convert")
        assert r.status_code == 200
        so_id = r.json()["so_id"]

        # confirm
        r = client.patch(f"/api/v1/so/{so_id}", params={"status": "confirmed"})
        assert r.status_code == 200
        assert r.json()["status"] == "confirmed"

        # list SOs
        r = client.get("/api/v1/so")
        assert r.status_code == 200
        assert len(r.json()) >= 1

        # get SO lines
        r = client.get(f"/api/v1/so/{so_id}/lines")
        assert r.status_code == 200
        assert len(r.json()) == 1

    def test_cancel_po(self, client):
        """Verify cancelled PO can't be converted"""
        client.post("/api/v1/items", json={
            "item_code": "CPU-CN", "description": "Cancel CPU", "unit": "PC",
        })
        client.post("/api/v1/customers", json={
            "customer_id": "CUST-CN", "name": "Cancel 客戶",
        })
        client.post("/api/v1/po", json={
            "po_id": "PO-CN", "customer_id": "CUST-CN",
            "lines": [{"item_code": "CPU-CN", "qty": 1, "unit_price": 1.0, "line_no": 1}],
        })
        r = client.post("/api/v1/po/PO-CN/convert")
        assert r.status_code == 200

        r = client.post("/api/v1/po/PO-CN/convert")
        assert r.status_code == 400
        assert "已轉換" in r.json()["detail"]

    def test_convert_cancelled_po(self, client):
        """L239-240: cancelled PO → convert 400"""
        # Create PO → convert to SO → we only test that CANCELLED status blocks convert
        # The app doesn't have a cancel-PO endpoint, so we test through direct DB
        # Test via the update_so 404 path: convert a non-existent PO
        client.post("/api/v1/items", json={
            "item_code": "CPU-CC2", "description": "Cancelled PO CPU", "unit": "PC",
        })
        client.post("/api/v1/customers", json={
            "customer_id": "CUST-CC2", "name": "Cancelled PO 客戶",
        })
        client.post("/api/v1/po", json={
            "po_id": "PO-CC2", "customer_id": "CUST-CC2",
            "lines": [{"item_code": "CPU-CC2", "qty": 1, "unit_price": 1.0, "line_no": 1}],
        })
        # The app doesn't expose a cancel-PO PATCH, but we can test the CANCELLED guard
        # via SQLAlchemy direct: set status to CANCELLED, then try convert
        from erp_sim.models import POStatus, PurchaseOrder
        from erp_sim.models import SessionLocal as SL
        db = SL()
        try:
            po = db.query(PurchaseOrder).filter(PurchaseOrder.po_id == "PO-CC2").first()
            if po:
                po.status = POStatus.CANCELLED
                db.commit()
        finally:
            db.close()
        r = client.post("/api/v1/po/PO-CC2/convert")
        assert r.status_code == 400
        assert "已取消" in r.json()["detail"]


# ════════════════════════════════════════════════════════════════════════════
# Negative-path / edge-case coverage — targets main.py 85% → 95%+
# ════════════════════════════════════════════════════════════════════════════

class TestPOEdgeCases:
    """Cover PO 404 / duplicate / bad-status paths"""

    def test_po_lines_not_found(self, client):
        """L206: get_po_lines with non-existent PO"""
        r = client.get("/api/v1/po/NONEXIST/lines")
        assert r.status_code == 404

    def test_create_po_duplicate(self, client, seed_item, seed_customer):
        """L213: create_po duplicate"""
        client.post("/api/v1/po", json={
            "po_id": "PO-DUP", "customer_id": "CUST-001",
            "lines": [{"item_code": "CPU-001", "qty": 1, "unit_price": 1.0, "line_no": 1}],
        })
        r = client.post("/api/v1/po", json={
            "po_id": "PO-DUP", "customer_id": "CUST-001",
            "lines": [{"item_code": "CPU-001", "qty": 1, "unit_price": 1.0, "line_no": 1}],
        })
        assert r.status_code == 400

    def test_convert_po_not_found(self, client):
        """L245: convert non-existent PO"""
        r = client.post("/api/v1/po/NONEXIST/convert")
        assert r.status_code == 404

    def test_convert_already_converted(self, client, seed_item, seed_customer):
        """L249: convert already-converted PO"""
        client.post("/api/v1/po", json={
            "po_id": "PO-CONV", "customer_id": "CUST-001",
            "lines": [{"item_code": "CPU-001", "qty": 5, "unit_price": 10.0, "line_no": 1}],
        })
        client.post("/api/v1/po/PO-CONV/convert")
        r = client.post("/api/v1/po/PO-CONV/convert")
        assert r.status_code == 400
        assert "已轉換" in r.json()["detail"]


class TestSOEdgeCases:
    """Cover SO 404 / duplicate / bad-item paths"""

    def test_so_not_found(self, client):
        """L296: get_so 404"""
        r = client.get("/api/v1/so/NONEXIST")
        assert r.status_code == 404

    def test_create_so_duplicate(self, client, seed_item, seed_customer):
        """L303: create_so duplicate"""
        client.post("/api/v1/so", json={
            "so_id": "SO-DUP", "customer_id": "CUST-001",
            "lines": [{"item_code": "CPU-001", "qty": 5, "unit_price": 10.0, "line_no": 1}],
        })
        r = client.post("/api/v1/so", json={
            "so_id": "SO-DUP", "customer_id": "CUST-001",
            "lines": [{"item_code": "CPU-001", "qty": 5, "unit_price": 10.0, "line_no": 1}],
        })
        assert r.status_code == 400

    def test_create_so_bad_item(self, client, seed_customer):
        """L320: create_so with non-existent item"""
        r = client.post("/api/v1/so", json={
            "so_id": "SO-BADITEM", "customer_id": "CUST-001",
            "lines": [{"item_code": "NOEXIST", "qty": 1, "unit_price": 1.0, "line_no": 1}],
        })
        assert r.status_code == 400

    def test_so_lines_not_found(self, client):
        """L345: get_so_lines 404"""
        r = client.get("/api/v1/so/NONEXIST/lines")
        assert r.status_code == 404


class TestATPCoverage:
    """Cover force_insufficient + item-not-found ATP/CTP paths"""

    def test_atp_force_insufficient(self, client, seed_item):
        """L376: ATP force_insufficient"""
        r = client.post("/api/v1/atp/check?force_insufficient=true", json={
            "item_code": "CPU-001", "qty": 100, "request_date": "2026-06-01T00:00:00",
        })
        assert r.status_code == 200
        assert r.json()["result"] == "insufficient"

    def test_atp_force_delay(self, client, seed_item):
        """ATP force_delay"""
        r = client.post("/api/v1/atp/check?force_delay=true", json={
            "item_code": "CPU-001", "qty": 100, "request_date": "2026-06-01T00:00:00",
        })
        assert r.status_code == 200
        assert r.json()["result"] == "delayed"

    def test_atp_item_not_found(self, client):
        """L424: ATP with non-existent item"""
        r = client.post("/api/v1/atp/check", json={
            "item_code": "NONEXIST", "qty": 10, "request_date": "2026-06-01T00:00:00",
        })
        assert r.status_code == 404

    def test_ctp_force_insufficient(self, client, seed_item):
        """L436: CTP force_insufficient"""
        r = client.post("/api/v1/ctp/check?force_insufficient=true", json={
            "item_code": "CPU-001", "qty": 100, "request_date": "2026-06-01T00:00:00",
        })
        assert r.status_code == 200
        assert r.json()["result"] == "insufficient"

    def test_ctp_force_delay(self, client, seed_item):
        """CTP force_delay"""
        r = client.post("/api/v1/ctp/check?force_delay=true", json={
            "item_code": "CPU-001", "qty": 100, "request_date": "2026-06-01T00:00:00",
        })
        assert r.status_code == 200
        assert r.json()["result"] == "delayed"

    def test_ctp_item_not_found(self, client):
        """CTP with non-existent item"""
        r = client.post("/api/v1/ctp/check", json={
            "item_code": "NONEXIST", "qty": 10, "request_date": "2026-06-01T00:00:00",
        })
        assert r.status_code == 404


class TestShippingEdgeCases:
    """Cover all shipping 404/400 and remaining paths"""

    @pytest.fixture(autouse=True)
    def setup(self, client, seed_item, seed_customer, seed_po):
        r = client.post("/api/v1/po/PO-20260524-001/convert")
        self.so_id = r.json()["so_id"]
        client.patch(f"/api/v1/so/{self.so_id}", params={"status": "confirmed"})

    def test_get_shipping_not_found(self, client):
        """L508: get_shipping 404"""
        r = client.get("/api/v1/shipping/NONEXIST")
        assert r.status_code == 404

    def test_pack_not_found(self, client):
        """L530: pack 404"""
        r = client.patch("/api/v1/shipping/NONEXIST/pack?pallet_count=1")
        assert r.status_code == 404

    def test_pack_wrong_status(self, client):
        """L532: pack when already shipped"""
        client.post("/api/v1/shipping/create", json={
            "shipping_id": "SH-PACKBAD", "so_id": self.so_id, "pallet_count": 1, "container_type": "20GP",
        })
        client.patch("/api/v1/shipping/SH-PACKBAD/pack?pallet_count=1")
        # second pack on already-packing should fail
        r = client.patch("/api/v1/shipping/SH-PACKBAD/pack?pallet_count=2")
        assert r.status_code == 400

    def test_ship_not_found(self, client):
        """L550: ship 404"""
        r = client.patch("/api/v1/shipping/NONEXIST/ship")
        assert r.status_code == 404

    def test_ship_wrong_status(self, client):
        """L552: ship when not yet packed"""
        client.post("/api/v1/shipping/create", json={
            "shipping_id": "SH-SHIPBAD", "so_id": self.so_id, "pallet_count": 1, "container_type": "20GP",
        })
        r = client.patch("/api/v1/shipping/SH-SHIPBAD/ship")
        assert r.status_code == 400

    def test_pack_detail_not_found(self, client):
        """L582: pack_detail 404"""
        r = client.patch("/api/v1/shipping/NONEXIST/pack_detail", json=[])
        assert r.status_code == 404

    def test_pack_detail_wrong_status(self, client):
        """L590: pack_detail when already shipped"""
        client.post("/api/v1/shipping/create", json={
            "shipping_id": "SH-PDBAD", "so_id": self.so_id, "pallet_count": 1, "container_type": "20GP",
        })
        client.patch("/api/v1/shipping/SH-PDBAD/pack?pallet_count=1")
        client.patch("/api/v1/shipping/SH-PDBAD/ship")
        r = client.patch("/api/v1/shipping/SH-PDBAD/pack_detail", json=[
            {"pallet_no": 1, "line_no": 1, "item_code": "CPU-001", "qty_packed": 1, "qty_shipped": 1, "weight_kg": 1.0, "dimensions_cm": "1x1x1"},
        ])
        assert r.status_code == 400

    def test_get_pack_detail_not_found(self, client):
        """L601: get_pack_detail 404"""
        r = client.get("/api/v1/shipping/NONEXIST/pack_detail")
        assert r.status_code == 404

    def test_shipping_lines_not_found(self, client):
        """L603: get_shipping_lines 404"""
        r = client.get("/api/v1/shipping/NONEXIST/lines")
        assert r.status_code == 404

    def test_pack_partial_not_found(self, client):
        """L630: pack_partial 404"""
        r = client.patch("/api/v1/shipping/NONEXIST/pack_partial", json=[])
        assert r.status_code == 404

    def test_pack_partial_wrong_status(self, client):
        """L632: pack_partial when already shipped"""
        client.post("/api/v1/shipping/create", json={
            "shipping_id": "SH-PPBAD", "so_id": self.so_id, "pallet_count": 1, "container_type": "20GP",
        })
        client.patch("/api/v1/shipping/SH-PPBAD/pack?pallet_count=1")
        client.patch("/api/v1/shipping/SH-PPBAD/ship")
        r = client.patch("/api/v1/shipping/SH-PPBAD/pack_partial", json=[
            {"pallet_no": 1, "line_no": 1, "item_code": "CPU-001", "qty_packed": 1, "weight_kg": 1.0, "dimensions_cm": "1x1x1"},
        ])
        assert r.status_code == 400

    def test_partial_ship_success_and_404(self, client):
        """L649-662: partial_ship success + 404"""
        client.post("/api/v1/shipping/create", json={
            "shipping_id": "SH-PS2", "so_id": self.so_id, "pallet_count": 0, "container_type": "20GP",
        })
        client.patch("/api/v1/shipping/SH-PS2/pack_partial", json=[
            {"pallet_no": 1, "line_no": 1, "item_code": "CPU-001", "qty_packed": 3, "weight_kg": 5.0, "dimensions_cm": "50x30x30"},
        ])
        r = client.patch("/api/v1/shipping/SH-PS2/partial_ship", json={
            "remaining_qty": 7, "remarks": "分兩批出",
        })
        assert r.status_code == 200
        assert r.json()["status"] == "shipped"
        assert r.json()["partial_delivery"] is True

        # 404
        r = client.patch("/api/v1/shipping/NONEXIST/partial_ship", json={"remaining_qty": 0})
        assert r.status_code == 404

    def test_partial_deliver_success_and_errors(self, client):
        """L671/673: partial_deliver 404/400 + success"""
        client.post("/api/v1/shipping/create", json={
            "shipping_id": "SH-PDEL", "so_id": self.so_id, "pallet_count": 1, "container_type": "20GP",
        })
        client.patch("/api/v1/shipping/SH-PDEL/pack?pallet_count=1")
        client.patch("/api/v1/shipping/SH-PDEL/ship")
        r = client.patch("/api/v1/shipping/SH-PDEL/partial_deliver", json={
            "delivered_qty": 5, "remaining_qty": 5, "delivery_proof_url": "https://a.com/pod",
            "is_delivery_signed": False, "remarks": "部分到貨",
        })
        assert r.status_code == 200
        assert r.json()["status"] == "partial_delivery"

        # 404
        r = client.patch("/api/v1/shipping/NONEXIST/partial_deliver", json={"delivered_qty": 0, "remaining_qty": 0, "is_delivery_signed": False})
        assert r.status_code == 404

        # 400 — try on pending
        client.post("/api/v1/shipping/create", json={
            "shipping_id": "SH-PDEL2", "so_id": self.so_id, "pallet_count": 1, "container_type": "20GP",
        })
        r = client.patch("/api/v1/shipping/SH-PDEL2/partial_deliver", json={"delivered_qty": 0, "remaining_qty": 0, "is_delivery_signed": False})
        assert r.status_code == 400

    def test_deliver_not_found(self, client):
        """L700: deliver 404"""
        r = client.patch("/api/v1/shipping/NONEXIST/deliver")
        assert r.status_code == 404

    def test_deliver_wrong_status(self, client):
        """L702: deliver when not yet shipped"""
        client.post("/api/v1/shipping/create", json={
            "shipping_id": "SH-DELBAD", "so_id": self.so_id, "pallet_count": 1, "container_type": "20GP",
        })
        r = client.patch("/api/v1/shipping/SH-DELBAD/deliver")
        assert r.status_code == 400

    def test_attach_duplicate(self, client):
        """L702: attachment duplicate"""
        client.post("/api/v1/shipping/create", json={
            "shipping_id": "SH-ATDUP", "so_id": self.so_id, "pallet_count": 1, "container_type": "20GP",
        })
        client.post("/api/v1/shipping/SH-ATDUP/attach", json={
            "attachment_id": "ATT-DUP", "type": "pod", "filename": "a.pdf", "url": "http://a", "uploaded_by": "x",
        })
        r = client.post("/api/v1/shipping/SH-ATDUP/attach", json={
            "attachment_id": "ATT-DUP", "type": "pod", "filename": "a.pdf", "url": "http://a", "uploaded_by": "x",
        })
        assert r.status_code == 400

    def test_partial_ship_wrong_status(self, client):
        """L623: partial_ship 400 when status is PENDING"""
        client.post("/api/v1/shipping/create", json={
            "shipping_id": "SH-PSBAD", "so_id": self.so_id, "pallet_count": 0, "container_type": "20GP",
        })
        # Status is PENDING, partial_ship should return 400
        r = client.patch("/api/v1/shipping/SH-PSBAD/partial_ship", json={
            "remaining_qty": 0, "remarks": "test",
        })
        assert r.status_code == 400
        assert "狀態為" in r.json()["detail"]

    def test_attach_shipping_not_found(self, client):
        """L691: attach_shipping_doc 404 for non-existent shipping"""
        r = client.post("/api/v1/shipping/NONEXIST/attach", json={
            "attachment_id": "ATT-404X", "type": "pod", "filename": "test.pdf",
            "url": "https://example.com/test.pdf",
        })
        assert r.status_code == 404

    def test_attachments_not_found(self, client):
        """L722: get_attachments 404"""
        r = client.get("/api/v1/shipping/NONEXIST/attachments")
        assert r.status_code == 404


class TestInvoiceEdgeCases:
    """Cover invoice 404/400/various paths"""

    @pytest.fixture(autouse=True)
    def setup(self, client, seed_item, seed_customer, seed_po):
        r = client.post("/api/v1/po/PO-20260524-001/convert")
        self.so_id = r.json()["so_id"]
        client.patch(f"/api/v1/so/{self.so_id}", params={"status": "confirmed"})

    def _create_draft(self, client, inv_id):
        client.post("/api/v1/invoice/create", json={
            "invoice_id": inv_id, "so_id": self.so_id,
            "amount": 1000.0, "lines": [
                {"line_no": 1, "item_code": "CPU-001", "description": "CPU", "qty": 1.0, "unit_price": 1000.0}
            ],
        })

    def test_create_invoice_duplicate(self, client):
        """L736: invoice duplicate"""
        self._create_draft(client, "INV-DUP")
        r = client.post("/api/v1/invoice/create", json={
            "invoice_id": "INV-DUP", "so_id": self.so_id, "amount": 100.0,
        })
        assert r.status_code == 400

    def test_get_invoices_by_so_not_found(self, client):
        """L780: get_invoices_by_so 404"""
        r = client.get("/api/v1/invoice/by_so/NONEXIST")
        assert r.status_code == 404

    def test_overdue_invoices(self, client):
        """L790-805: overdue invoices — create invoices with past due dates and verify they become overdue"""
        # Create and issue+send an invoice with a past due_date so it's overdue
        r = client.post("/api/v1/invoice/create", json={
            "invoice_id": "INV-OD1", "so_id": self.so_id,
            "amount": 2000.0, "currency": "USD",
            "due_date": "2020-01-01T00:00:00",  # way past
            "lines": [
                {"line_no": 1, "item_code": "CPU-001", "description": "CPU", "qty": 2.0, "unit_price": 1000.0},
            ],
        })
        assert r.status_code == 200
        client.patch("/api/v1/invoice/INV-OD1/issue")
        client.post("/api/v1/invoice/INV-OD1/send")

        # Query overdue — should find INV-OD1 and auto-mark as overdue
        r = client.get("/api/v1/invoice/overdue?days_overdue=1")
        assert r.status_code == 200
        overdue = r.json()
        assert len(overdue) >= 1
        assert any(inv["invoice_id"] == "INV-OD1" for inv in overdue)

        # Verify INV-OD1 is now overdue
        r = client.get("/api/v1/invoice/INV-OD1")
        assert r.status_code == 200
        assert r.json()["status"] == "overdue"

        # Query without dunning
        r = client.get("/api/v1/invoice/overdue?include_dunning=false")
        assert r.status_code == 200

    def test_get_invoice_not_found(self, client):
        """L810-813: get_invoice 404"""
        r = client.get("/api/v1/invoice/NONEXIST")
        assert r.status_code == 404

    def test_issue_not_found(self, client):
        """L820: issue 404"""
        r = client.patch("/api/v1/invoice/NONEXIST/issue")
        assert r.status_code == 404

    def test_issue_wrong_status(self, client):
        """L822: issue when not draft"""
        self._create_draft(client, "INV-ISBAD")
        client.patch("/api/v1/invoice/INV-ISBAD/issue")
        r = client.patch("/api/v1/invoice/INV-ISBAD/issue")
        assert r.status_code == 400

    def test_send_not_found(self, client):
        """L838: send 404"""
        r = client.post("/api/v1/invoice/NONEXIST/send")
        assert r.status_code == 404

    def test_send_wrong_status(self, client):
        """L840: send when not issued"""
        self._create_draft(client, "INV-SDBAD")
        r = client.post("/api/v1/invoice/INV-SDBAD/send")
        assert r.status_code == 400

    def test_payment_not_found(self, client):
        """L852: payment 404"""
        r = client.post("/api/v1/invoice/NONEXIST/payment")
        assert r.status_code == 404

    def test_payment_already_paid(self, client):
        """L854: payment when already paid"""
        self._create_draft(client, "INV-PAYBAD")
        client.patch("/api/v1/invoice/INV-PAYBAD/issue")
        client.post("/api/v1/invoice/INV-PAYBAD/send")
        client.post("/api/v1/invoice/INV-PAYBAD/payment")
        r = client.post("/api/v1/invoice/INV-PAYBAD/payment")
        assert r.status_code == 400

    def test_payment_with_date(self, client):
        """L861: payment with explicit date"""
        self._create_draft(client, "INV-PDATE")
        client.patch("/api/v1/invoice/INV-PDATE/issue")
        client.post("/api/v1/invoice/INV-PDATE/send")
        r = client.post("/api/v1/invoice/INV-PDATE/payment", json={
            "payment_ref": "PAY-REF", "payment_date": "2026-05-01T00:00:00",
        })
        assert r.status_code == 200
        assert r.json()["status"] == "paid"
        assert r.json()["payment_ref"] == "PAY-REF"

    def test_void_not_found(self, client):
        """L871: void 404"""
        r = client.patch("/api/v1/invoice/NONEXIST/void", json={"void_reason": "x"})
        assert r.status_code == 404

    def test_void_already_paid(self, client):
        """L873: void when already paid"""
        self._create_draft(client, "INV-VBAD")
        client.patch("/api/v1/invoice/INV-VBAD/issue")
        client.post("/api/v1/invoice/INV-VBAD/send")
        client.post("/api/v1/invoice/INV-VBAD/payment")
        r = client.patch("/api/v1/invoice/INV-VBAD/void", json={"void_reason": "x"})
        assert r.status_code == 400

    def test_credit_note_not_found(self, client):
        """L886: credit note 404"""
        r = client.post("/api/v1/invoice/NONEXIST/credit", json={"credit_note_for": "INV-X", "amount": 100.0})
        assert r.status_code == 404

    def test_get_invoice_lines_not_found(self, client):
        """L913: get_invoice_lines 404"""
        r = client.get("/api/v1/invoice/NONEXIST/lines")
        assert r.status_code == 404


class TestLogisticsEdgeCases:
    """Cover logistics 404/400 and remaining paths"""

    @pytest.fixture(autouse=True)
    def setup(self, client, seed_item, seed_customer, seed_po):
        r = client.post("/api/v1/po/PO-20260524-001/convert")
        self.so_id = r.json()["so_id"]
        client.patch(f"/api/v1/so/{self.so_id}", params={"status": "confirmed"})
        client.post("/api/v1/shipping/create", json={
            "shipping_id": "SH-LOG", "so_id": self.so_id, "pallet_count": 1, "container_type": "20GP",
        })

    def _arrange(self, client, tracking_no="TRK-LE1"):
        client.post("/api/v1/logistics/arrange", json={
            "tracking_no": tracking_no, "shipping_id": "SH-LOG",
            "carrier": "MAERSK", "eta": "2026-12-30T00:00:00",
            "origin_port": "KHH", "dest_port": "LAX",
            "vessel_flight": "MS-001", "bl_number": "BL-LE1",
        })

    def test_arrange_bad_shipping(self, client):
        """L940: arrange_logistics with non-existent shipping"""
        r = client.post("/api/v1/logistics/arrange", json={
            "tracking_no": "TRK-BAD", "shipping_id": "NONEXIST", "carrier": "MAERSK",
        })
        assert r.status_code == 404

    def test_arrange_duplicate(self, client):
        """L942: arrange_logistics duplicate"""
        self._arrange(client, "TRK-DUP")
        r = client.post("/api/v1/logistics/arrange", json={
            "tracking_no": "TRK-DUP", "shipping_id": "SH-LOG", "carrier": "MAERSK",
        })
        assert r.status_code == 400

    def test_get_by_shipping_not_found(self, client):
        """L973: get_logistics_by_shipping 404"""
        r = client.get("/api/v1/logistics/by_shipping/NONEXIST")
        assert r.status_code == 404

    def test_active_logistics_with_carrier(self, client):
        """L987: active logistics with carrier filter"""
        self._arrange(client, "TRK-ACTIVE")
        r = client.get("/api/v1/logistics/active?carrier=MAERSK")
        assert r.status_code == 200
        results = r.json()
        assert any(lg["tracking_no"] == "TRK-ACTIVE" for lg in results)

    def test_get_logistics_not_found(self, client):
        """L983-986: get_logistics 404"""
        r = client.get("/api/v1/logistics/NONEXIST")
        assert r.status_code == 404

    def test_get_logistics_success(self, client):
        """L987: get_logistics success (return existing logistics)"""
        self._arrange(client, "TRK-FOUND")
        r = client.get("/api/v1/logistics/TRK-FOUND")
        assert r.status_code == 200
        assert r.json()["tracking_no"] == "TRK-FOUND"
        assert r.json()["carrier"] == "MAERSK"

    def test_depart_not_found(self, client):
        """L1003: depart 404"""
        r = client.post("/api/v1/logistics/NONEXIST/depart")
        assert r.status_code == 404

    def test_depart_wrong_status(self, client):
        """L1005: depart when already in-transit"""
        self._arrange(client, "TRK-DEPBAD")
        client.post("/api/v1/logistics/TRK-DEPBAD/depart")
        r = client.post("/api/v1/logistics/TRK-DEPBAD/depart")
        assert r.status_code == 400

    def test_depart_with_full_data(self, client):
        """Depart with data payload (origin_port, note, etc.)"""
        self._arrange(client, "TRK-DEPDATA")
        r = client.post("/api/v1/logistics/TRK-DEPDATA/depart", json={
            "departure_date": "2026-05-25T12:00:00",
            "vessel_flight": "BR-999",
            "origin_port": "TPE",
            "note": "從台北出發",
        })
        assert r.status_code == 200
        assert r.json()["status"] == "in_transit"
        assert r.json()["departure_date"] is not None

    def test_customs_not_found(self, client):
        """L1029: customs 404"""
        r = client.post("/api/v1/logistics/NONEXIST/customs")
        assert r.status_code == 404

    def test_customs_wrong_status(self, client):
        """L1031: customs when already in customs"""
        self._arrange(client, "TRK-CBAD")
        client.post("/api/v1/logistics/TRK-CBAD/depart")
        client.post("/api/v1/logistics/TRK-CBAD/customs")
        r = client.post("/api/v1/logistics/TRK-CBAD/customs")
        assert r.status_code == 400

    def test_customs_no_data(self, client):
        """L1042-1043: customs without data payload"""
        self._arrange(client, "TRK-CNODATA")
        client.post("/api/v1/logistics/TRK-CNODATA/depart")
        r = client.post("/api/v1/logistics/TRK-CNODATA/customs")
        assert r.status_code == 200
        assert r.json()["status"] == "customs"

    def test_customs_hold_success_and_404(self, client):
        """L1054: customs_hold 404 + success"""
        self._arrange(client, "TRK-CH")
        r = client.post("/api/v1/logistics/TRK-CH/customs_hold", json={
            "reason": "文件不符，需補充資料",
        })
        assert r.status_code == 200
        assert r.json()["status"] == "customs_hold"

        r = client.post("/api/v1/logistics/NONEXIST/customs_hold", json={"reason": "x"})
        assert r.status_code == 404

    def test_customs_clear_not_found(self, client):
        """L1069: customs_clear 404"""
        r = client.post("/api/v1/logistics/NONEXIST/customs_clear")
        assert r.status_code == 404

    def test_customs_clear_wrong_status(self, client):
        """L1071: customs_clear when not in customs"""
        self._arrange(client, "TRK-CCBAD")
        r = client.post("/api/v1/logistics/TRK-CCBAD/customs_clear")
        assert r.status_code == 400

    def test_arrive_not_found(self, client):
        """L1087: arrive 404"""
        r = client.post("/api/v1/logistics/NONEXIST/arrive")
        assert r.status_code == 404

    def test_arrive_already_delivered(self, client):
        """L1089: arrive when already delivered (deliver_sign sets DELIVERED, then arrive blocks)"""
        self._arrange(client, "TRK-ARRBAD")
        client.post("/api/v1/logistics/TRK-ARRBAD/depart")
        client.post("/api/v1/logistics/TRK-ARRBAD/deliver_sign", json={
            "signed_by": "x", "is_final": True,
        })
        r = client.post("/api/v1/logistics/TRK-ARRBAD/arrive")
        assert r.status_code == 400

    def test_arrive_with_data(self, client):
        """L1095: arrive with data payload"""
        self._arrange(client, "TRK-ARRDATA")
        client.post("/api/v1/logistics/TRK-ARRDATA/depart")
        r = client.post("/api/v1/logistics/TRK-ARRDATA/arrive", json={
            "actual_arrival": "2026-06-01T14:00:00",
            "delivery_note": "貨物已送達倉庫",
        })
        assert r.status_code == 200
        assert r.json()["status"] == "arrived"

    def test_partial_arrive_success_and_errors(self, client):
        """L1116/1118: partial_arrive 404/400 + success"""
        self._arrange(client, "TRK-PA")
        client.post("/api/v1/logistics/TRK-PA/depart")
        r = client.post("/api/v1/logistics/TRK-PA/partial_arrive", json={
            "delivered_qty": 5, "remaining_qty": 5,
        })
        assert r.status_code == 200
        assert r.json()["status"] == "partial_delivery"

        r = client.post("/api/v1/logistics/NONEXIST/partial_arrive", json={
            "delivered_qty": 1, "remaining_qty": 1,
        })
        assert r.status_code == 404

        # 400 — already in partial_delivery → allow? Actually after partial_arrive it's partial_delivery,
        # which is not in [delivered, failed] so it should succeed again. Let's test with delivered.
        self._arrange(client, "TRK-PA2")
        client.post("/api/v1/logistics/TRK-PA2/depart")
        client.post("/api/v1/logistics/TRK-PA2/deliver_sign", json={
            "signed_by": "x", "is_final": True,
        })
        r = client.post("/api/v1/logistics/TRK-PA2/partial_arrive", json={
            "delivered_qty": 1, "remaining_qty": 1,
        })
        assert r.status_code == 400

    def test_deliver_sign_not_found(self, client):
        """L1141: deliver_sign 404"""
        r = client.post("/api/v1/logistics/NONEXIST/deliver_sign", json={
            "signed_by": "x", "is_final": True,
        })
        assert r.status_code == 404

    def test_deliver_sign_already_delivered(self, client):
        """L1143: deliver_sign already delivered"""
        self._arrange(client, "TRK-DSBAD")
        client.post("/api/v1/logistics/TRK-DSBAD/depart")
        client.post("/api/v1/logistics/TRK-DSBAD/deliver_sign", json={
            "signed_by": "x", "is_final": True,
        })
        r = client.post("/api/v1/logistics/TRK-DSBAD/deliver_sign", json={
            "signed_by": "x", "is_final": True,
        })
        assert r.status_code == 400

    def test_failed_success_and_404(self, client):
        """L1179/1181: failed 404/400 + success"""
        self._arrange(client, "TRK-FAIL")
        r = client.post("/api/v1/logistics/TRK-FAIL/failed", json={
            "reason": "貨物損壞", "note": "退回處理",
        })
        assert r.status_code == 200
        assert r.json()["status"] == "failed"

        r = client.post("/api/v1/logistics/NONEXIST/failed", json={"reason": "x"})
        assert r.status_code == 404

        # 400 — already delivered
        self._arrange(client, "TRK-FAIL2")
        client.post("/api/v1/logistics/TRK-FAIL2/depart")
        client.post("/api/v1/logistics/TRK-FAIL2/deliver_sign", json={
            "signed_by": "x", "is_final": True,
        })
        r = client.post("/api/v1/logistics/TRK-FAIL2/failed", json={"reason": "x"})
        assert r.status_code == 400

    def test_reroute_success_and_errors(self, client):
        """L1195/1197: reroute 404/400 + success"""
        self._arrange(client, "TRK-RR")
        client.post("/api/v1/logistics/TRK-RR/failed", json={"reason": "測試"})
        r = client.post("/api/v1/logistics/TRK-RR/reroute", json={
            "new_carrier": "EVA AIR", "new_eta": "2026-12-31T00:00:00", "note": "改搭其他航班",
        })
        assert r.status_code == 200
        assert r.json()["status"] == "reroute"
        assert r.json()["carrier"] == "EVA AIR"

        r = client.post("/api/v1/logistics/NONEXIST/reroute", json={"note": "x"})
        assert r.status_code == 404

        # 400 — reroute on booked status
        self._arrange(client, "TRK-RR2")
        r = client.post("/api/v1/logistics/TRK-RR2/reroute", json={"note": "x"})
        assert r.status_code == 400

    def test_write_event_manual_and_404(self, client):
        """L1217: manual event 404 + success"""
        self._arrange(client, "TRK-EV")
        r = client.post("/api/v1/logistics/TRK-EV/event", json={
            "event_id": "LEV-001",
            "status": "custom_check",
            "note": "海關抽驗",
            "location": "LAX",
            "created_by": "agent-001",
        })
        assert r.status_code == 200
        assert r.json()["status"] == "custom_check"

        r = client.post("/api/v1/logistics/NONEXIST/event", json={
            "event_id": "LEV-002", "status": "x", "note": "x",
        })
        assert r.status_code == 404

    def test_get_events_not_found(self, client):
        """L1238: get_events 404"""
        r = client.get("/api/v1/logistics/NONEXIST/events")
        assert r.status_code == 404


class TestATPCTPInsufficient:
    """Cover ATP/CTP insufficient paths (not force_*, real insufficient)"""

    def test_atp_insufficient(self, client):
        """ATP with demand > stock → insufficient"""
        client.post("/api/v1/items", json={
            "item_code": "CPU-LOW", "description": "Low stock CPU", "unit": "PC",
            "lead_time_days": 5, "safety_stock": 10, "daily_capacity": 50,
        })
        r = client.post("/api/v1/atp/check", json={
            "item_code": "CPU-LOW", "qty": 100, "request_date": "2026-06-01T00:00:00",
        })
        assert r.status_code == 200
        assert r.json()["result"] == "insufficient"

    def test_ctp_insufficient(self, client):
        """CTP with demand > capacity → insufficient"""
        client.post("/api/v1/items", json={
            "item_code": "CPU-LOW2", "description": "Low cap CPU", "unit": "PC",
            "lead_time_days": 1, "safety_stock": 5, "daily_capacity": 10,
        })
        r = client.post("/api/v1/ctp/check", json={
            "item_code": "CPU-LOW2", "qty": 100, "request_date": "2026-06-01T00:00:00",
        })
        assert r.status_code == 200
        assert r.json()["result"] == "insufficient"


class TestSoCrossCheck:
    """SO cross-check: PO customer mismatch"""

    def test_create_so_po_customer_mismatch(self, client, seed_item, seed_customer):
        """Create SO via PO with different customer → 400"""
        # Create another customer
        client.post("/api/v1/customers", json={
            "customer_id": "CUST-ALT", "name": "Alt客戶",
        })
        # Create PO for CUST-001
        client.post("/api/v1/po", json={
            "po_id": "PO-SOCHK", "customer_id": "CUST-001",
            "lines": [{"item_code": "CPU-001", "qty": 5, "unit_price": 10.0, "line_no": 1}],
        })
        # Try to create SO with different customer linked to PO
        r = client.post("/api/v1/so", json={
            "so_id": "SO-CHK", "po_id": "PO-SOCHK", "customer_id": "CUST-ALT",
            "lines": [{"item_code": "CPU-001", "qty": 5, "unit_price": 10.0, "line_no": 1}],
        })
        assert r.status_code == 400


class TestUpdateSONotFound:
    """L336: update_so 404 path"""

    def test_update_so_not_found(self, client):
        r = client.patch("/api/v1/so/NONEXIST", params={"status": "confirmed"})
        assert r.status_code == 404


class TestUpdateSORemarksOnly:
    """S718-T720: Update SO remarks only (different branch)"""

    def test_update_so_remarks(self, client, seed_item, seed_customer):
        client.post("/api/v1/so", json={
            "so_id": "SO-RMK", "customer_id": "CUST-001",
            "lines": [{"item_code": "CPU-001", "qty": 1, "unit_price": 1.0, "line_no": 1}],
        })
        r = client.patch("/api/v1/so/SO-RMK", params={"remarks": "緊急訂單"})
        assert r.status_code == 200
        assert r.json()["remarks"] == "緊急訂單"
