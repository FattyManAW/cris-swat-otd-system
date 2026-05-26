"""Item / Customer / PO / SO / ATP / CTP CRUD tests — erp_sim/main.py API 覆蓋"""


class TestItemCRUD:
    def test_create_item(self, client):
        r = client.post("/api/v1/items", json={
            "item_code": "CPU-002",
            "description": "高階 CPU",
            "unit": "PC",
            "category": "cpu",
            "lead_time_days": 7,
            "safety_stock": 50,
            "daily_capacity": 200,
        })
        assert r.status_code == 200
        assert r.json()["item_code"] == "CPU-002"

    def test_create_duplicate_item(self, client, seed_item):
        r = client.post("/api/v1/items", json={
            "item_code": "CPU-001",
            "description": "重複",
            "unit": "PC",
            "lead_time_days": 5,
            "safety_stock": 100,
            "daily_capacity": 500,
        })
        assert r.status_code == 400
        assert "已存在" in r.json()["detail"]

    def test_list_items(self, client, seed_item):
        r = client.get("/api/v1/items")
        assert r.status_code == 200
        items = r.json()
        assert len(items) >= 1
        assert items[0]["item_code"] == "CPU-001"

    def test_get_item(self, client, seed_item):
        r = client.get("/api/v1/items/CPU-001")
        assert r.status_code == 200
        assert r.json()["description"] == "測試 CPU"

    def test_get_item_not_found(self, client):
        r = client.get("/api/v1/items/NONEXIST")
        assert r.status_code == 404


class TestCustomerCRUD:
    def test_create_customer(self, client):
        r = client.post("/api/v1/customers", json={
            "customer_id": "CUST-002",
            "name": "新客戶",
            "terms": "Net30",
        })
        assert r.status_code == 200
        assert r.json()["customer_id"] == "CUST-002"

    def test_create_duplicate_customer(self, client, seed_customer):
        r = client.post("/api/v1/customers", json={
            "customer_id": "CUST-001",
            "name": "重複客戶",
        })
        assert r.status_code == 400

    def test_list_customers(self, client, seed_customer):
        r = client.get("/api/v1/customers")
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_get_customer(self, client, seed_customer):
        r = client.get("/api/v1/customers/CUST-001")
        assert r.status_code == 200
        assert r.json()["name"] == "測試客戶"

    def test_get_customer_not_found(self, client):
        r = client.get("/api/v1/customers/NONEXIST")
        assert r.status_code == 404


class TestPOCRUD:
    def test_create_po(self, client, seed_item, seed_customer):
        r = client.post("/api/v1/po", json={
            "po_id": "PO-20260524-002",
            "customer_id": "CUST-001",
            "lines": [
                {"item_code": "CPU-001", "qty": 5, "unit_price": 99.0, "line_no": 1},
            ]
        })
        assert r.status_code == 200
        assert r.json()["po_id"] == "PO-20260524-002"
        assert r.json()["status"] == "pending"

    def test_create_po_missing_customer(self, client, seed_item):
        r = client.post("/api/v1/po", json={
            "po_id": "PO-NO-CUST",
            "customer_id": "NONEXIST",
            "lines": [{"item_code": "CPU-001", "qty": 1, "unit_price": 10.0, "line_no": 1}]
        })
        assert r.status_code == 400
        assert "客戶" in r.json()["detail"]

    def test_create_po_missing_item(self, client, seed_customer):
        r = client.post("/api/v1/po", json={
            "po_id": "PO-NO-ITEM",
            "customer_id": "CUST-001",
            "lines": [{"item_code": "NONEXIST", "qty": 1, "unit_price": 10.0, "line_no": 1}]
        })
        assert r.status_code == 400
        assert "料號" in r.json()["detail"]

    def test_list_pos(self, client, seed_po):
        r = client.get("/api/v1/po")
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_get_po(self, client, seed_po):
        r = client.get("/api/v1/po/PO-20260524-001")
        assert r.status_code == 200
        assert r.json()["customer_id"] == "CUST-001"

    def test_get_po_not_found(self, client):
        r = client.get("/api/v1/po/NONEXIST")
        assert r.status_code == 404

    def test_get_po_lines(self, client, seed_po):
        r = client.get("/api/v1/po/PO-20260524-001/lines")
        assert r.status_code == 200
        assert len(r.json()) == 2

    def test_po_convert_to_so(self, client, seed_po):
        r = client.post("/api/v1/po/PO-20260524-001/convert")
        assert r.status_code == 200
        data = r.json()
        assert data["po_id"] == "PO-20260524-001"
        assert "SO-" in data["so_id"]

        # PO 應該變成 converted
        r2 = client.get("/api/v1/po/PO-20260524-001")
        assert r2.json()["status"] == "converted"

        # 不能再轉一次
        r3 = client.post("/api/v1/po/PO-20260524-001/convert")
        assert r3.status_code == 400


class TestSOCRUD:
    def test_create_so_draft(self, client, seed_item, seed_customer):
        r = client.post("/api/v1/so", json={
            "so_id": "SO-20260524-002",
            "customer_id": "CUST-001",
            "po_id": None,
            "lines": [
                {"item_code": "CPU-001", "qty": 3, "unit_price": 150.0, "delivery_date": "2026-06-01T00:00:00", "line_no": 1},
            ]
        })
        assert r.status_code == 200
        assert r.json()["status"] == "draft"

    def test_create_so_with_po_mismatch(self, client, seed_item, seed_customer, seed_po):
        r = client.post("/api/v1/so", json={
            "so_id": "SO-MISMATCH",
            "customer_id": "WRONG-CUST",
            "po_id": "PO-20260524-001",
            "lines": [{"item_code": "CPU-001", "qty": 1, "unit_price": 10.0, "line_no": 1}]
        })
        # main.py 只在 po exists + customer mismatch 時才 raise
        # 但如果 WRONG-CUST 不存在呢？PO customer 是 CUST-001，SO customer 是 WRONG-CUST
        # code: if po and po.customer_id != data.customer_id → raise
        # 這會觸發 400
        # But WRONG-CUST 不在 DB，PO query 正常 → 會 raise
        # Actually...po.customer_id = "CUST-001", data.customer_id = "WRONG-CUST"
        # They differ → raise 400
        assert r.status_code == 400

    def test_list_sos(self, client, seed_po):
        # seed_po 尚未轉換，手動 create so
        client.post("/api/v1/so", json={
            "so_id": "SO-LIST-TEST", "customer_id": "CUST-001",
            "lines": [{"item_code": "CPU-001", "qty": 1, "unit_price": 10.0, "line_no": 1}]
        })
        r = client.get("/api/v1/so")
        assert r.status_code == 200
        assert len(r.json()) >= 1

    def test_get_so(self, client, seed_po):
        client.post("/api/v1/po/PO-20260524-001/convert")
        # SO id is auto-generated
        r_so = client.get("/api/v1/so")
        so_id = r_so.json()[0]["so_id"]
        r = client.get(f"/api/v1/so/{so_id}")
        assert r.status_code == 200
        assert r.json()["po_id"] == "PO-20260524-001"

    def test_get_so_not_found(self, client):
        r = client.get("/api/v1/so/NONEXIST")
        assert r.status_code == 404

    def test_update_so(self, client, seed_po):
        client.post("/api/v1/po/PO-20260524-001/convert")
        r_so = client.get("/api/v1/so")
        so_id = r_so.json()[0]["so_id"]

        r = client.patch(f"/api/v1/so/{so_id}", params={"status": "confirmed", "remarks": "已確認"})
        assert r.status_code == 200
        assert r.json()["status"] == "confirmed"
        assert r.json()["remarks"] == "已確認"


class TestATPCheck:
    def test_atp_on_time(self, client, seed_item):
        r = client.post("/api/v1/atp/check", json={
            "item_code": "CPU-001",
            "qty": 50,
            "request_date": "2026-06-01T00:00:00",
        })
        assert r.status_code == 200
        assert r.json()["result"] == "on_time"
        assert "可承諾" in r.json()["remarks"]

    def test_atp_insufficient(self, client, seed_item):
        r = client.post("/api/v1/atp/check", json={
            "item_code": "CPU-001",
            "qty": 999,
            "request_date": "2026-06-01T00:00:00",
        })
        assert r.status_code == 200
        assert r.json()["result"] == "insufficient"

    def test_atp_force_delay(self, client, seed_item):
        r = client.post("/api/v1/atp/check?force_delay=true", json={
            "item_code": "CPU-001",
            "qty": 50,
            "request_date": "2026-06-01T00:00:00",
        })
        assert r.status_code == 200
        assert r.json()["result"] == "delayed"

    def test_atp_item_not_found(self, client):
        r = client.post("/api/v1/atp/check", json={
            "item_code": "NONEXIST",
            "qty": 10,
            "request_date": "2026-06-01T00:00:00",
        })
        assert r.status_code == 404


class TestCTPCheck:
    def test_ctp_on_time(self, client, seed_item):
        r = client.post("/api/v1/ctp/check", json={
            "item_code": "CPU-001",
            "qty": 100,
            "request_date": "2026-06-01T00:00:00",
        })
        assert r.status_code == 200
        assert r.json()["result"] == "on_time"

    def test_ctp_delay(self, client, seed_item):
        r = client.post("/api/v1/ctp/check?force_delay=true", json={
            "item_code": "CPU-001",
            "qty": 100,
            "request_date": "2026-06-01T00:00:00",
        })
        assert r.status_code == 200
        assert r.json()["result"] == "delayed"

    def test_ctp_insufficient(self, client, seed_item):
        r = client.post("/api/v1/ctp/check", json={
            "item_code": "CPU-001",
            "qty": 9999,
            "request_date": "2026-06-01T00:00:00",
        })
        assert r.status_code == 200
        assert r.json()["result"] == "insufficient"
