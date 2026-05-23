"""
ATP/CTP Agent — 交期試算專家

負責接收詢單需求，調用 ERP 模擬層進行 ATP（可承諾量）/ CTP（可交付能力）試算，
回覆精確的交期與可承諾數量。

執行：python3 agent.py
或：python3 agent.py --demo    # 執行示範流程
"""

import argparse
import json
import sys
from datetime import datetime
from typing import Optional

import requests

# ── 配置 ────────────────────────────────────────────────────────────────────

ERP_BASE = "http://localhost:8001"
AGENT_NAME = "ATP/CTP Agent"


# ── 核心邏輯 ────────────────────────────────────────────────────────────────

class ATPCTPAgent:
    """ATP/CTP 交期試算 Agent"""

    def __init__(self, erp_base: str = ERP_BASE):
        self.erp_base = erp_base

    # ── 內部方法 ──

    def _post(self, path: str, payload: dict, params: Optional[dict] = None) -> dict:
        r = requests.post(f"{self.erp_base}{path}", json=payload, params=params or {})
        r.raise_for_status()
        return r.json()

    def _get(self, path: str) -> dict:
        r = requests.get(f"{self.erp_base}{path}")
        r.raise_for_status()
        return r.json()

    # ── 公開 API ──

    def check_item(self, item_code: str) -> dict:
        """查詢料號基本資料"""
        return self._get(f"/api/v1/items/{item_code}")

    def atp_check(self, item_code: str, qty: int, request_date: str,
                  force_insufficient: bool = False, force_delay: bool = False) -> dict:
        """ATP 可承諾量試算"""
        return self._post(
            "/api/v1/atp/check",
            {"item_code": item_code, "qty": qty, "request_date": request_date},
            params={
                "force_insufficient": str(force_insufficient).lower(),
                "force_delay": str(force_delay).lower(),
            },
        )

    def ctp_check(self, item_code: str, qty: int, request_date: str,
                  force_insufficient: bool = False, force_delay: bool = False) -> dict:
        """CTP 可交付能力試算"""
        return self._post(
            "/api/v1/ctp/check",
            {"item_code": item_code, "qty": qty, "request_date": request_date},
            params={
                "force_insufficient": str(force_insufficient).lower(),
                "force_delay": str(force_delay).lower(),
            },
        )

    def process_inquiry(self, order_ref: str, item_code: str, qty: int,
                        request_date: str, customer: str = "") -> dict:
        """
        處理詢單：依次執行 ATP + CTP 試算，回傳綜合結果。

        CTP 為最終依據（包含產能限制）。
        """
        print(f"\n{'='*60}")
        print(f"[{AGENT_NAME}] 處理詢單 {order_ref}")
        print(f"  客戶：{customer}")
        print(f"  料號：{item_code}  數量：{qty}  需求日期：{request_date}")
        print(f"{'='*60}")

        # Step 1: 查詢料號
        try:
            item = self.check_item(item_code)
            print(f"  📦 料號：{item['item_code']} — {item['description']}")
            print(f"     交期前置：{item['lead_time_days']} 天  安全庫存：{item['safety_stock']}  日產能：{item['daily_capacity']}")
        except requests.HTTPError as e:
            return self._error_result(order_ref, item_code, f"料號查詢失敗：{e}")

        # Step 2: ATP 試算
        try:
            atp = self.atp_check(item_code, qty, request_date)
            print(f"  🔵 ATP：{atp['result']} → {atp['remarks']}")
        except requests.HTTPError as e:
            return self._error_result(order_ref, item_code, f"ATP 試算失敗：{e}")

        # Step 3: CTP 試算
        try:
            ctp = self.ctp_check(item_code, qty, request_date)
            print(f"  🟢 CTP：{ctp['result']} → {ctp['remarks']}")
        except requests.HTTPError as e:
            return self._error_result(order_ref, item_code, f"CTP 試算失敗：{e}")

        # Step 4: 綜合結論
        final = ctp  # CTP 為最終依據
        summary = self._build_summary(order_ref, item, atp, ctp, final)
        print(f"\n  ✅ 結論：{summary['conclusion']}")
        print(f"  📅 建議交期：{summary['suggested_date']}")
        print(f"  📦 可承諾量：{summary['available_qty']}")

        return summary

    # ── 輔助方法 ──

    @staticmethod
    def _error_result(order_ref: str, item_code: str, msg: str) -> dict:
        return {
            "event": "atp_ctp_error",
            "order_ref": order_ref,
            "item_code": item_code,
            "result": "error",
            "remarks": msg,
            "agent": AGENT_NAME,
        }

    @staticmethod
    def _build_summary(order_ref: str, item: dict, atp: dict, ctp: dict, final: dict) -> dict:
        result_map = {"on_time": "✅ 準時", "delayed": "⚠️ 延遲", "insufficient": "❌ 不足"}
        return {
            "event": "atp_ctp_result",
            "order_ref": order_ref,
            "item_code": item["item_code"],
            "item_desc": item["description"],
            "atp_result": atp["result"],
            "ctp_result": ctp["result"],
            "final_result": final["result"],
            "available_qty": final.get("available_qty", 0),
            "suggested_date": final.get("available_date", ""),
            "lead_time_days": item["lead_time_days"],
            "batch_recommended": final.get("batch_recommended", 1),
            "conclusion": result_map.get(final["result"], final["result"]),
            "remarks": final.get("remarks", ""),
            "agent": AGENT_NAME,
        }


# ── 命令列介面 ───────────────────────────────────────────────────────────────

def demo(agent: ATPCTPAgent):
    """執行示範流程"""
    scenarios = [
        # (order_ref, item_code, qty, request_date, customer, label)
        ("INQ-DEMO-001", "E2E-SKU-001", 100,  "2026-06-15", "ACME Corp",       "正常詢單"),
        ("INQ-DEMO-002", "E2E-SKU-001", 9999, "2026-06-15", "Globex Inc",       "大單（庫存不足）"),
        ("INQ-DEMO-003", "E2E-SKU-002", 200,  "2026-06-15", "Initech",          "正常詢單 B"),
    ]

    results = []
    for order_ref, item_code, qty, req_date, customer, label in scenarios:
        print(f"\n▶ {label}")
        result = agent.process_inquiry(order_ref, item_code, qty, req_date, customer)
        results.append(result)

    # 總結
    print(f"\n{'='*60}")
    print("總結報告")
    print(f"{'='*60}")
    for r in results:
        print(f"  {r['order_ref']} | {r['item_code']} x{r.get('available_qty','?')} | {r['final_result']} → {r.get('suggested_date','')}")

    return results


def interactive(agent: ATPCTPAgent):
    """互動模式"""
    print(f"{AGENT_NAME} — 互動模式")
    print("格式：料號 數量 需求日期 (YYYY-MM-DD)")
    print("例如：SKU-001 100 2026-06-15")
    print("輸入 exit 離開\n")

    while True:
        try:
            line = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not line or line.lower() in ("exit", "quit"):
            break
        parts = line.split()
        if len(parts) < 3:
            print("❌ 請輸入：料號 數量 需求日期")
            continue
        item_code, qty_str, req_date = parts[0], parts[1], parts[2]
        try:
            qty = int(qty_str)
        except ValueError:
            print(f"❌ 數量必須為數字：{qty_str}")
            continue
        try:
            result = agent.process_inquiry("INQ-INTERACTIVE", item_code, qty, req_date)
            print(json.dumps(result, ensure_ascii=False, indent=2))
        except Exception as e:
            print(f"❌ 錯誤：{e}")


def main():
    parser = argparse.ArgumentParser(description=f"{AGENT_NAME} — OTD 交期試算專家")
    parser.add_argument("--demo", action="store_true", help="執行示範流程")
    parser.add_argument("--erp-base", default=ERP_BASE, help="ERP 模擬層位址")
    parser.add_argument("--interactive", "-i", action="store_true", help="互動模式")
    args = parser.parse_args()

    agent = ATPCTPAgent(erp_base=args.erp_base)

    if args.demo:
        demo(agent)
    elif args.interactive:
        interactive(agent)
    else:
        # 預設執行 demo
        demo(agent)


if __name__ == "__main__":
    main()
