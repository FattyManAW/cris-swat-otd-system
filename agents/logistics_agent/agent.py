"""
Logistics Agent — 物流處理專家

負責從出貨排程確認到到貨確認的全程物流流程，包含：
報關文件生成、出貨安排、在途追蹤與到貨確認。

執行：python3 agent.py --demo
"""

import json
import argparse
import requests
import uuid
from datetime import datetime
from typing import Optional

ERP_BASE = "http://localhost:8001"
AGENT_NAME = "Logistics Agent"


class LogisticsAgent:
    """物流處理 Agent"""

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

    # ── Step 1：安排出貨物流 ──

    def arrange_shipment(self, schedule_id: str, carrier: str = "auto") -> dict:
        """
        安排出貨物流：
        1. 查詢出貨單
        2. 若已有追蹤號，直接回傳（不重複安排）
        3. 生成追蹤號，調用 arrange
        4. 回傳追蹤號與預計到貨日
        """
        print(f"\n{'='*60}")
        print(f"[{AGENT_NAME}] 安排出貨物流")
        print(f"  排程：{schedule_id}  物流商：{carrier}")
        print(f"{'='*60}")

        # 查詢出貨單
        shipping = self._get(f"/api/v1/shipping/{schedule_id}")
        print(f"  📦 出貨單：{shipping['shipping_id']}")
        print(f"     狀態：{shipping['status']}")
        print(f"     棧板數：{shipping.get('pallet_count', 'N/A')}")
        print(f"     貨櫃規格：{shipping.get('container_type', 'N/A')}")
        print(f"     結關日：{shipping.get('customs_date', 'N/A')}")

        # 若已有追蹤號，跳過
        if shipping.get("tracking_no"):
            print(f"  ℹ️ 已有追蹤號：{shipping['tracking_no']}，跳過安排")
            return {
                "event": "shipment_already_arranged",
                "schedule_id": schedule_id,
                "tracking_no": shipping["tracking_no"],
                "carrier": carrier,
                "estimated_arrival": None,
                "agent": AGENT_NAME,
            }

        # 生成追蹤號
        tracking_no = self._gen_tracking(schedule_id)
        print(f"  追蹤號：{tracking_no}")

        # 安排物流
        result = self._post("/api/v1/logistics/arrange", {
            "tracking_no": tracking_no,
            "shipping_id": shipping.get("shipping_id", ""),
            "carrier": carrier,
            "eta": shipping.get("customs_date"),
        })

        print(f"\n  ✅ 物流已安排")
        print(f"     追蹤號：{result.get('tracking_no', 'N/A')}")
        print(f"     物流商：{result.get('carrier', 'N/A')}")
        print(f"     預計到貨：{result.get('eta', 'N/A')}")

        return {
            "event": "shipment_arranged",
            "schedule_id": schedule_id,
            "tracking_no": result.get("tracking_no"),
            "carrier": result.get("carrier"),
            "estimated_arrival": result.get("eta"),
            "agent": AGENT_NAME,
        }

    # ── Step 2：物流追蹤 ──

    def track_shipment(self, tracking_no: str) -> dict:
        """
        查詢物流狀態
        """
        print(f"\n[{AGENT_NAME}] 追蹤物流 {tracking_no}")

        status = self._get(f"/api/v1/logistics/{tracking_no}")

        status_icon = {
            "booked": "📋",
            "in_transit": "🚚",
            "customs": "🛃",
            "delivered": "✅",
            "exception": "⚠️",
        }.get(status.get("status"), "❓")

        print(f"  {status_icon} 狀態：{status.get('status')}")
        print(f"     物流商：{status.get('carrier', 'N/A')}")
        print(f"     ETA：{status.get('eta', 'N/A')}")
        print(f"     實際到貨：{status.get('actual_arrival', 'N/A')}")

        return {
            "event": "tracking_queried",
            "tracking_no": tracking_no,
            "status": status.get("status"),
            "carrier": status.get("carrier"),
            "eta": status.get("eta"),
            "actual_arrival": status.get("actual_arrival"),
            "agent": AGENT_NAME,
        }

    # ── Step 3：確認到貨 ──

    def confirm_arrival(self, tracking_no: str) -> dict:
        """
        確認到貨（arrive endpoint 不需 body）
        """
        print(f"\n[{AGENT_NAME}] 確認到貨 {tracking_no}")

        # 先查詢當前狀態
        before = self._get(f"/api/v1/logistics/{tracking_no}")
        print(f"  到貨前狀態：{before.get('status')}")

        # 標記到貨（不需 body）
        result = self._post(f"/api/v1/logistics/{tracking_no}/arrive")

        print(f"  ✅ 到貨已確認")
        print(f"     新狀態：{result.get('status')}")
        print(f"     實際到貨：{result.get('actual_arrival', 'N/A')}")

        return {
            "event": "arrival_confirmed",
            "tracking_no": tracking_no,
            "status": result.get("status"),
            "actual_arrival": result.get("actual_arrival"),
            "agent": AGENT_NAME,
        }

    # ── Step 4：出貨單查詢 ──

    def get_shipping_detail(self, shipping_id: str) -> dict:
        """查詢出貨單詳細資料"""
        shipping = self._get(f"/api/v1/shipping/{shipping_id}")
        print(f"\n[{AGENT_NAME}] 出貨單明細 {shipping_id}")
        print(f"  狀態：{shipping.get('status')}")
        print(f"  SO：{shipping.get('so_id')}")
        print(f"  棧板數：{shipping.get('pallet_count', 'N/A')}")
        print(f"  貨櫃規格：{shipping.get('container_type', 'N/A')}")
        print(f"  結關日：{shipping.get('customs_date', 'N/A')}")
        print(f"  追蹤號：{shipping.get('tracking_no', 'N/A')}")
        return shipping

    # ── Step 5：完整物流流程 ──

    def process_shipment(self, schedule_id: str, carrier: str = "auto",
                         confirm_arrival: bool = False) -> dict:
        """
        完整物流流程：
        查詢出貨單 → 安排物流 → 追蹤狀態 → （可選）確認到貨
        """
        print(f"\n{'='*60}")
        print(f"[{AGENT_NAME}] 完整物流流程")
        print(f"  排程：{schedule_id}")
        print(f"{'='*60}")

        # Step 1：查詢出貨單
        shipping = self.get_shipping_detail(schedule_id)

        # Step 2：安排物流
        arrange_result = self.arrange_shipment(schedule_id, carrier)

        # Step 3：追蹤
        tracking_no = arrange_result.get("tracking_no")
        if tracking_no:
            track_result = self.track_shipment(tracking_no)

            # Step 4：確認到貨（可選）
            if confirm_arrival:
                arrival_result = self.confirm_arrival(tracking_no)
            else:
                arrival_result = None
        else:
            track_result = None
            arrival_result = None

        return {
            "event": "shipment_processed",
            "schedule_id": schedule_id,
            "shipping": shipping,
            "arrange": arrange_result,
            "tracking": track_result,
            "arrival": arrival_result,
            "agent": AGENT_NAME,
        }


# ── 命令列介面 ───────────────────────────────────────────────────────────────

def demo(agent):
    # 場景 1：查看出貨單
    result = agent.get_shipping_detail("E2E-SHP-001")
    print(f"\n  結果：{json.dumps(result, ensure_ascii=False, indent=2)[:300]}...")

    # 場景 2：安排出貨物流
    result = agent.arrange_shipment("E2E-SHP-001", carrier="DHL")
    print(f"\n  結果：{json.dumps(result, ensure_ascii=False, indent=2)[:300]}...")

    # 場景 3：追蹤物流
    tracking_no = result.get("tracking_no", "TRK-E2E-001")
    result = agent.track_shipment(tracking_no)
    print(f"\n  結果：{json.dumps(result, ensure_ascii=False, indent=2)[:300]}...")

    # 場景 4：出貨單查詢
    result = agent.get_shipping_detail("E2E-SHP-001")
    print(f"\n  結果：{json.dumps(result, ensure_ascii=False, indent=2)[:300]}...")


def interactive(agent):
    print(f"{AGENT_NAME} — 互動模式")
    print("format: <command> [args]")
    print("  shipping <shipping_id>                  — 查看出貨單")
    print("  arrange <schedule_id> [carrier]          — 安排出貨物流")
    print("  track <tracking_no>                      — 追蹤物流")
    print("  arrive <tracking_no>                     — 確認到貨")
    print("  full <schedule_id> [carrier]             — 完整物流流程")
    print("  exit                                     — 離開\n")

    while True:
        try:
            line = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not line or line.lower() in ("exit", "quit"):
            break

        parts = line.split(maxsplit=3)
        cmd = parts[0].lower()
        try:
            if cmd == "shipping":
                result = agent.get_shipping_detail(parts[1])
                print(json.dumps(result, ensure_ascii=False, indent=2))
            elif cmd == "arrange":
                carrier = parts[2] if len(parts) > 2 else "auto"
                result = agent.arrange_shipment(parts[1], carrier)
                print(json.dumps(result, ensure_ascii=False, indent=2))
            elif cmd == "track":
                result = agent.track_shipment(parts[1])
                print(json.dumps(result, ensure_ascii=False, indent=2))
            elif cmd == "arrive":
                result = agent.confirm_arrival(parts[1])
                print(json.dumps(result, ensure_ascii=False, indent=2))
            elif cmd == "full":
                carrier = parts[2] if len(parts) > 2 else "auto"
                result = agent.process_shipment(parts[1], carrier)
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                print(f"❌ 未知指令：{cmd}")
        except Exception as e:
            print(f"❌ 錯誤：{e}")


def main():
    parser = argparse.ArgumentParser(description=f"{AGENT_NAME} — OTD 物流專家")
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
