"""
Customer Service Agent — 客戶溝通樞紐

負責從詢單接收到出貨通知的全程客戶互動，包括詢單接收、進度追蹤、ASN 發出、
出貨通知、Invoice & Shipping 寄出、報關聯繫等。

執行：python3 agent.py --demo
"""

import argparse
import json
from datetime import datetime
from typing import Optional

import requests

ERP_BASE = "http://localhost:8001"
AGENT_NAME = "Customer Service Agent"


class CustomerServiceAgent:
    """客服流程 Agent"""

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

    def _patch(self, path, params=None):
        r = requests.patch(f"{self.erp_base}{path}", params=params or {})
        r.raise_for_status()
        return r.json()

    # ── 詢單處理 ──

    def process_inquiry(self, order_ref: str, items: list[dict],
                        request_date: str, customer: str = "",
                        channel: str = "email") -> dict:
        """
        處理客戶詢單：
        1. 驗證料號存在
        2. 執行 ATP 試算
        3. 生成回覆內容
        """
        print(f"\n{'='*60}")
        print(f"[{AGENT_NAME}] 處理詢單 {order_ref}")
        print(f"  客戶：{customer}  渠道：{channel}")
        print(f"{'='*60}")

        # Step 1: 驗證料號
        valid = []
        for item in items:
            try:
                info = self._get(f"/api/v1/items/{item['item_code']}")
                valid.append({**item, "description": info["description"]})
                print(f"  ✅ {item['item_code']} — {info['description']}")
            except requests.HTTPError:
                print(f"  ❌ {item['item_code']} — 料號不存在")

        if not valid:
            return {
                "event": "inquiry_reply",
                "order_ref": order_ref,
                "result": "rejected",
                "content": "抱歉，您的詢單中包含不存在的料號，請確認後重新查詢。",
                "agent": AGENT_NAME,
            }

        # Step 2: ATP 試算
        atp_results = []
        for item in valid:
            try:
                atp = self._post("/api/v1/atp/check", {
                    "item_code": item["item_code"],
                    "qty": item.get("qty", 0),
                    "request_date": request_date,
                })
                atp_results.append(atp)
                print(f"  🔵 ATP {item['item_code']}：{atp['result']} → {atp['remarks']}")
            except requests.HTTPError as e:
                print(f"  ❌ ATP 失敗 {item['item_code']}：{e}")

        # Step 3: 生成回覆
        reply = self._build_reply(order_ref, customer, channel, valid, atp_results)
        print(f"\n  📧 回覆已生成（channel={channel}）")

        return reply

    def check_so_status(self, so_id: str) -> dict:
        """查詢 SO 狀態"""
        so = self._get(f"/api/v1/so/{so_id}")
        so["lines"] = self._get(f"/api/v1/so/{so_id}/lines")
        return so

    def send_asn(self, so_id: str, shipping_id: str) -> dict:
        """發出 ASN 預出貨通知"""
        so = self.check_so_status(so_id)
        shipping = self._get(f"/api/v1/shipping/{shipping_id}")

        print(f"\n[{AGENT_NAME}] 發出 ASN")
        print(f"  SO：{so_id}  Shipping：{shipping_id}")
        print(f"  SO 狀態：{so['status']}  出貨狀態：{shipping['status']}")

        return {
            "event": "asn_issued",
            "so_id": so_id,
            "shipping_id": shipping_id,
            "customer_id": so.get("customer_id", ""),
            "status": shipping["status"],
            "agent": AGENT_NAME,
        }

    def send_shipping_notice(self, so_id: str, tracking_no: str) -> dict:
        """發出出貨通知"""
        return {
            "event": "shipping_notice_sent",
            "so_id": so_id,
            "tracking_no": tracking_no,
            "agent": AGENT_NAME,
        }

    def send_invoice(self, invoice_id: str) -> dict:
        """發出 Invoice"""
        inv = self._get(f"/api/v1/invoice/{invoice_id}")
        print(f"\n[{AGENT_NAME}] 發出發票通知")
        print(f"  發票：{inv['invoice_id']}  金額：{inv['amount']}")
        return {
            "event": "invoice_sent",
            "invoice_id": invoice_id,
            "so_id": inv.get("so_id", ""),
            "amount": inv["amount"],
            "agent": AGENT_NAME,
        }

    def handle_customer_voice(self, order_ref: str, feedback: str,
                              feedback_type: str = "general") -> dict:
        """處理客戶反饋/聲音"""
        print(f"\n[{AGENT_NAME}] 收到客戶反饋")
        print(f"  訂單：{order_ref}  類型：{feedback_type}")
        print(f"  內容：{feedback[:100]}...")

        return {
            "event": "customer_voice_received",
            "order_ref": order_ref,
            "feedback_type": feedback_type,
            "content": feedback,
            "handled_by": AGENT_NAME,
            "forwarded_to": "After Service Agent",
            "agent": AGENT_NAME,
        }

    # ── 輔助方法 ──

    @staticmethod
    def _build_reply(order_ref, customer, channel, items, atp_results):
        lines = []
        for item, atp in zip(items, atp_results):
            status_icon = {"on_time": "✅", "delayed": "⚠️", "insufficient": "❌"}.get(atp["result"], "❓")
            lines.append(
                f"  {status_icon} {item['description']} ({item['item_code']}) "
                f"x{item['qty']} → {atp['remarks']}"
            )

        result_map = {"on_time": "✅ 可承接", "delayed": "⚠️ 可承接（略延）", "insufficient": "❌ 無法承接"}
        overall = max((r["result"] for r in atp_results), key=lambda x: {"on_time": 2, "delayed": 1, "insufficient": 0}.get(x, 0))
        conclusion = result_map.get(overall, overall)

        content = "您好，感謝您的詢單。\n\n"
        for line in lines:
            content += line + "\n"
        content += f"\n{conclusion}"

        return {
            "event": "inquiry_replied",
            "order_ref": order_ref,
            "reply_to": customer,
            "channel": channel,
            "content": content.strip(),
            "items_count": len(items),
            "atp_summary": {r["item_code"]: r["result"] for r in atp_results},
            "agent": AGENT_NAME,
        }


# ── 命令列介面 ───────────────────────────────────────────────────────────────

def demo(agent):
    scenarios = [
        ("正常詢單", "INQ-DEMO-001", [{"item_code": "E2E-SKU-001", "qty": 100}], "2026-06-15", "ACME Corp"),
        ("混合詢單", "INQ-DEMO-002", [{"item_code": "E2E-SKU-001", "qty": 50}, {"item_code": "E2E-SKU-003", "qty": 30}], "2026-06-15", "Globex Inc"),
    ]

    for label, ref, items, date, cust in scenarios:
        print(f"\n▶ {label}")
        result = agent.process_inquiry(ref, items, date, cust)
        print(f"  Result: {result.get('event')} → {result.get('content', '')[:100]}")

    # ASN 示範
    print("\n▶ ASN 發出")
    result = agent.send_asn("E2E-SO-001", "E2E-SHP-001")
    print(f"  Result: {result}")

    # 客戶反饋
    print("\n▶ 客戶反饋")
    result = agent.handle_customer_voice("PO-2026-001", "請問出貨了嗎？", "progress_inquiry")
    print(f"  Result: {result}")


def interactive(agent):
    print(f"{AGENT_NAME} — 互動模式")
    print("format: <command> [args]")
    print("  inquiry <ref> <item_code> <qty> <date>   — 詢單")
    print("  so <so_id>                                — 查詢 SO")
    print("  asn <so_id> <shipping_id>                 — 發出 ASN")
    print("  voice <ref> <type> <message>              — 客戶反饋")
    print("  exit                                      — 離開\n")

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
            if cmd == "inquiry":
                ref, item, qty, date = parts[1:]
                result = agent.process_inquiry(ref, [{"item_code": item, "qty": int(qty)}], date)
                print(json.dumps(result, ensure_ascii=False, indent=2))
            elif cmd == "so":
                so = agent.check_so_status(parts[1])
                print(json.dumps(so, ensure_ascii=False, indent=2))
            elif cmd == "asn":
                result = agent.send_asn(parts[1], parts[2])
                print(json.dumps(result, ensure_ascii=False, indent=2))
            elif cmd == "voice":
                ref, ftype, msg = parts[1:]
                result = agent.handle_customer_voice(ref, msg, ftype)
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                print(f"❌ 未知指令：{cmd}")
        except Exception as e:
            print(f"❌ 錯誤：{e}")


def main():
    parser = argparse.ArgumentParser(description=f"{AGENT_NAME} — OTD 客服專家")
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--erp-base", default=ERP_BASE)
    parser.add_argument("--interactive", "-i", action="store_true")
    args = parser.parse_args()

    agent = CustomerServiceAgent(erp_base=args.erp_base)
    if args.demo:
        demo(agent)
    elif args.interactive:
        interactive(agent)
    else:
        demo(agent)


if __name__ == "__main__":
    main()
