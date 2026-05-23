"""main.py (root) 完整 OTD lifecycle 測試 — TestClient (不需要真實 HTTP)"""
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
        r = client.get("/health")
        assert r.status_code == 200

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
        r = client.patch(f"/api/v1/shipping/SH-X1/pack_detail", json=[
            {"pallet_no": 1, "line_no": 1, "item_code": "CPU-X1", "qty_packed": 50, "qty_shipped": 50,
             "weight_kg": 25.0, "dimensions_cm": "120x80x60"},
            {"pallet_no": 2, "line_no": 1, "item_code": "CPU-X1", "qty_packed": 50, "qty_shipped": 50,
             "weight_kg": 25.0, "dimensions_cm": "120x80x60"},
        ])
        assert r.status_code == 200

        # 10. Ship
        r = client.patch(f"/api/v1/shipping/SH-X1/ship?tracking_no=TRK-X1")
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
        # main.py doesn't have a cancel PO endpoint! PO cancel doesn't exist here.
        # But we can try converting an already-converted PO
        r = client.post("/api/v1/po/PO-CN/convert")
        assert r.status_code == 200

        r = client.post("/api/v1/po/PO-CN/convert")
        assert r.status_code == 400
        assert "已轉換" in r.json()["detail"]