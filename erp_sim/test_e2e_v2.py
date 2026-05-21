"""
OTD v2.0 深化測試套件 — Shipping / Invoice / Logistics
覆蓋 Spec TC-06/07/08 各 6 子測試（共 18 個）

執行：cd otd_erp_sim && python3 test_e2e_v2.py
"""

import json
import time
import requests

BASE = "http://localhost:8001"
PASS = 0
FAIL = 0


def req(method, path, **kwargs):
    url = f"{BASE}{path}"
    r = requests.request(method, url, **kwargs)
    return r


def ok(r, expected=200):
    global PASS, FAIL
    if r.status_code == expected:
        PASS += 1
        return r.json()
    FAIL += 1
    print(f"    ❌ Expected {expected}, got {r.status_code}: {r.text[:300]}")
    return r.json() if r.headers.get("content-type", "").startswith("application/json") else {}


def check(msg, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {msg}")
    else:
        FAIL += 1
        print(f"  ❌ {msg}")


# ════════════════════════════════════════════════════════════════════════════
# Shared seed data
# ════════════════════════════════════════════════════════════════════════════

def seed():
    for item in [
        {"item_code": "V2-SKU-001", "description": "V2 Test Item A", "lead_time_days": 5, "safety_stock": 500},
        {"item_code": "V2-SKU-002", "description": "V2 Test Item B", "lead_time_days": 10, "safety_stock": 300},
    ]:
        req("POST", "/api/v1/items", json=item)
    req("POST", "/api/v1/customers", json={"customer_id": "V2-CUST", "name": "V2 Test Customer", "terms": "Net30"})
    req("POST", "/api/v1/po", json={
        "po_id": "V2-PO-001", "customer_id": "V2-CUST",
        "lines": [
            {"item_code": "V2-SKU-001", "qty": 200, "unit_price": 50.0, "line_no": 1},
            {"item_code": "V2-SKU-002", "qty": 100, "unit_price": 30.0, "line_no": 2},
        ],
    })
    req("POST", "/api/v1/po/V2-PO-001/convert", params={"so_id": "V2-SO-001"})
    req("POST", "/api/v1/shipping/create", json={
        "shipping_id": "V2-SHP-001", "so_id": "V2-SO-001",
        "pallet_count": 2, "container_type": "40HQ", "ship_from_location": "Factory A",
    })


# ════════════════════════════════════════════════════════════════════════════
# TC-06 深化：Shipping 6 子測試
# ════════════════════════════════════════════════════════════════════════════

def test_6a_pack_detail():
    """TC-06a 包裝明細建立與查詢"""
    print("\n=== TC-06a 包裝明細 ===")
    r = req("PATCH", "/api/v1/shipping/V2-SHP-001/pack_detail", json=[
        {"pallet_no": 1, "line_no": 1, "item_code": "V2-SKU-001", "qty_packed": 100, "weight_kg": 10.5, "dimensions_cm": "120×80×60"},
        {"pallet_no": 2, "line_no": 2, "item_code": "V2-SKU-002", "qty_packed": 50, "weight_kg": 8.0, "dimensions_cm": "100×60×50"},
    ])
    ship = ok(r)
    check("packing status", ship["status"] == "packing")

    r = req("GET", "/api/v1/shipping/V2-SHP-001/pack_detail")
    details = ok(r)
    check("2 pallets", len(details) == 2)
    check("pallet 1 weight", details[0]["weight_kg"] == 10.5)


def test_6b_partial_pack():
    """TC-06b 部分包裝"""
    print("\n=== TC-06b 部分包裝 ===")
    r = req("PATCH", "/api/v1/shipping/V2-SHP-001/pack_partial", json=[
        {"pallet_no": 3, "line_no": 1, "item_code": "V2-SKU-001", "qty_packed": 100, "weight_kg": 10.5},
    ])
    ship = ok(r)
    check("partial_packed status", ship["status"] == "partial_packed")


def test_6c_partial_ship_deliver():
    """TC-06c 部分出貨 + 部分到貨"""
    print("\n=== TC-06c 部分出貨/到貨 ===")
    # ship pack_detail first to transition to packed
    req("PATCH", "/api/v1/shipping/V2-SHP-001/pack_detail", json=[
        {"pallet_no": 1, "line_no": 1, "item_code": "V2-SKU-001", "qty_packed": 200, "weight_kg": 21.0},
    ])
    r = req("PATCH", "/api/v1/shipping/V2-SHP-001/ship", params={"tracking_no": "V2-TRK-001"})
    ship = ok(r)
    check("shipped", ship["status"] == "shipped")

    r = req("PATCH", "/api/v1/shipping/V2-SHP-001/partial_deliver", json={
        "delivered_qty": 100, "remaining_qty": 100, "remarks": "第一批到貨"
    })
    ship = ok(r)
    check("partial_delivery", ship["status"] == "partial_delivery")


def test_6d_delivery_proof():
    """TC-06d 簽收證明"""
    print("\n=== TC-06d 簽收證明 ===")
    r = req("POST", "/api/v1/shipping/V2-SHP-001/attach", json={
        "attachment_id": "V2-ATT-001", "type": "pod", "filename": "pod_20260521.pdf",
        "url": "/uploads/pod_20260521.pdf", "uploaded_by": "forge",
    })
    att = ok(r)
    check("attachment created", att["type"] == "pod")

    r = req("GET", "/api/v1/shipping/V2-SHP-001/attachments")
    atts = ok(r)
    check("attachments count", len(atts) >= 1)


def test_6e_status_protection():
    """TC-06e Shipping 狀態機保護"""
    print("\n=== TC-06e 狀態機保護 ===")
    # pending → packed (illegal, must go through packing)
    req("POST", "/api/v1/shipping/create", json={
        "shipping_id": "V2-SHP-002", "so_id": "V2-SO-001",
    })
    # Try to ship from pending without packing
    r = req("PATCH", "/api/v1/shipping/V2-SHP-002/ship", params={"tracking_no": "V2-TRK-002"})
    check("pending→shipped blocked", r.status_code == 400)

    # Try deliver before ship
    r = req("PATCH", "/api/v1/shipping/V2-SHP-002/deliver", json={})
    check("pending→deliver blocked", r.status_code >= 400)


def test_6f_shipping_lines():
    """TC-06f Shipping SO lines 查詢"""
    print("\n=== TC-06f Shipping SO lines ===")
    r = req("GET", "/api/v1/shipping/V2-SHP-001/lines")
    lines = ok(r)
    check("2 SO lines", len(lines) == 2)


# ════════════════════════════════════════════════════════════════════════════
# TC-07 深化：Invoice 6 子測試
# ════════════════════════════════════════════════════════════════════════════

def test_7a_invoice_lifecycle():
    """TC-07a 發票生命週期 draft→issued→sent→paid"""
    print("\n=== TC-07a 發票生命週期 ===")
    r = req("POST", "/api/v1/invoice/create", json={
        "invoice_id": "V2-INV-001", "so_id": "V2-SO-001", "amount": 13000.0,
        "tax_amount": 619.05, "currency": "USD", "due_date": "2026-07-15T00:00:00",
        "lines": [
            {"line_no": 1, "item_code": "V2-SKU-001", "description": "Item A", "qty": 200, "unit_price": 50},
            {"line_no": 2, "item_code": "V2-SKU-002", "description": "Item B", "qty": 100, "unit_price": 30},
        ],
    })
    inv = ok(r)
    check("draft", inv["status"] == "draft")

    r = req("PATCH", "/api/v1/invoice/V2-INV-001/issue", json={"invoice_no": "INV-2026-001"})
    inv = ok(r)
    check("issued", inv["status"] == "issued")

    r = req("POST", "/api/v1/invoice/V2-INV-001/send")
    inv = ok(r)
    check("sent", inv["status"] == "sent")

    r = req("POST", "/api/v1/invoice/V2-INV-001/payment", json={"payment_ref": "WIRE-001"})
    inv = ok(r)
    check("paid", inv["status"] == "paid")

    r = req("GET", "/api/v1/invoice/V2-INV-001/lines")
    lines = ok(r)
    check("2 invoice lines", len(lines) == 2)


def test_7b_overdue():
    """TC-07b 逾期查詢（auto-mark）"""
    print("\n=== TC-07b 逾期查詢 ===")
    # Create invoice with past due date
    req("POST", "/api/v1/invoice/create", json={
        "invoice_id": "V2-INV-002", "so_id": "V2-SO-001", "amount": 1000,
        "due_date": "2026-05-01T00:00:00",
    })
    req("PATCH", "/api/v1/invoice/V2-INV-002/issue")
    req("POST", "/api/v1/invoice/V2-INV-002/send")

    r = req("GET", "/api/v1/invoice/overdue", params={"days_overdue": 1})
    overdue = ok(r)
    check("overdue found", len(overdue) >= 1)
    if overdue:
        check("auto-marked overdue", overdue[0]["status"] in ("overdue", "dunning"))


def test_7c_void():
    """TC-07c 作廢流程"""
    print("\n=== TC-07c 作廢流程 ===")
    req("POST", "/api/v1/invoice/create", json={
        "invoice_id": "V2-INV-003", "so_id": "V2-SO-001", "amount": 500,
    })
    req("PATCH", "/api/v1/invoice/V2-INV-003/issue")

    r = req("PATCH", "/api/v1/invoice/V2-INV-003/void", json={"void_reason": "客戶取消訂單"})
    inv = ok(r)
    check("void", inv["status"] == "void")
    check("void reason stored", inv["void_reason"] == "客戶取消訂單")


def test_7d_credit_note():
    """TC-07d 折讓單"""
    print("\n=== TC-07d 折讓單 ===")
    r = req("POST", "/api/v1/invoice/V2-INV-001/credit", json={
        "credit_note_for": "V2-INV-001", "amount": 1000, "reason": "品質異常折讓"
    })
    cn = ok(r)
    check("credit_note", cn["status"] == "credit_note")
    check("credited link", cn["credit_note_for"] == "V2-INV-001")


def test_7e_by_so():
    """TC-07e 依 SO 查詢關聯發票"""
    print("\n=== TC-07e 依 SO 查詢 ===")
    r = req("GET", "/api/v1/invoice/by_so/V2-SO-001")
    invs = ok(r)
    check("multiple invoices", len(invs) >= 2)


def test_7f_multi_line_invoice():
    """TC-07f 多品項發票金額驗證"""
    print("\n=== TC-07f 多品項金額驗證 ===")
    r = req("GET", "/api/v1/invoice/V2-INV-001/lines")
    lines = ok(r)
    total = sum(l["amount"] for l in lines)
    check(f"total={total}", abs(total - 200 * 50 - 100 * 30) < 0.01)


# ════════════════════════════════════════════════════════════════════════════
# TC-08 深化：Logistics 6 子測試
# ════════════════════════════════════════════════════════════════════════════

def test_8a_full_trace():
    """TC-08a 物流狀態機全鏈"""
    print("\n=== TC-08a 物流全鏈 ===")
    r = req("POST", "/api/v1/logistics/arrange", json={
        "tracking_no": "V2-TRK-001", "shipping_id": "V2-SHP-001",
        "carrier": "DHL", "origin_port": "Shanghai", "dest_port": "Los Angeles",
    })
    lg = ok(r)
    check("booked", lg["status"] == "booked")

    r = req("POST", "/api/v1/logistics/V2-TRK-001/depart", json={"origin_port": "SH", "vessel_flight": "DHL-FL-001"})
    lg = ok(r)
    check("in_transit after depart", lg["status"] == "in_transit")

    r = req("POST", "/api/v1/logistics/V2-TRK-001/customs", json={"dest_port": "LA", "customs_status": "cleared", "bl_number": "BL-001"})
    lg = ok(r)
    check("customs", lg["status"] == "customs")

    r = req("POST", "/api/v1/logistics/V2-TRK-001/customs_clear")
    lg = ok(r)
    check("in_transit after clear", lg["status"] == "in_transit")

    r = req("POST", "/api/v1/logistics/V2-TRK-001/arrive")
    lg = ok(r)
    check("arrived", lg["status"] == "arrived")


def test_8b_customs_hold():
    """TC-08b 海關扣留異常路徑"""
    print("\n=== TC-08b 海關扣留 ===")
    req("POST", "/api/v1/logistics/arrange", json={
        "tracking_no": "V2-TRK-003", "shipping_id": "V2-SHP-002",
        "carrier": "FedEx",
    })
    req("POST", "/api/v1/logistics/V2-TRK-003/depart")
    req("POST", "/api/v1/logistics/V2-TRK-003/customs", json={"dest_port": "NY", "customs_status": "cleared"})

    r = req("POST", "/api/v1/logistics/V2-TRK-003/customs_hold", json={"reason": "文件不全"})
    lg = ok(r)
    check("customs_hold", lg["status"] == "customs_hold")
    check("held status", lg["customs_status"] == "held")

    r = req("POST", "/api/v1/logistics/V2-TRK-003/customs_clear", json={"note": "補件後放行"})
    lg = ok(r)
    check("cleared after hold", lg["status"] == "in_transit")


def test_8c_partial_delivery():
    """TC-08c 分批到貨"""
    print("\n=== TC-08c 分批到貨 ===")
    r = req("POST", "/api/v1/logistics/V2-TRK-003/arrive")
    lg = ok(r)

    r2 = req("POST", "/api/v1/logistics/V2-TRK-003/partial_arrive", json={
        "delivered_qty": 50, "remaining_qty": 150, "note": "第一批到貨"
    })
    lg2 = ok(r2)
    check("partial_delivery", lg2["status"] == "partial_delivery")


def test_8d_failed_reroute():
    """TC-08d 配送失敗 → 重新安排"""
    print("\n=== TC-08d 失敗重排 ===")
    req("POST", "/api/v1/logistics/arrange", json={
        "tracking_no": "V2-TRK-004", "shipping_id": "V2-SHP-002",
        "carrier": "UPS",
    })
    req("POST", "/api/v1/logistics/V2-TRK-004/depart")

    r = req("POST", "/api/v1/logistics/V2-TRK-004/failed", json={
        "reason": "地址錯誤", "note": "無法送達"
    })
    lg = ok(r)
    check("failed", lg["status"] == "failed")

    r = req("POST", "/api/v1/logistics/V2-TRK-004/reroute", json={
        "new_carrier": "FedEx", "note": "更正地址後重送"
    })
    lg = ok(r)
    check("reroute", lg["status"] == "reroute")
    check("carrier changed", lg["carrier"] == "FedEx")


def test_8e_event_trail():
    """TC-08e 物流事件軌跡"""
    print("\n=== TC-08e 事件軌跡 ===")
    r = req("GET", "/api/v1/logistics/V2-TRK-001/events")
    events = ok(r)
    check("5+ events", len(events) >= 5)
    chain = [e["status"] for e in events]
    check(f"chain: {chain}", "booked" in chain and "arrived" in chain)
    # verify chronological order
    times = [e["event_at"] for e in events]
    check("chronological", times == sorted(times))


def test_8f_by_shipping():
    """TC-08f 依出貨單查詢關聯物流"""
    print("\n=== TC-08f by_shipping ===")
    r = req("GET", "/api/v1/logistics/by_shipping/V2-SHP-001")
    lg = ok(r)
    check("tracking match", lg["tracking_no"] == "V2-TRK-001")


# ════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 60)
    print("OTD v2.0 深化測試套件 — Shipping / Invoice / Logistics")
    print("=" * 60)
    print("(Ensuring server is running at http://localhost:8001)")
    print()

    # Pre-flight
    try:
        r = req("GET", "/healthz")
        check("server healthy", r.json().get("ok"))
    except Exception:
        print("❌ Server not reachable. Start with: python3 -m uvicorn main:app --port 8001")
        exit(1)

    print("\n--- Seeding data ---")
    try:
        seed()
        check("seed complete", True)
    except Exception as e:
        check(f"seed failed: {e}", False)

    tests = [
        ("TC-06a 包裝明細", test_6a_pack_detail),
        ("TC-06b 部分包裝", test_6b_partial_pack),
        ("TC-06c 部分出貨/到貨", test_6c_partial_ship_deliver),
        ("TC-06d 簽收證明", test_6d_delivery_proof),
        ("TC-06e 狀態機保護", test_6e_status_protection),
        ("TC-06f SO lines 查詢", test_6f_shipping_lines),
        ("TC-07a 發票生命週期", test_7a_invoice_lifecycle),
        ("TC-07b 逾期查詢", test_7b_overdue),
        ("TC-07c 作廢", test_7c_void),
        ("TC-07d 折讓單", test_7d_credit_note),
        ("TC-07e SO 查詢", test_7e_by_so),
        ("TC-07f 金額驗證", test_7f_multi_line_invoice),
        ("TC-08a 物流全鏈", test_8a_full_trace),
        ("TC-08b 海關扣留", test_8b_customs_hold),
        ("TC-08c 分批到貨", test_8c_partial_delivery),
        ("TC-08d 失敗重排", test_8d_failed_reroute),
        ("TC-08e 事件軌跡", test_8e_event_trail),
        ("TC-08f by_shipping", test_8f_by_shipping),
    ]

    for name, fn in tests:
        try:
            fn()
        except Exception as e:
            import traceback
            print(f"\n  ❌ EXCEPTION in {name}: {e}")
            traceback.print_exc()
            FAIL += 1

    print("\n" + "=" * 60)
    print(f"結果: {PASS} 通過 / {FAIL} 失敗  (共 {PASS + FAIL} checks)")
    print("=" * 60)
    exit(0 if FAIL == 0 else 1)