"""
OTD 端對端整合測試
覆蓋完整流程：詢單 → ATP/CTP → PO → PO→SO → SO → Pick/Pack/Ship → Invoice → Logistics

執行：cd otd_erp_sim && python3 test_e2e.py
"""

import os
import requests

BASE = os.environ.get("BASE_URL", "http://100.107.36.80:8004")

def req(method, path, **kwargs):
    url = f"{BASE}{path}"
    r = requests.request(method, url, **kwargs)
    print(f"  {method} {path} → {r.status_code}")
    if r.status_code >= 400:
        print(f"    ERROR: {r.text[:300]}")
    return r


def ok(r, expected=200):
    assert r.status_code == expected, f"Expected {expected}, got {r.status_code}: {r.text[:200]}"
    return r.json()


# ════════════════════════════════════════════════════════════════════════════
# 測試套件
# ════════════════════════════════════════════════════════════════════════════

def test_1_health():
    """TC-01 健康檢查"""
    print("\n=== TC-01 健康檢查 ===")
    r = req("GET", "/healthz")
    assert r.json()["ok"] is True
    print("  ✅ 伺服器正常")


def test_2_items_and_customers():
    """TC-02 建立料號與客戶（基礎資料）"""
    print("\n=== TC-02 料號與客戶 ===")

    for item in [
        {"item_code": "E2E-SKU-001", "description": "整合測試料號 A", "unit": "PC", "lead_time_days": 7,  "safety_stock": 500},
        {"item_code": "E2E-SKU-002", "description": "整合測試料號 B", "unit": "PC", "lead_time_days": 10, "safety_stock": 300},
        {"item_code": "E2E-SKU-003", "description": "整合測試外殼",   "unit": "SET", "lead_time_days": 14, "safety_stock": 200},
    ]:
        r = req("POST", "/api/v1/items", json=item)

    r = req("POST", "/api/v1/customers", json={
        "customer_id": "E2E-CUST-001", "name": "整合測試客戶", "terms": "Net30"
    })
    ok(r)
    print("  ✅ 料號與客戶建立完成")


def test_3_atp_ctp():
    """TC-03 ATP / CTP 交期試算"""
    print("\n=== TC-03 ATP/CTP 交期試算 ===")

    # ATP 正常
    r = req("POST", "/api/v1/atp/check", json={
        "item_code": "E2E-SKU-001", "qty": 100,
        "request_date": "2026-06-15T00:00:00"
    })
    atp = ok(r)
    assert atp["result"] in ("on_time", "delayed", "insufficient")
    print(f"  ATP: {atp['result']} → {atp['remarks']}")

    # CTP
    r = req("POST", "/api/v1/ctp/check", json={
        "item_code": "E2E-SKU-001", "qty": 100,
        "request_date": "2026-06-15T00:00:00"
    })
    ctp = ok(r)
    print(f"  CTP: {ctp['result']} → {ctp['remarks']}")

    # ATP 庫存不足
    r = req("POST", "/api/v1/atp/check", json={
        "item_code": "E2E-SKU-001", "qty": 9999,
        "request_date": "2026-06-15T00:00:00"
    }, params={"force_insufficient": "true"})
    atp_bad = ok(r)
    assert atp_bad["result"] == "insufficient"
    print(f"  ATP 不足: {atp_bad['remarks']}")

    print("  ✅ ATP/CTP 試算完成")


def test_4_po_lifecycle():
    """TC-04 PO 建立 → 查詢 → 轉 SO"""
    print("\n=== TC-04 PO 生命週期 ===")

    r = req("POST", "/api/v1/po", json={
        "po_id": "E2E-PO-001",
        "customer_id": "E2E-CUST-001",
        "lines": [
            {"item_code": "E2E-SKU-001", "qty": 100, "unit_price": 50.0, "line_no": 1},
            {"item_code": "E2E-SKU-002", "qty": 200, "unit_price": 30.0, "line_no": 2},
            {"item_code": "E2E-SKU-003", "qty": 50,  "unit_price": 100.0, "line_no": 3},
        ],
    })
    po = ok(r)
    assert po["status"] == "pending"
    print(f"  PO 建立: {po['po_id']} status={po['status']}")

    r = req("GET", "/api/v1/po/E2E-PO-001/lines")
    lines = ok(r)
    assert len(lines) == 3
    print(f"  PO lines: {len(lines)} 筆")

    r = req("POST", "/api/v1/po/E2E-PO-001/convert", params={"so_id": "E2E-SO-001"})
    so = ok(r)
    assert so["status"] == "draft"
    assert so["po_id"] == "E2E-PO-001"
    print(f"  PO→SO: SO={so['so_id']} status={so['status']}")

    r = req("GET", "/api/v1/po/E2E-PO-001")
    po2 = ok(r)
    assert po2["status"] == "converted"
    print("  PO status: converted ✅")

    print("  ✅ PO 生命週期完成")


def test_5_so_lifecycle():
    """TC-05 SO 狀態機流轉"""
    print("\n=== TC-05 SO 生命週期 ===")

    r = req("GET", "/api/v1/so/E2E-SO-001/lines")
    lines = ok(r)
    assert len(lines) == 3
    print(f"  SO lines: {len(lines)} 筆")

    r = req("PATCH", "/api/v1/so/E2E-SO-001", params={"status": "confirmed"})
    so = ok(r)
    assert so["status"] == "confirmed"
    print("  SO confirmed ✅")

    r = req("PATCH", "/api/v1/so/E2E-SO-001", params={"status": "partial"})
    so = ok(r)
    assert so["status"] == "partial"
    print("  SO partial ✅")

    print("  ✅ SO 狀態流轉完成")


def test_6_shipping():
    """TC-06 Pick / Pack / Ship"""
    print("\n=== TC-06 出貨流程 ===")

    r = req("POST", "/api/v1/shipping/create", json={
        "shipping_id": "E2E-SHP-001",
        "so_id": "E2E-SO-001",
        "pallet_count": 2,
        "container_type": "20GP",
        "customs_date": "2026-06-20T00:00:00",
    })
    ship = ok(r)
    assert ship["status"] == "pending"
    print(f"  出貨單: {ship['shipping_id']} status={ship['status']}")

    r = req("PATCH", "/api/v1/shipping/E2E-SHP-001/pack", params={"pallet_count": 3})
    ship = ok(r)
    assert ship["status"] == "packing"
    print(f"  包裝: pallets={ship['pallet_count']}")

    r = req("PATCH", "/api/v1/shipping/E2E-SHP-001/ship", params={"tracking_no": "E2E-TRK-001"})
    ship = ok(r)
    assert ship["status"] == "shipped"
    print(f"  出貨: tracking={ship['tracking_no']}")

    print("  ✅ 出貨流程完成")


def test_7_invoice():
    """TC-07 發票"""
    print("\n=== TC-07 發票 ===")

    r = req("POST", "/api/v1/invoice/create", json={
        "invoice_id": "E2E-INV-001",
        "shipping_id": "E2E-SHP-001",
        "so_id": "E2E-SO-001",
        "amount": 21000.0,
    })
    inv = ok(r)
    assert inv["status"] == "draft"
    print(f"  發票 draft: {inv['invoice_id']} amount={inv['amount']}")

    # draft → issued
    r = req("PATCH", "/api/v1/invoice/E2E-INV-001/issue")
    inv = ok(r)
    assert inv["status"] == "issued"
    print(f"  開立: status={inv['status']}")

    # send
    r = req("POST", "/api/v1/invoice/E2E-INV-001/send")
    inv = ok(r)
    assert inv["status"] == "sent"
    print(f"  寄送: status={inv['status']}")

    r = req("GET", "/api/v1/invoice/E2E-INV-001")
    ok(r)
    print("  發票查詢 ✅")
    print("  ✅ 發票完成")


def test_8_logistics():
    """TC-08 物流追蹤 → 到貨"""
    print("\n=== TC-08 物流 ===")

    r = req("POST", "/api/v1/logistics/arrange", json={
        "tracking_no": "E2E-TRK-001",
        "shipping_id": "E2E-SHP-001",
        "carrier": "整合測試物流",
        "eta": "2026-06-25T00:00:00",
    })
    lg = ok(r)
    assert lg["status"] == "booked"
    print(f"  物流: {lg['tracking_no']} status={lg['status']}")

    r = req("POST", "/api/v1/logistics/E2E-TRK-001/arrive")
    lg2 = ok(r)
    assert lg2["status"] == "arrived"
    print(f"  到貨: status={lg2['status']}")

    r = req("GET", "/api/v1/shipping/E2E-SHP-001")
    ship = ok(r)
    assert ship["status"] == "delivered"
    print("  出貨單同步: delivered ✅")
    print("  ✅ 物流完成")


def test_9_validation():
    """TC-09 資料驗證保護"""
    print("\n=== TC-09 資料驗證 ===")

    r = req("POST", "/api/v1/po", json={
        "po_id": "E2E-PO-001", "customer_id": "E2E-CUST-001", "lines": []
    })
    assert r.status_code == 400
    print("  重複 PO 阻擋 ✅")

    r = req("POST", "/api/v1/invoice/create", json={
        "invoice_id": "E2E-INV-001", "so_id": "E2E-SO-001", "amount": 1
    })
    assert r.status_code == 400
    print("  重複發票阻擋 ✅")

    r = req("POST", "/api/v1/atp/check", json={
        "item_code": "NO-ITEM", "qty": 1, "request_date": "2026-06-15T00:00:00"
    })
    assert r.status_code == 404
    print("  不存在料號阻擋 ✅")

    print("  ✅ 驗證保護完成")


def test_10_full_trace():
    """TC-10 全流程資料關聯驗證"""
    print("\n=== TC-10 全流程關聯驗證 ===")

    r = req("GET", "/api/v1/po/E2E-PO-001")
    po = ok(r)
    r = req("GET", "/api/v1/so/E2E-SO-001")
    so = ok(r)
    r = req("GET", "/api/v1/shipping/E2E-SHP-001")
    ship = ok(r)
    r = req("GET", "/api/v1/invoice/E2E-INV-001")
    inv = ok(r)
    r = req("GET", "/api/v1/logistics/E2E-TRK-001")
    lg = ok(r)

    checks = [
        ("PO→SO",    so["po_id"] == "E2E-PO-001"),
        ("SO→出貨",  ship["so_id"] == "E2E-SO-001"),
        ("SO→發票",  inv["so_id"] == "E2E-SO-001"),
        ("發票→出貨", inv["shipping_id"] == "E2E-SHP-001"),
        ("出貨→物流", lg["shipping_id"] == "E2E-SHP-001"),
    ]
    for name, passed in checks:
        print(f"  {name}: {'✅' if passed else '❌'}")
        assert passed

    print("  ✅ 全流程關聯驗證通過")


# ════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 60)
    print("OTD 端對端整合測試")
    print("=" * 60)

    passed = 0
    failed = 0

    for name, fn in [
        ("TC-01 健康檢查", test_1_health),
        ("TC-02 料號與客戶", test_2_items_and_customers),
        ("TC-03 ATP/CTP", test_3_atp_ctp),
        ("TC-04 PO 生命週期", test_4_po_lifecycle),
        ("TC-05 SO 生命週期", test_5_so_lifecycle),
        ("TC-06 出貨流程", test_6_shipping),
        ("TC-07 發票", test_7_invoice),
        ("TC-08 物流", test_8_logistics),
        ("TC-09 資料驗證", test_9_validation),
        ("TC-10 全流程關聯", test_10_full_trace),
    ]:
        try:
            fn()
            passed += 1
        except Exception:
            import traceback; traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"結果: {passed} 通過 / {failed} 失敗")
    print("=" * 60)
    exit(0 if failed == 0 else 1)
