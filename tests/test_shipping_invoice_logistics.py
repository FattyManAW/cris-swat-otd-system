"""Shipping / Invoice / Logistics v2.0 API integration tests"""
import pytest


# ════════════════════════════════════════════════════════════════════════════
# Shipping tests
# ════════════════════════════════════════════════════════════════════════════

class TestShippingAPI:
    @pytest.fixture(autouse=True)
    def setup(self, client, seed_item, seed_customer, seed_po):
        # convert PO to SO
        r = client.post("/api/v1/po/PO-20260524-001/convert")
        assert r.status_code == 200
        self.so_id = r.json()["so_id"]
        # confirm SO
        r = client.patch(f"/api/v1/so/{self.so_id}", params={"status": "confirmed"})
        assert r.status_code == 200

    def test_create_shipping(self, client):
        r = client.post("/api/v1/shipping/create", json={
            "shipping_id": "SH-001",
            "so_id": self.so_id,
            "pallet_count": 2,
            "container_type": "40HQ",
        })
        assert r.status_code == 200
        assert r.json()["shipping_id"] == "SH-001"
        assert r.json()["status"] == "pending"

    def test_create_shipping_duplicate(self, client):
        client.post("/api/v1/shipping/create", json={
            "shipping_id": "SH-DUP", "so_id": self.so_id, "pallet_count": 1, "container_type": "20GP",
        })
        r = client.post("/api/v1/shipping/create", json={
            "shipping_id": "SH-DUP", "so_id": self.so_id, "pallet_count": 1, "container_type": "20GP",
        })
        assert r.status_code == 400

    def test_create_shipping_bad_so(self, client):
        r = client.post("/api/v1/shipping/create", json={
            "shipping_id": "SH-BAD", "so_id": "NONEXIST", "pallet_count": 1, "container_type": "20GP",
        })
        assert r.status_code == 404

    def test_get_shipping(self, client):
        client.post("/api/v1/shipping/create", json={
            "shipping_id": "SH-GET", "so_id": self.so_id, "pallet_count": 1, "container_type": "20GP",
        })
        r = client.get("/api/v1/shipping/SH-GET")
        assert r.status_code == 200
        assert r.json()["shipping_id"] == "SH-GET"

    def test_pack_shipping(self, client):
        client.post("/api/v1/shipping/create", json={
            "shipping_id": "SH-PACK", "so_id": self.so_id, "pallet_count": 0, "container_type": "20GP",
        })
        r = client.patch("/api/v1/shipping/SH-PACK/pack?pallet_count=3")
        assert r.status_code == 200
        assert r.json()["status"] == "packing"
        assert r.json()["pallet_count"] == 3

    def test_ship(self, client):
        client.post("/api/v1/shipping/create", json={
            "shipping_id": "SH-SHIP", "so_id": self.so_id, "pallet_count": 1, "container_type": "20GP",
        })
        client.patch("/api/v1/shipping/SH-SHIP/pack?pallet_count=1")
        r = client.patch("/api/v1/shipping/SH-SHIP/ship?tracking_no=TRK-001")
        assert r.status_code == 200
        assert r.json()["status"] == "shipped"
        assert r.json()["tracking_no"] == "TRK-001"

    def test_pack_detail(self, client):
        client.post("/api/v1/shipping/create", json={
            "shipping_id": "SH-PD", "so_id": self.so_id, "pallet_count": 0, "container_type": "20GP",
        })
        r = client.patch("/api/v1/shipping/SH-PD/pack_detail", json=[
            {"pallet_no": 1, "line_no": 1, "item_code": "CPU-001", "qty_packed": 5, "qty_shipped": 5, "weight_kg": 10.0, "dimensions_cm": "60x40x40"},
        ])
        assert r.status_code == 200
        assert r.json()["status"] == "packing"

        # get pack details
        r2 = client.get("/api/v1/shipping/SH-PD/pack_detail")
        assert r2.status_code == 200
        assert len(r2.json()) == 1
        assert r2.json()[0]["qty_packed"] == 5

    def test_pack_partial(self, client):
        client.post("/api/v1/shipping/create", json={
            "shipping_id": "SH-PART", "so_id": self.so_id, "pallet_count": 0, "container_type": "20GP",
        })
        r = client.patch("/api/v1/shipping/SH-PART/pack_partial", json=[
            {"pallet_no": 1, "line_no": 1, "item_code": "CPU-001", "qty_packed": 3, "weight_kg": 5.0, "dimensions_cm": "50x30x30"},
        ])
        assert r.status_code == 200
        assert r.json()["status"] == "partial_packed"

    def test_partial_ship(self, client):
        client.post("/api/v1/shipping/create", json={
            "shipping_id": "SH-PS", "so_id": self.so_id, "pallet_count": 0, "container_type": "20GP",
        })
        client.patch("/api/v1/shipping/SH-PS/pack_partial", json=[
            {"pallet_no": 1, "line_no": 1, "item_code": "CPU-001", "qty_packed": 3, "weight_kg": 5.0, "dimensions_cm": "50x30x30"},
        ])
        r = client.patch("/api/v1/shipping/SH-PS/partial_ship", json={
            "remaining_qty": 7, "remarks": "分兩批出",
        })
        assert r.status_code == 200
        assert r.json()["status"] == "shipped"
        assert r.json()["partial_delivery"] is True

    def test_deliver(self, client):
        client.post("/api/v1/shipping/create", json={
            "shipping_id": "SH-DEL", "so_id": self.so_id, "pallet_count": 1, "container_type": "20GP",
        })
        client.patch("/api/v1/shipping/SH-DEL/pack?pallet_count=1")
        client.patch("/api/v1/shipping/SH-DEL/ship?tracking_no=TRK-DEL")
        r = client.patch("/api/v1/shipping/SH-DEL/deliver", json={
            "delivery_proof_url": "https://example.com/pod",
            "remarks": "簽收完成",
        })
        assert r.status_code == 200
        assert r.json()["status"] == "delivered"
        assert r.json()["is_delivery_signed"] is True

    def test_shipping_attachments(self, client):
        client.post("/api/v1/shipping/create", json={
            "shipping_id": "SH-ATT", "so_id": self.so_id, "pallet_count": 1, "container_type": "20GP",
        })
        r = client.post("/api/v1/shipping/SH-ATT/attach", json={
            "attachment_id": "ATT-001",
            "type": "pod",
            "filename": "pod.pdf",
            "url": "https://example.com/pod.pdf",
            "uploaded_by": "agent-test",
        })
        assert r.status_code == 200
        assert r.json()["attachment_id"] == "ATT-001"

        r2 = client.get("/api/v1/shipping/SH-ATT/attachments")
        assert r2.status_code == 200
        assert len(r2.json()) == 1

    def test_shipping_lines(self, client):
        client.post("/api/v1/shipping/create", json={
            "shipping_id": "SH-LINES", "so_id": self.so_id, "pallet_count": 1, "container_type": "20GP",
        })
        r = client.get("/api/v1/shipping/SH-LINES/lines")
        assert r.status_code == 200
        assert len(r.json()) == 2  # SO has 2 lines


# ════════════════════════════════════════════════════════════════════════════
# Invoice tests
# ════════════════════════════════════════════════════════════════════════════

class TestInvoiceAPI:
    @pytest.fixture(autouse=True)
    def setup(self, client, seed_item, seed_customer, seed_po):
        r = client.post("/api/v1/po/PO-20260524-001/convert")
        self.so_id = r.json()["so_id"]
        client.patch(f"/api/v1/so/{self.so_id}", params={"status": "confirmed"})

    def test_create_invoice(self, client):
        r = client.post("/api/v1/invoice/create", json={
            "invoice_id": "INV-001",
            "so_id": self.so_id,
            "amount": 5000.0,
            "invoice_no": "TAX-2026-001",
            "invoice_type": "tax",
            "tax_amount": 250.0,
            "currency": "USD",
            "lines": [
                {"line_no": 1, "item_code": "CPU-001", "description": "CPU", "qty": 10.0, "unit_price": 475.0, "amount": 4750.0},
            ],
        })
        assert r.status_code == 200
        assert r.json()["invoice_id"] == "INV-001"
        assert r.json()["amount"] == 5000.0
        assert r.json()["net_amount"] == 4750.0

    def test_create_invoice_bad_so(self, client):
        r = client.post("/api/v1/invoice/create", json={
            "invoice_id": "INV-BAD", "so_id": "NONEXIST", "amount": 100.0,
        })
        assert r.status_code == 404

    def test_invoice_issue_send_payment_lifecycle(self, client):
        # create
        client.post("/api/v1/invoice/create", json={
            "invoice_id": "INV-LC",
            "so_id": self.so_id,
            "amount": 3000.0,
            "lines": [{"line_no": 1, "item_code": "CPU-001", "description": "CPU", "qty": 5.0, "unit_price": 600.0}],
        })
        # issue
        r = client.patch("/api/v1/invoice/INV-LC/issue", json={"invoice_no": "TAX-002"})
        assert r.status_code == 200
        assert r.json()["status"] == "issued"
        # send
        r = client.post("/api/v1/invoice/INV-LC/send")
        assert r.status_code == 200
        assert r.json()["status"] == "sent"
        # payment
        r = client.post("/api/v1/invoice/INV-LC/payment", json={"payment_ref": "PAY-001"})
        assert r.status_code == 200
        assert r.json()["status"] == "paid"

    def test_void_invoice(self, client):
        client.post("/api/v1/invoice/create", json={
            "invoice_id": "INV-VOID", "so_id": self.so_id, "amount": 100.0,
            "lines": [{"line_no": 1, "item_code": "CPU-001", "description": "CPU", "qty": 1.0, "unit_price": 100.0}],
        })
        client.patch("/api/v1/invoice/INV-VOID/issue")
        r = client.patch("/api/v1/invoice/INV-VOID/void", json={"void_reason": "測試作廢"})
        assert r.status_code == 200
        assert r.json()["status"] == "void"
        assert r.json()["void_reason"] == "測試作廢"

    def test_credit_note(self, client):
        client.post("/api/v1/invoice/create", json={
            "invoice_id": "INV-CN", "so_id": self.so_id, "amount": 2000.0,
            "lines": [{"line_no": 1, "item_code": "CPU-001", "description": "CPU", "qty": 2.0, "unit_price": 1000.0}],
        })
        client.patch("/api/v1/invoice/INV-CN/issue")
        r = client.post("/api/v1/invoice/INV-CN/credit", json={"credit_note_for": "INV-CN", "amount": 500.0})
        assert r.status_code == 200
        assert r.json()["status"] == "credit_note"
        assert r.json()["invoice_type"] == "credit_note"

    def test_get_invoice_lines(self, client):
        client.post("/api/v1/invoice/create", json={
            "invoice_id": "INV-LINES", "so_id": self.so_id, "amount": 100.0,
            "lines": [
                {"line_no": 1, "item_code": "CPU-001", "description": "CPU", "qty": 1.0, "unit_price": 100.0, "amount": 100.0},
            ],
        })
        r = client.get("/api/v1/invoice/INV-LINES/lines")
        assert r.status_code == 200
        assert len(r.json()) == 1

    def test_get_invoices_by_so(self, client):
        client.post("/api/v1/invoice/create", json={
            "invoice_id": "INV-SO", "so_id": self.so_id, "amount": 500.0,
            "lines": [{"line_no": 1, "item_code": "CPU-001", "description": "CPU", "qty": 1.0, "unit_price": 500.0}],
        })
        r = client.get(f"/api/v1/invoice/by_so/{self.so_id}")
        assert r.status_code == 200
        assert len(r.json()) >= 1

    # Note: overdue test is skipped because it uses utcnow() comparison
    # and we can't easily fake dates in this setup


# ════════════════════════════════════════════════════════════════════════════
# Logistics tests
# ════════════════════════════════════════════════════════════════════════════

class TestLogisticsAPI:
    @pytest.fixture(autouse=True)
    def setup(self, client, seed_item, seed_customer, seed_po):
        r = client.post("/api/v1/po/PO-20260524-001/convert")
        self.so_id = r.json()["so_id"]
        client.patch(f"/api/v1/so/{self.so_id}", params={"status": "confirmed"})
        client.post("/api/v1/shipping/create", json={
            "shipping_id": "SH-LG", "so_id": self.so_id, "pallet_count": 1, "container_type": "20GP",
        })

    def test_arrange_logistics(self, client):
        r = client.post("/api/v1/logistics/arrange", json={
            "tracking_no": "TRK-001",
            "shipping_id": "SH-LG",
            "carrier": "DHL",
            "eta": "2026-06-30T00:00:00",
            "origin_port": "KHH",
            "dest_port": "LAX",
            "vessel_flight": "BR-123",
            "bl_number": "BL-001",
            "booking_ref": "BK-001",
        })
        assert r.status_code == 200
        assert r.json()["tracking_no"] == "TRK-001"
        assert r.json()["status"] == "booked"

    def test_logistics_depart(self, client):
        client.post("/api/v1/logistics/arrange", json={
            "tracking_no": "TRK-DEP", "shipping_id": "SH-LG", "carrier": "DHL", "eta": "2026-06-30T00:00:00",
            "origin_port": "KHH", "dest_port": "LAX",
        })
        r = client.post("/api/v1/logistics/TRK-DEP/depart", json={
            "departure_date": "2026-06-01T00:00:00", "vessel_flight": "BR-123", "origin_port": "KHH",
        })
        assert r.status_code == 200
        assert r.json()["status"] == "in_transit"
        assert r.json()["departure_date"] is not None

    def test_logistics_customs(self, client):
        client.post("/api/v1/logistics/arrange", json={
            "tracking_no": "TRK-CUS", "shipping_id": "SH-LG", "carrier": "DHL", "eta": "2026-06-30T00:00:00",
            "origin_port": "KHH", "dest_port": "LAX",
        })
        r = client.post("/api/v1/logistics/TRK-CUS/customs", json={
            "customs_status": "cleared", "bl_number": "BL-002", "dest_port": "LAX",
        })
        assert r.status_code == 200
        assert r.json()["status"] == "customs"

    def test_logistics_customs_hold(self, client):
        client.post("/api/v1/logistics/arrange", json={
            "tracking_no": "TRK-HOLD", "shipping_id": "SH-LG", "carrier": "DHL", "eta": "2026-06-30T00:00:00",
            "origin_port": "KHH", "dest_port": "LAX",
        })
        r = client.post("/api/v1/logistics/TRK-HOLD/customs_hold", json={"reason": "文件查驗"})
        assert r.status_code == 200
        assert r.json()["status"] == "customs_hold"

    def test_logistics_customs_clear(self, client):
        client.post("/api/v1/logistics/arrange", json={
            "tracking_no": "TRK-CLR", "shipping_id": "SH-LG", "carrier": "DHL", "eta": "2026-06-30T00:00:00",
            "origin_port": "KHH", "dest_port": "LAX",
        })
        client.post("/api/v1/logistics/TRK-CLR/customs", json={"customs_status": "cleared"})
        r = client.post("/api/v1/logistics/TRK-CLR/customs_clear")
        assert r.status_code == 200
        assert r.json()["status"] == "in_transit"

    def test_logistics_arrive(self, client):
        client.post("/api/v1/logistics/arrange", json={
            "tracking_no": "TRK-ARR", "shipping_id": "SH-LG", "carrier": "DHL", "eta": "2026-06-30T00:00:00",
            "origin_port": "KHH", "dest_port": "LAX",
        })
        r = client.post("/api/v1/logistics/TRK-ARR/arrive", json={"delivery_note": "已送達倉庫"})
        assert r.status_code == 200
        assert r.json()["status"] == "arrived"

    def test_logistics_deliver_sign(self, client):
        client.post("/api/v1/logistics/arrange", json={
            "tracking_no": "TRK-DS", "shipping_id": "SH-LG", "carrier": "DHL", "eta": "2026-06-30T00:00:00",
            "origin_port": "KHH", "dest_port": "LAX",
        })
        r = client.post("/api/v1/logistics/TRK-DS/deliver_sign", json={
            "signed_by": "張三", "is_final": True,
        })
        assert r.status_code == 200
        assert r.json()["status"] == "delivered"

    def test_logistics_failed_reroute(self, client):
        client.post("/api/v1/logistics/arrange", json={
            "tracking_no": "TRK-FR", "shipping_id": "SH-LG", "carrier": "DHL", "eta": "2026-06-30T00:00:00",
            "origin_port": "KHH", "dest_port": "LAX",
        })
        r = client.post("/api/v1/logistics/TRK-FR/failed", json={"reason": "貨物損壞"})
        assert r.status_code == 200
        assert r.json()["status"] == "failed"

        r = client.post("/api/v1/logistics/TRK-FR/reroute", json={
            "new_carrier": "FedEx", "new_eta": "2026-07-10T00:00:00", "note": "改由 FedEx 重送",
        })
        assert r.status_code == 200
        assert r.json()["status"] == "reroute"
        assert r.json()["carrier"] == "FedEx"

    def test_logistics_partial_arrive(self, client):
        client.post("/api/v1/logistics/arrange", json={
            "tracking_no": "TRK-PA", "shipping_id": "SH-LG", "carrier": "DHL", "eta": "2026-06-30T00:00:00",
            "origin_port": "KHH", "dest_port": "LAX",
        })
        r = client.post("/api/v1/logistics/TRK-PA/partial_arrive", json={
            "delivered_qty": 5, "remaining_qty": 5,
        })
        assert r.status_code == 200
        assert r.json()["status"] == "partial_delivery"

    def test_logistics_events(self, client):
        client.post("/api/v1/logistics/arrange", json={
            "tracking_no": "TRK-EV", "shipping_id": "SH-LG", "carrier": "DHL", "eta": "2026-06-30T00:00:00",
            "origin_port": "KHH", "dest_port": "LAX",
        })
        # depart creates event
        client.post("/api/v1/logistics/TRK-EV/depart")

        r = client.get("/api/v1/logistics/TRK-EV/events")
        assert r.status_code == 200
        events = r.json()
        # booked + in_transit
        assert len(events) >= 2

    def test_logistics_by_shipping(self, client):
        client.post("/api/v1/logistics/arrange", json={
            "tracking_no": "TRK-BS", "shipping_id": "SH-LG", "carrier": "DHL", "eta": "2026-06-30T00:00:00",
            "origin_port": "KHH", "dest_port": "LAX",
        })
        r = client.get("/api/v1/logistics/by_shipping/SH-LG")
        assert r.status_code == 200
        assert r.json()["tracking_no"] == "TRK-BS"

    def test_active_logistics(self, client):
        client.post("/api/v1/logistics/arrange", json={
            "tracking_no": "TRK-ACT", "shipping_id": "SH-LG", "carrier": "DHL", "eta": "2026-06-30T00:00:00",
            "origin_port": "KHH", "dest_port": "LAX",
        })
        r = client.get("/api/v1/logistics/active")
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_manual_event(self, client):
        client.post("/api/v1/logistics/arrange", json={
            "tracking_no": "TRK-ME", "shipping_id": "SH-LG", "carrier": "DHL", "eta": "2026-06-30T00:00:00",
            "origin_port": "KHH", "dest_port": "LAX",
        })
        r = client.post("/api/v1/logistics/TRK-ME/event", json={
            "event_id": "EV-001",
            "status": "location_update",
            "location": "HKG",
            "note": "經香港轉運",
            "created_by": "agent-cs",
        })
        assert r.status_code == 200
        assert r.json()["status"] == "location_update"
        assert r.json()["location"] == "HKG"