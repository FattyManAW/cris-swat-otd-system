"""
Logistics Agent — 物流處理專家 (v2.0)

負責從出貨排程確認到到貨確認的全程物流流程，包含：
報關文件生成、出貨安排、在途追蹤與到貨確認。

v2.0: 串接 Shipping/Invoice/Logistics 深化端點
- depart / customs / customs_hold / customs_clear / partial_arrive / deliver_sign
- failed / reroute / event trail / active logistics

執行：python3 agent.py --demo
"""

import argparse
import json
import uuid
from datetime import datetime
from typing import Optional

import requests

ERP_BASE = "http://localhost:8001"
AGENT_NAME = "Logistics Agent"


class LogisticsAgent:
    """物流處理 Agent v2.0"""

    def __init__(self, erp_base: str = ERP_BASE):
        self.erp_base = erp_base

    def _post(self, path, payload=None, params=None):
        r = requests.post(f"{self.erp_base}{path}", json=payload or {}, params=params or {})
        r.raise_for_status()
        return r.json()

    def _get(self, path):
        r = requests.get(f"{self.erp_base}{path}")
        r.raise_for_status()
        return r.json()

    def _gen_tracking(self, schedule_id):
        suffix = schedule_id.split("-")[-1] if "-" in schedule_id else str(uuid.uuid4())[:8]
        return f"TRK-{suffix}"

    # ── Step 1：安排出貨物流 ──────────────────────────────────────────────

    def arrange_shipment(self, schedule_id: str, carrier: str = "auto",
                         origin_port: str = "", dest_port: str = "") -> dict:
        print(f"\n{'='*60}")
        print(f"[{AGENT_NAME}] 安排出貨物流")
        print(f"  排程：{schedule_id}  物流商：{carrier}")
        print(f"  起運港：{origin_port} → 目的港：{dest_port}")
        print(f"{'='*60}")

        shipping = self._get(f"/api/v1/shipping/{schedule_id}")
        if shipping.get("tracking_no"):
            print(f"  ℹ️ 已有追蹤號：{shipping['tracking_no']}，跳過安排")
            return self.track_shipment_full(shipping["tracking_no"])

        tracking_no = self._gen_tracking(schedule_id)
        print(f"  追蹤號：{tracking_no}")

        result = self._post("/api/v1/logistics/arrange", {
            "tracking_no": tracking_no,
            "shipping_id": shipping.get("shipping_id", ""),
            "carrier": carrier,
            "origin_port": origin_port,
            "dest_port": dest_port,
            "eta": shipping.get("customs_date"),
        })

        print(f"  ✅ 物流已安排 → {result.get('carrier')}")
        return {"event": "shipment_arranged", "tracking_no": tracking_no, **result}

    # ── Step 2：出發 → 通關 → 在途 → 到貨（v2.0 全鏈）──────────────────

    def depart(self, tracking_no: str, origin_port: str = "",
               vessel_flight: str = "") -> dict:
        print(f"\n[{AGENT_NAME}] 🚢 出發 {tracking_no}")
        return self._post(f"/api/v1/logistics/{tracking_no}/depart", {
            "origin_port": origin_port,
            "vessel_flight": vessel_flight,
        })

    def customs_start(self, tracking_no: str, dest_port: str = "",
                      bl_number: str = "") -> dict:
        print(f"\n[{AGENT_NAME}] 🛃 通關 {tracking_no}")
        return self._post(f"/api/v1/logistics/{tracking_no}/customs", {
            "dest_port": dest_port,
            "bl_number": bl_number,
            "customs_status": "cleared",
        })

    def customs_hold(self, tracking_no: str, reason: str) -> dict:
        print(f"\n[{AGENT_NAME}] ⚠️ 海關扣留 {tracking_no}: {reason}")
        return self._post(f"/api/v1/logistics/{tracking_no}/customs_hold", {
            "reason": reason,
        })

    def customs_clear(self, tracking_no: str, note: str = "") -> dict:
        print(f"\n[{AGENT_NAME}] ✅ 清關完成 {tracking_no}")
        return self._post(f"/api/v1/logistics/{tracking_no}/customs_clear", {
            "note": note,
        })

    def arrive(self, tracking_no: str, delivery_note: str = "") -> dict:
        print(f"\n[{AGENT_NAME}] 📦 到貨 {tracking_no}")
        return self._post(f"/api/v1/logistics/{tracking_no}/arrive", {
            "delivery_note": delivery_note,
        })

    def partial_arrive(self, tracking_no: str, delivered_qty: int,
                       remaining_qty: int) -> dict:
        print(f"\n[{AGENT_NAME}] 📦 分批到貨 {tracking_no}: {delivered_qty}/{delivered_qty + remaining_qty}")
        return self._post(f"/api/v1/logistics/{tracking_no}/partial_arrive", {
            "delivered_qty": delivered_qty,
            "remaining_qty": remaining_qty,
        })

    def deliver_sign(self, tracking_no: str, signed_by: str,
                     delivery_note: str = "") -> dict:
        print(f"\n[{AGENT_NAME}] ✍️ 簽收 {tracking_no} by {signed_by}")
        return self._post(f"/api/v1/logistics/{tracking_no}/deliver_sign", {
            "signed_by": signed_by,
            "delivery_note": delivery_note,
            "is_final": True,
        })

    def mark_failed(self, tracking_no: str, reason: str,
                    note: str = "") -> dict:
        print(f"\n[{AGENT_NAME}] ❌ 配送失敗 {tracking_no}: {reason}")
        return self._post(f"/api/v1/logistics/{tracking_no}/failed", {
            "reason": reason,
            "note": note,
        })

    def reroute(self, tracking_no: str, new_carrier: str = "",
                note: str = "") -> dict:
        print(f"\n[{AGENT_NAME}] 🔄 重新安排 {tracking_no} → {new_carrier}")
        return self._post(f"/api/v1/logistics/{tracking_no}/reroute", {
            "new_carrier": new_carrier,
            "note": note,
        })

    # ── Step 3：查詢 ───────────────────────────────────────────────────────

    def track_shipment(self, tracking_no: str) -> dict:
        print(f"\n[{AGENT_NAME}] 查詢物流 {tracking_no}")
        status = self._get(f"/api/v1/logistics/{tracking_no}")
        print(f"  狀態：{status.get('status')}  ETA：{status.get('eta', 'N/A')}")
        return {"event": "tracking_queried", **status}

    def track_shipment_full(self, tracking_no: str) -> dict:
        """查詢物流含事件軌跡"""
        status = self.track_shipment(tracking_no)
        events = self._get(f"/api/v1/logistics/{tracking_no}/events")
        chain = [e["status"] for e in events]
        print(f"  事件鏈 ({len(events)}): {' → '.join(chain)}")
        return {**status, "events": events, "chain": chain}

    def list_active(self, carrier: str = "") -> dict:
        print(f"\n[{AGENT_NAME}] 進行中物流" + (f" ({carrier})" if carrier else ""))
        params = {"carrier": carrier} if carrier else {}
        items = self._get("/api/v1/logistics/active")
        print(f"  共 {len(items)} 筆")
        for i in items:
            print(f"  - {i['tracking_no']} [{i['status']}] {i.get('carrier', 'N/A')}")
        return {"event": "active_listed", "count": len(items), "items": items}

    # ── Step 4：完整流程 ───────────────────────────────────────────────────

    def process_full(self, shipping_id: str, carrier: str = "DHL",
                     origin: str = "", dest: str = "", signed_by: str = "") -> dict:
        """一鍵執行完整物流鏈：arrange → depart → customs → clear → arrive → sign"""
        print(f"\n{'='*60}")
        print(f"[{AGENT_NAME}] 完整物流流程 v2.0")
        print(f"  出貨單：{shipping_id}")
        print(f"{'='*60}")

        steps = {}
        steps["arrange"] = self.arrange_shipment(shipping_id, carrier, origin, dest)
        tk = steps["arrange"]["tracking_no"]

        steps["depart"] = self.depart(tk, origin_port=origin)
        steps["customs"] = self.customs_start(tk, dest_port=dest)
        steps["clear"] = self.customs_clear(tk, "清關完成")
        steps["arrive"] = self.arrive(tk, "貨物已送達")
        if signed_by:
            steps["sign"] = self.deliver_sign(tk, signed_by)
        steps["trail"] = self.track_shipment_full(tk)

        print("\n  ✅ 物流全鏈完成")
        return {"event": "logistics_complete", "tracking_no": tk, "steps": steps}


def demo(agent):
    # 前置：建立每 demo 結束才清除的種子資料
    try:
        agent._post("/api/v1/items", {"item_code": "LGT-SKU", "description": "Demo Item", "lead_time_days": 5, "safety_stock": 100})
        agent._post("/api/v1/customers", {"customer_id": "LGT-CUST", "name": "Demo Customer"})
        agent._post("/api/v1/po", {"po_id": "LGT-PO-001", "customer_id": "LGT-CUST", "lines": [{"item_code": "LGT-SKU", "qty": 100, "unit_price": 50, "line_no": 1}]})
        agent._post("/api/v1/po/LGT-PO-001/convert", params={"so_id": "LGT-SO-001"})
        agent._post("/api/v1/shipping/create", {"shipping_id": "LGT-SHP-001", "so_id": "LGT-SO-001", "pallet_count": 2, "ship_from_location": "Factory A"})
        print("  ✅ 種子資料建立完成")
    except Exception:
        pass  # 可能已存在

    # 場景 1：安排出貨物流（v2.0 含 origin/dest）
    result = agent.arrange_shipment("LGT-SHP-001", "DHL", "Shanghai", "Los Angeles")
    tk = result.get("tracking_no", "TRK-E2E-001")
    print(f"\n  結果：{json.dumps({k: v for k, v in result.items() if k != 'status'}, ensure_ascii=False, indent=2)[:400]}...")

    # 場景 2：完整物流鏈（depart → customs → clear → arrive）
    agent.depart(tk, "Shanghai", "DHL-FL-001")
    agent.customs_start(tk, "Los Angeles", "BL-2026-001")
    agent.customs_clear(tk, "海關放行，繼續運輸")
    agent.arrive(tk, "已送達洛杉磯配送中心")

    # 場景 3：海關扣留異常
    print("\n▶ 異常場景：海關扣留")
    tk2 = "TRK-CUSTOMS-DEMO"
    agent._post("/api/v1/logistics/arrange", {
        "tracking_no": tk2, "shipping_id": "LGT-SHP-001", "carrier": "FedEx",
    })
    agent.depart(tk2, "Shanghai")
    agent.customs_start(tk2, "New York")
    agent.customs_hold(tk2, "文件不全，缺少產地證明")
    agent.customs_clear(tk2, "補件完成，海關放行")
    agent.arrive(tk2, "已送達")

    # 場景 4：配送失敗 → 重排
    print("\n▶ 異常場景：配送失敗 → 重排")
    tk3 = "TRK-FAIL-DEMO"
    agent._post("/api/v1/logistics/arrange", {
        "tracking_no": tk3, "shipping_id": "LGT-SHP-001", "carrier": "UPS",
    })
    agent.depart(tk3)
    agent.mark_failed(tk3, "地址錯誤", "收件地址不存在")
    agent.reroute(tk3, "FedEx", "更正地址後重新配送")

    # 場景 5：事件軌跡
    print("\n▶ 事件軌跡")
    agent.track_shipment_full(tk)

    # 場景 6：進行中物流
    agent.list_active()


def interactive(agent):
    print(f"{AGENT_NAME} v2.0 — 互動模式")
    print("指令:")
    print("  arrange <shipping_id> [carrier] [origin] [dest]")
    print("  depart <tk> [port] [vessel]")
    print("  customs <tk> [dest] [bl]")
    print("  hold <tk> <reason>")
    print("  clear <tk> [note]")
    print("  arrive <tk> [note]")
    print("  partial <tk> <delivered> <remaining>")
    print("  sign <tk> <signed_by> [note]")
    print("  fail <tk> <reason> [note]")
    print("  reroute <tk> [carrier] [note]")
    print("  track <tk>")
    print("  full <tk> [signed_by]")
    print("  active [carrier]")
    print("  full <shipping_id> [carrier] [origin] [dest] [signed]")
    print("  exit\n")

    while True:
        try:
            line = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not line or line.lower() in ("exit", "quit"):
            break

        parts = line.split(maxsplit=5)
        cmd = parts[0].lower()
        try:
            if cmd == "arrange":
                agent.arrange_shipment(parts[1], parts[2] if len(parts) > 2 else "DHL",
                                       parts[3] if len(parts) > 3 else "",
                                       parts[4] if len(parts) > 4 else "")
            elif cmd == "depart":
                agent.depart(parts[1], parts[2] if len(parts) > 2 else "",
                             parts[3] if len(parts) > 3 else "")
            elif cmd == "customs":
                agent.customs_start(parts[1], parts[2] if len(parts) > 2 else "",
                                    parts[3] if len(parts) > 3 else "")
            elif cmd == "hold":
                agent.customs_hold(parts[1], parts[2])
            elif cmd == "clear":
                agent.customs_clear(parts[1], parts[2] if len(parts) > 2 else "")
            elif cmd == "arrive":
                agent.arrive(parts[1], parts[2] if len(parts) > 2 else "")
            elif cmd == "partial":
                agent.partial_arrive(parts[1], int(parts[2]), int(parts[3]))
            elif cmd == "sign":
                agent.deliver_sign(parts[1], parts[2],
                                   parts[3] if len(parts) > 3 else "")
            elif cmd == "fail":
                agent.mark_failed(parts[1], parts[2],
                                  parts[3] if len(parts) > 3 else "")
            elif cmd == "reroute":
                agent.reroute(parts[1], parts[2] if len(parts) > 2 else "",
                              parts[3] if len(parts) > 3 else "")
            elif cmd == "track":
                agent.track_shipment_full(parts[1])
            elif cmd == "active":
                agent.list_active(parts[1] if len(parts) > 1 else "")
            elif cmd == "full":
                agent.process_full(
                    parts[1],
                    parts[2] if len(parts) > 2 else "DHL",
                    parts[3] if len(parts) > 3 else "",
                    parts[4] if len(parts) > 4 else "",
                    parts[5] if len(parts) > 5 else "",
                )
            else:
                print(f"❌ 未知指令：{cmd}")
        except Exception as e:
            print(f"❌ 錯誤：{e}")


def main():
    parser = argparse.ArgumentParser(description=f"{AGENT_NAME} v2.0 — OTD 物流專家")
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--erp-base", default=ERP_BASE)
    parser.add_argument("--interactive", "-i", action="store_true")
    args = parser.parse_args()

    agent = LogisticsAgent(erp_base=args.erp_base)
    if args.demo:
        demo(agent)
    elif args.interactive:
        interactive(agent)
    else:
        demo(agent)


if __name__ == "__main__":
    main()
