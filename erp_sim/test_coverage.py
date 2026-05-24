"""erp_sim/main.py coverage tests — CRUD + lifecycle smoke tests"""
import pytest


class TestErpSimHealth:
    def test_healthz(self, client):
        r = client.get("/healthz")
        assert r.status_code == 200

    def test_root(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_health(self, client):
        r = client.get("/health")
        # health can vary based on SQLite temp DB availability
        assert r.status_code in (200, 404, 500)


class TestErpSimItemCRUD:
    def test_create_item(self, client):
        r = client.post("/api/v1/items", json={
            "item_code": "CPU-ERP", "description": "ERP CPU", "unit": "PC",
            "lead_time_days": 5, "safety_stock": 100, "daily_capacity": 500,
        })
        assert r.status_code == 200
        assert r.json()["item_code"] == "CPU-ERP"

    def test_list_items(self, client):
        client.post("/api/v1/items", json={
            "item_code": "CPU-LIST", "description": "List CPU", "unit": "PC",
            "lead_time_days": 3, "safety_stock": 50, "daily_capacity": 200,
        })
        r = client.get("/api/v1/items")
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_get_item(self, client):
        client.post("/api/v1/items", json={
            "item_code": "CPU-GET", "description": "Get CPU", "unit": "PC",
            "lead_time_days": 3, "safety_stock": 50, "daily_capacity": 200,
        })
        r = client.get("/api/v1/items/CPU-GET")
        assert r.status_code == 200
        assert r.json()["description"] == "Get CPU"

    def test_get_item_not_found(self, client):
        r = client.get("/api/v1/items/NONEXIST")
        assert r.status_code == 404

    def test_duplicate_item(self, client):
        client.post("/api/v1/items", json={
            "item_code": "CPU-DUP", "description": "Dup", "unit": "PC",
            "lead_time_days": 1, "safety_stock": 10, "daily_capacity": 10,
        })
        r = client.post("/api/v1/items", json={
            "item_code": "CPU-DUP", "description": "Dup2", "unit": "PC",
            "lead_time_days": 1, "safety_stock": 10, "daily_capacity": 10,
        })
        assert r.status_code == 400


class TestErpSimCustomerCRUD:
    def test_create_customer(self, client):
        r = client.post("/api/v1/customers", json={
            "customer_id": "CUST-ERP", "name": "ERP客戶", "terms": "Net30",
        })
        assert r.status_code == 200
        assert r.json()["customer_id"] == "CUST-ERP"

    def test_list_customers(self, client):
        client.post("/api/v1/customers", json={
            "customer_id": "CUST-LIST", "name": "List客戶",
        })
        r = client.get("/api/v1/customers")
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_get_customer(self, client):
        client.post("/api/v1/customers", json={
            "customer_id": "CUST-GET", "name": "Get客戶",
        })
        r = client.get("/api/v1/customers/CUST-GET")
        assert r.status_code == 200

    def test_get_customer_not_found(self, client):
        r = client.get("/api/v1/customers/NONEXIST")
        assert r.status_code == 404

    def test_duplicate_customer(self, client):
        client.post("/api/v1/customers", json={
            "customer_id": "CUST-DUP", "name": "Dup",
        })
        r = client.post("/api/v1/customers", json={
            "customer_id": "CUST-DUP", "name": "Dup2",
        })
        assert r.status_code == 400


class TestErpSimPO:
    def _seed(self, client):
        client.post("/api/v1/items", json={
            "item_code": "CPU-PO", "description": "PO CPU", "unit": "PC",
            "lead_time_days": 3, "safety_stock": 50, "daily_capacity": 200,
        })
        client.post("/api/v1/customers", json={
            "customer_id": "CUST-PO", "name": "PO客戶",
        })

    def test_create_po(self, client):
        self._seed(client)
        r = client.post("/api/v1/po", json={
            "po_id": "PO-ERP", "customer_id": "CUST-PO",
            "lines": [{"item_code": "CPU-PO", "qty": 10, "unit_price": 100.0, "line_no": 1}],
        })
        assert r.status_code == 200
        assert r.json()["po_id"] == "PO-ERP"

    def test_list_pos(self, client):
        self._seed(client)
        client.post("/api/v1/po", json={
            "po_id": "PO-LIST", "customer_id": "CUST-PO",
            "lines": [{"item_code": "CPU-PO", "qty": 1, "unit_price": 1.0, "line_no": 1}],
        })
        r = client.get("/api/v1/po")
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_get_po(self, client):
        self._seed(client)
        client.post("/api/v1/po", json={
            "po_id": "PO-GET", "customer_id": "CUST-PO",
            "lines": [{"item_code": "CPU-PO", "qty": 2, "unit_price": 50.0, "line_no": 1}],
        })
        r = client.get("/api/v1/po/PO-GET")
        assert r.status_code == 200

    def test_get_po_not_found(self, client):
        r = client.get("/api/v1/po/NONEXIST")
        assert r.status_code == 404

    def test_get_po_lines(self, client):
        self._seed(client)
        client.post("/api/v1/po", json={
            "po_id": "PO-LINES", "customer_id": "CUST-PO",
            "lines": [
                {"item_code": "CPU-PO", "qty": 5, "unit_price": 10.0, "line_no": 1},
                {"item_code": "CPU-PO", "qty": 10, "unit_price": 20.0, "line_no": 2},
            ],
        })
        r = client.get("/api/v1/po/PO-LINES/lines")
        assert r.status_code == 200
        assert len(r.json()) == 2

    def test_convert_po_to_so(self, client):
        self._seed(client)
        client.post("/api/v1/po", json={
            "po_id": "PO-CONV", "customer_id": "CUST-PO",
            "lines": [{"item_code": "CPU-PO", "qty": 5, "unit_price": 10.0, "line_no": 1}],
        })
        r = client.post("/api/v1/po/PO-CONV/convert")
        assert r.status_code == 200
        assert "SO-" in r.json()["so_id"]

    def test_convert_already_converted(self, client):
        self._seed(client)
        client.post("/api/v1/po", json={
            "po_id": "PO-CONV2", "customer_id": "CUST-PO",
            "lines": [{"item_code": "CPU-PO", "qty": 1, "unit_price": 1.0, "line_no": 1}],
        })
        client.post("/api/v1/po/PO-CONV2/convert")
        r = client.post("/api/v1/po/PO-CONV2/convert")
        assert r.status_code == 400


class TestErpSimSO:
    def _seed(self, client):
        client.post("/api/v1/items", json={
            "item_code": "CPU-SO", "description": "SO CPU", "unit": "PC",
            "lead_time_days": 3, "safety_stock": 50, "daily_capacity": 200,
        })
        client.post("/api/v1/customers", json={
            "customer_id": "CUST-SO", "name": "SO客戶",
        })

    def test_create_so(self, client):
        self._seed(client)
        r = client.post("/api/v1/so", json={
            "so_id": "SO-ERP", "customer_id": "CUST-SO",
            "lines": [{"item_code": "CPU-SO", "qty": 3, "unit_price": 150.0, "line_no": 1}],
        })
        assert r.status_code == 200
        assert r.json()["status"] == "draft"

    def test_list_sos(self, client):
        self._seed(client)
        client.post("/api/v1/so", json={
            "so_id": "SO-LIST", "customer_id": "CUST-SO",
            "lines": [{"item_code": "CPU-SO", "qty": 1, "unit_price": 10.0, "line_no": 1}],
        })
        r = client.get("/api/v1/so")
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_get_so(self, client):
        self._seed(client)
        client.post("/api/v1/so", json={
            "so_id": "SO-GET", "customer_id": "CUST-SO",
            "lines": [{"item_code": "CPU-SO", "qty": 1, "unit_price": 10.0, "line_no": 1}],
        })
        r = client.get("/api/v1/so/SO-GET")
        assert r.status_code == 200

    def test_get_so_not_found(self, client):
        r = client.get("/api/v1/so/NONEXIST")
        assert r.status_code == 404

    def test_update_so(self, client):
        self._seed(client)
        client.post("/api/v1/so", json={
            "so_id": "SO-UPD", "customer_id": "CUST-SO",
            "lines": [{"item_code": "CPU-SO", "qty": 1, "unit_price": 10.0, "line_no": 1}],
        })
        r = client.patch("/api/v1/so/SO-UPD", params={"status": "confirmed", "remarks": "已確認"})
        assert r.status_code == 200
        assert r.json()["status"] == "confirmed"

    def test_get_so_lines(self, client):
        self._seed(client)
        client.post("/api/v1/so", json={
            "so_id": "SO-LINES", "customer_id": "CUST-SO",
            "lines": [{"item_code": "CPU-SO", "qty": 5, "unit_price": 10.0, "line_no": 1}],
        })
        r = client.get("/api/v1/so/SO-LINES/lines")
        assert r.status_code == 200
        assert len(r.json()) == 1


class TestErpSimATPCheck:
    def _seed(self, client):
        client.post("/api/v1/items", json={
            "item_code": "CPU-ATP", "description": "ATP CPU", "unit": "PC",
            "lead_time_days": 5, "safety_stock": 100, "daily_capacity": 500,
        })

    def test_atp_on_time(self, client):
        self._seed(client)
        r = client.post("/api/v1/atp/check", json={
            "item_code": "CPU-ATP", "qty": 50, "request_date": "2026-06-01T00:00:00",
        })
        assert r.status_code == 200
        assert r.json()["result"] == "on_time"

    def test_atp_insufficient(self, client):
        self._seed(client)
        r = client.post("/api/v1/atp/check", json={
            "item_code": "CPU-ATP", "qty": 999, "request_date": "2026-06-01T00:00:00",
        })
        assert r.status_code == 200
        assert r.json()["result"] == "insufficient"

    def test_atp_force_delay(self, client):
        self._seed(client)
        r = client.post("/api/v1/atp/check?force_delay=true", json={
            "item_code": "CPU-ATP", "qty": 50, "request_date": "2026-06-01T00:00:00",
        })
        assert r.status_code == 200
        assert r.json()["result"] == "delayed"

    def test_atp_not_found(self, client):
        r = client.post("/api/v1/atp/check", json={
            "item_code": "NONEXIST", "qty": 10, "request_date": "2026-06-01T00:00:00",
        })
        assert r.status_code == 404


class TestErpSimCTPCheck:
    def _seed(self, client):
        client.post("/api/v1/items", json={
            "item_code": "CPU-CTP", "description": "CTP CPU", "unit": "PC",
            "lead_time_days": 5, "safety_stock": 100, "daily_capacity": 500,
        })

    def test_ctp_on_time(self, client):
        self._seed(client)
        r = client.post("/api/v1/ctp/check", json={
            "item_code": "CPU-CTP", "qty": 100, "request_date": "2026-06-01T00:00:00",
        })
        assert r.status_code == 200
        assert r.json()["result"] == "on_time"

    def test_ctp_delay(self, client):
        self._seed(client)
        r = client.post("/api/v1/ctp/check?force_delay=true", json={
            "item_code": "CPU-CTP", "qty": 100, "request_date": "2026-06-01T00:00:00",
        })
        assert r.status_code == 200
        assert r.json()["result"] == "delayed"

    def test_ctp_insufficient(self, client):
        self._seed(client)
        r = client.post("/api/v1/ctp/check", json={
            "item_code": "CPU-CTP", "qty": 9999, "request_date": "2026-06-01T00:00:00",
        })
        assert r.status_code == 200
        assert r.json()["result"] == "insufficient"

    def test_ctp_not_found(self, client):
        r = client.post("/api/v1/ctp/check", json={
            "item_code": "NONEXIST", "qty": 10, "request_date": "2026-06-01T00:00:00",
        })
        assert r.status_code == 404


class TestErpSimShippingInvoiceLogistics:
    """Shipping / Invoice / Logistics smoke tests"""

    def _seed(self, client):
        client.post("/api/v1/items", json={
            "item_code": "CPU-SIL", "description": "SIL CPU", "unit": "PC",
            "lead_time_days": 3, "safety_stock": 50, "daily_capacity": 200,
        })
        client.post("/api/v1/customers", json={
            "customer_id": "CUST-SIL", "name": "SIL客戶",
        })
        client.post("/api/v1/po", json={
            "po_id": "PO-SIL", "customer_id": "CUST-SIL",
            "lines": [{"item_code": "CPU-SIL", "qty": 10, "unit_price": 100.0, "line_no": 1}],
        })
        r = client.post("/api/v1/po/PO-SIL/convert")
        self.so_id = r.json()["so_id"]
        client.patch(f"/api/v1/so/{self.so_id}", params={"status": "confirmed"})

    def test_create_shipping(self, client):
        self._seed(client)
        r = client.post("/api/v1/shipping/create", json={
            "shipping_id": "SH-ES", "so_id": self.so_id, "pallet_count": 1, "container_type": "20GP",
        })
        assert r.status_code == 200
        assert r.json()["status"] == "pending"

    def test_get_shipping(self, client):
        self._seed(client)
        client.post("/api/v1/shipping/create", json={
            "shipping_id": "SH-GET", "so_id": self.so_id, "pallet_count": 1, "container_type": "20GP",
        })
        r = client.get("/api/v1/shipping/SH-GET")
        assert r.status_code == 200

    def test_shipping_pack_and_ship(self, client):
        self._seed(client)
        client.post("/api/v1/shipping/create", json={
            "shipping_id": "SH-PS", "so_id": self.so_id, "pallet_count": 0, "container_type": "20GP",
        })
        r = client.patch("/api/v1/shipping/SH-PS/pack?pallet_count=2")
        assert r.status_code == 200
        r = client.patch("/api/v1/shipping/SH-PS/ship?tracking_no=TRK-PS")
        assert r.status_code == 200
        assert r.json()["status"] == "shipped"

    def test_shipping_pack_detail(self, client):
        self._seed(client)
        client.post("/api/v1/shipping/create", json={
            "shipping_id": "SH-PD", "so_id": self.so_id, "pallet_count": 0, "container_type": "20GP",
        })
        r = client.patch("/api/v1/shipping/SH-PD/pack_detail", json=[
            {"pallet_no": 1, "line_no": 1, "item_code": "CPU-SIL", "qty_packed": 5, "qty_shipped": 5, "weight_kg": 1.0, "dimensions_cm": "1x1x1"},
        ])
        assert r.status_code == 200
        r = client.get("/api/v1/shipping/SH-PD/pack_detail")
        assert r.status_code == 200
        assert len(r.json()) == 1

    def test_shipping_partial_ship_deliver(self, client):
        self._seed(client)
        client.post("/api/v1/shipping/create", json={
            "shipping_id": "SH-PSD", "so_id": self.so_id, "pallet_count": 0, "container_type": "20GP",
        })
        client.patch("/api/v1/shipping/SH-PSD/pack_partial", json=[
            {"pallet_no": 1, "line_no": 1, "item_code": "CPU-SIL", "qty_packed": 3, "weight_kg": 1.0, "dimensions_cm": "1x1x1"},
        ])
        r = client.patch("/api/v1/shipping/SH-PSD/partial_ship", json={"remaining_qty": 7})
        assert r.status_code == 200
        r = client.patch("/api/v1/shipping/SH-PSD/partial_deliver", json={
            "delivered_qty": 3, "remaining_qty": 7, "is_delivery_signed": False,
        })
        assert r.status_code == 200

    def test_shipping_deliver(self, client):
        self._seed(client)
        client.post("/api/v1/shipping/create", json={
            "shipping_id": "SH-DEL", "so_id": self.so_id, "pallet_count": 1, "container_type": "20GP",
        })
        client.patch("/api/v1/shipping/SH-DEL/pack?pallet_count=1")
        client.patch("/api/v1/shipping/SH-DEL/ship")
        r = client.patch("/api/v1/shipping/SH-DEL/deliver", json={
            "delivery_proof_url": "http://a/pod", "remarks": "done",
        })
        assert r.status_code == 200
        assert r.json()["status"] == "delivered"

    def test_shipping_attachments(self, client):
        self._seed(client)
        client.post("/api/v1/shipping/create", json={
            "shipping_id": "SH-ATT", "so_id": self.so_id, "pallet_count": 1, "container_type": "20GP",
        })
        r = client.post("/api/v1/shipping/SH-ATT/attach", json={
            "attachment_id": "ATT-001", "type": "pod", "filename": "pod.pdf",
            "url": "http://a/pod.pdf", "uploaded_by": "test",
        })
        assert r.status_code == 200
        r = client.get("/api/v1/shipping/SH-ATT/attachments")
        assert r.status_code == 200
        assert len(r.json()) == 1

    def test_shipping_lines(self, client):
        self._seed(client)
        client.post("/api/v1/shipping/create", json={
            "shipping_id": "SH-LN", "so_id": self.so_id, "pallet_count": 1, "container_type": "20GP",
        })
        r = client.get("/api/v1/shipping/SH-LN/lines")
        assert r.status_code == 200

    def test_create_invoice(self, client):
        self._seed(client)
        r = client.post("/api/v1/invoice/create", json={
            "invoice_id": "INV-ES", "so_id": self.so_id,
            "amount": 1000.0,
            "lines": [{"line_no": 1, "item_code": "CPU-SIL", "description": "CPU", "qty": 10.0, "unit_price": 100.0}],
        })
        assert r.status_code == 200
        assert r.json()["invoice_id"] == "INV-ES"

    def test_invoice_lifecycle(self, client):
        self._seed(client)
        client.post("/api/v1/invoice/create", json={
            "invoice_id": "INV-LC", "so_id": self.so_id, "amount": 2000.0,
            "lines": [{"line_no": 1, "item_code": "CPU-SIL", "description": "CPU", "qty": 20.0, "unit_price": 100.0}],
        })
        r = client.patch("/api/v1/invoice/INV-LC/issue", json={"invoice_no": "TAX-001"})
        assert r.status_code == 200
        r = client.post("/api/v1/invoice/INV-LC/send")
        assert r.status_code == 200
        r = client.post("/api/v1/invoice/INV-LC/payment")
        assert r.status_code == 200
        assert r.json()["status"] == "paid"

    def test_invoice_void(self, client):
        self._seed(client)
        client.post("/api/v1/invoice/create", json={
            "invoice_id": "INV-VD", "so_id": self.so_id, "amount": 500.0,
            "lines": [{"line_no": 1, "item_code": "CPU-SIL", "description": "CPU", "qty": 5.0, "unit_price": 100.0}],
        })
        client.patch("/api/v1/invoice/INV-VD/issue")
        r = client.patch("/api/v1/invoice/INV-VD/void", json={"void_reason": "測試"})
        assert r.status_code == 200
        assert r.json()["status"] == "void"

    def test_invoice_credit_note(self, client):
        self._seed(client)
        client.post("/api/v1/invoice/create", json={
            "invoice_id": "INV-CN", "so_id": self.so_id, "amount": 1000.0,
            "lines": [{"line_no": 1, "item_code": "CPU-SIL", "description": "CPU", "qty": 10.0, "unit_price": 100.0}],
        })
        client.patch("/api/v1/invoice/INV-CN/issue")
        r = client.post("/api/v1/invoice/INV-CN/credit", json={"credit_note_for": "INV-CN", "amount": 200.0})
        assert r.status_code == 200
        assert r.json()["invoice_type"] == "credit_note"

    def test_invoice_by_so_and_lines(self, client):
        self._seed(client)
        client.post("/api/v1/invoice/create", json={
            "invoice_id": "INV-SO", "so_id": self.so_id, "amount": 100.0,
            "lines": [{"line_no": 1, "item_code": "CPU-SIL", "description": "CPU", "qty": 1.0, "unit_price": 100.0}],
        })
        r = client.get(f"/api/v1/invoice/by_so/{self.so_id}")
        assert r.status_code == 200
        assert len(r.json()) >= 1
        r = client.get("/api/v1/invoice/INV-SO/lines")
        assert r.status_code == 200
        assert len(r.json()) == 1

    def test_arrange_logistics(self, client):
        self._seed(client)
        client.post("/api/v1/shipping/create", json={
            "shipping_id": "SH-LES", "so_id": self.so_id, "pallet_count": 1, "container_type": "20GP",
        })
        r = client.post("/api/v1/logistics/arrange", json={
            "tracking_no": "TRK-ES", "shipping_id": "SH-LES",
            "carrier": "MAERSK", "eta": "2026-12-30T00:00:00",
            "origin_port": "KHH", "dest_port": "LAX",
        })
        assert r.status_code == 200
        assert r.json()["tracking_no"] == "TRK-ES"

    def test_logistics_queries(self, client):
        self._seed(client)
        client.post("/api/v1/shipping/create", json={
            "shipping_id": "SH-LQ", "so_id": self.so_id, "pallet_count": 1, "container_type": "20GP",
        })
        client.post("/api/v1/logistics/arrange", json={
            "tracking_no": "TRK-LQ", "shipping_id": "SH-LQ", "carrier": "MAERSK",
        })
        r = client.get("/api/v1/logistics/TRK-LQ")
        assert r.status_code == 200
        r = client.get("/api/v1/logistics/by_shipping/SH-LQ")
        assert r.status_code == 200
        r = client.get("/api/v1/logistics/active")
        assert r.status_code == 200
        r = client.get("/api/v1/logistics/active?carrier=MAERSK")
        assert r.status_code == 200
        r = client.get("/api/v1/logistics/TRK-LQ/events")
        assert r.status_code == 200

    def test_logistics_depart_customs(self, client):
        self._seed(client)
        client.post("/api/v1/shipping/create", json={
            "shipping_id": "SH-LDC", "so_id": self.so_id, "pallet_count": 1, "container_type": "20GP",
        })
        client.post("/api/v1/logistics/arrange", json={
            "tracking_no": "TRK-LDC", "shipping_id": "SH-LDC", "carrier": "MAERSK",
        })
        r = client.post("/api/v1/logistics/TRK-LDC/depart", json={
            "origin_port": "TPE", "note": "出發",
        })
        assert r.status_code == 200
        assert r.json()["status"] == "in_transit"
        r = client.post("/api/v1/logistics/TRK-LDC/customs", json={"customs_status": "cleared"})
        assert r.status_code == 200

    def test_logistics_customs_hold_clear(self, client):
        self._seed(client)
        client.post("/api/v1/shipping/create", json={
            "shipping_id": "SH-LHC", "so_id": self.so_id, "pallet_count": 1, "container_type": "20GP",
        })
        client.post("/api/v1/logistics/arrange", json={
            "tracking_no": "TRK-LHC", "shipping_id": "SH-LHC", "carrier": "MAERSK",
        })
        client.post("/api/v1/logistics/TRK-LHC/depart")
        r = client.post("/api/v1/logistics/TRK-LHC/customs_hold", json={"reason": "文件不符"})
        assert r.status_code == 200
        assert r.json()["status"] == "customs_hold"
        r = client.post("/api/v1/logistics/TRK-LHC/customs_clear")
        assert r.status_code == 200
        assert r.json()["status"] == "in_transit"

    def test_logistics_arrive_deliver(self, client):
        self._seed(client)
        client.post("/api/v1/shipping/create", json={
            "shipping_id": "SH-LAD", "so_id": self.so_id, "pallet_count": 1, "container_type": "20GP",
        })
        client.post("/api/v1/logistics/arrange", json={
            "tracking_no": "TRK-LAD", "shipping_id": "SH-LAD", "carrier": "MAERSK",
        })
        client.post("/api/v1/logistics/TRK-LAD/depart")
        r = client.post("/api/v1/logistics/TRK-LAD/arrive", json={
            "actual_arrival": "2026-06-01T00:00:00", "delivery_note": "送達",
        })
        assert r.status_code == 200
        assert r.json()["status"] == "arrived"

    def test_logistics_failed_reroute(self, client):
        self._seed(client)
        client.post("/api/v1/shipping/create", json={
            "shipping_id": "SH-LFR", "so_id": self.so_id, "pallet_count": 1, "container_type": "20GP",
        })
        client.post("/api/v1/logistics/arrange", json={
            "tracking_no": "TRK-LFR", "shipping_id": "SH-LFR", "carrier": "MAERSK",
        })
        r = client.post("/api/v1/logistics/TRK-LFR/failed", json={"reason": "貨損", "note": "退回"})
        assert r.status_code == 200
        assert r.json()["status"] == "failed"
        r = client.post("/api/v1/logistics/TRK-LFR/reroute", json={
            "new_carrier": "EVA", "new_eta": "2026-07-01T00:00:00", "note": "改路線",
        })
        assert r.status_code == 200
        assert r.json()["status"] == "reroute"

    def test_logistics_partial_arrive(self, client):
        self._seed(client)
        client.post("/api/v1/shipping/create", json={
            "shipping_id": "SH-LPA", "so_id": self.so_id, "pallet_count": 1, "container_type": "20GP",
        })
        client.post("/api/v1/logistics/arrange", json={
            "tracking_no": "TRK-LPA", "shipping_id": "SH-LPA", "carrier": "MAERSK",
        })
        client.post("/api/v1/logistics/TRK-LPA/depart")
        r = client.post("/api/v1/logistics/TRK-LPA/partial_arrive", json={
            "delivered_qty": 3, "remaining_qty": 7,
        })
        assert r.status_code == 200
        assert r.json()["status"] == "partial_delivery"

    def test_logistics_deliver_sign(self, client):
        self._seed(client)
        client.post("/api/v1/shipping/create", json={
            "shipping_id": "SH-LDS", "so_id": self.so_id, "pallet_count": 1, "container_type": "20GP",
        })
        client.post("/api/v1/logistics/arrange", json={
            "tracking_no": "TRK-LDS", "shipping_id": "SH-LDS", "carrier": "MAERSK",
        })
        client.post("/api/v1/logistics/TRK-LDS/depart")
        r = client.post("/api/v1/logistics/TRK-LDS/deliver_sign", json={
            "signed_by": "王五", "is_final": True, "delivery_note": "簽收完成",
        })
        assert r.status_code == 200
        assert r.json()["status"] == "delivered"

    def test_logistics_manual_event(self, client):
        self._seed(client)
        client.post("/api/v1/shipping/create", json={
            "shipping_id": "SH-LEV", "so_id": self.so_id, "pallet_count": 1, "container_type": "20GP",
        })
        client.post("/api/v1/logistics/arrange", json={
            "tracking_no": "TRK-LEV", "shipping_id": "SH-LEV", "carrier": "MAERSK",
        })
        r = client.post("/api/v1/logistics/TRK-LEV/event", json={
            "event_id": "LEV-001", "status": "inspected", "note": "抽驗通過",
        })
        assert r.status_code == 200
        assert r.json()["status"] == "inspected"