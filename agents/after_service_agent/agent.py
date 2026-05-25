"""
After Service Agent — 售後服務專家

負責處理客戶聲音（Customer Voice）、案件追蹤、售後支援與客戶滿意度管理。

執行：python3 agent.py --demo
"""

import argparse
import json
from datetime import datetime, timezone
from typing import Optional

import requests

ERP_BASE = "http://localhost:8001"
AGENT_NAME = "After Service Agent"


class AfterServiceAgent:
    """售後服務 Agent"""

    def __init__(self, erp_base: str = ERP_BASE):
        self.erp_base = erp_base

    def _get(self, path):
        r = requests.get(f"{self.erp_base}{path}")
        r.raise_for_status()
        return r.json()

    # ── 案件處理 ──

    PRIORITY_MAP = {
        "emergency": "🔴 緊急",
        "high": "🟠 高",
        "medium": "🟡 中",
        "low": "🟢 低",
    }

    STATUS_MAP = {
        "received": "📥 已收到",
        "investigating": "🔍 調查中",
        "resolved": "✅ 已解決",
        "closed": "🔒 已結案",
        "escalated": "⬆️ 已升級",
    }

    def handle_feedback(self, ticket_id: str, order_ref: str, customer: str,
                        feedback_type: str, content: str,
                        channel: str = "email",
                        priority: str = "medium") -> dict:
        """
        處理客戶反饋：
        1. 分級（依反饋類型與內容）
        2. 若關聯訂單，查詢 ERP 狀態
        3. 生成回覆與處理計畫
        """
        print(f"\n{'='*60}")
        print(f"[{AGENT_NAME}] 客戶反饋處理")
        print(f"  案件：{ticket_id}  客戶：{customer}  優先級：{self.PRIORITY_MAP.get(priority, priority)}")
        print(f"  類型：{feedback_type}  渠道：{channel}")
        print(f"  內容：{content[:100]}...")
        print(f"{'='*60}")

        # 查詢關聯訂單
        order_info = None
        if order_ref:
            try:
                if order_ref.startswith("SO-"):
                    order_info = self._get(f"/api/v1/so/{order_ref}")
                elif order_ref.startswith("PO-"):
                    order_info = self._get(f"/api/v1/po/{order_ref}")
                print(f"  📋 訂單 {order_ref} 狀態：{order_info.get('status', 'N/A')}")
            except requests.HTTPError:
                print(f"  ⚠️ 訂單 {order_ref} 查詢不到")

        # 自動調整優先級
        adjusted = self._adjust_priority(feedback_type, content, priority)
        if adjusted != priority:
            print(f"  ⬆️ 優先級調整：{self.PRIORITY_MAP.get(priority)} → {self.PRIORITY_MAP.get(adjusted)}")
            priority = adjusted

        # 生成回覆
        reply = self._build_reply(ticket_id, order_ref, customer, feedback_type,
                                  content, priority, order_info)
        print("\n  📧 回覆已生成")

        return reply

    def update_ticket(self, ticket_id: str, status: str,
                      action: str = "", next_step: str = "") -> dict:
        """更新案件狀態"""
        print(f"\n[{AGENT_NAME}] 案件更新 {ticket_id}")
        print(f"  狀態：{self.STATUS_MAP.get(status, status)}")
        if action:
            print(f"  處理：{action}")
        if next_step:
            print(f"  下一步：{next_step}")

        return {
            "event": "ticket_updated",
            "ticket_id": ticket_id,
            "status": status,
            "action_taken": action,
            "next_step": next_step,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "agent": AGENT_NAME,
        }

    def resolve_ticket(self, ticket_id: str, resolution: str,
                       order_ref: str = "") -> dict:
        """結案"""
        print(f"\n[{AGENT_NAME}] 案件結案 {ticket_id}")
        print(f"  解決方案：{resolution}")

        return {
            "event": "ticket_resolved",
            "ticket_id": ticket_id,
            "order_ref": order_ref,
            "resolution": resolution,
            "status": "resolved",
            "resolved_at": datetime.now(timezone.utc).isoformat(),
            "agent": AGENT_NAME,
        }

    # ── 輔助方法 ──

    @staticmethod
    def _adjust_priority(feedback_type: str, content: str, current: str) -> str:
        """根據反饋類型與內容自動調整優先級"""
        urgency_keywords = ["緊急", "急", "延遲", "破損", "損壞", "投訴", "律師", "解約", "停止合作"]
        type_boost = {
            "quality_issue": 1,       # 品質問題升一級
            "shipping_delay": 1,       # 出貨延遲升一級
            "wrong_shipment": 1,       # 錯發升一級
            "general_inquiry": 0,      # 一般詢問不變
            "suggestion": -1,          # 建議降一級
        }

        boost = type_boost.get(feedback_type, 0)
        if any(kw in content for kw in urgency_keywords):
            boost += 1

        levels = ["low", "medium", "high", "emergency"]
        idx = levels.index(current) + boost
        return levels[max(0, min(idx, len(levels) - 1))]

    @staticmethod
    def _build_reply(ticket_id, order_ref, customer, feedback_type,
                     content, priority, order_info):
        priority_icon = {"emergency": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(priority, "🟡")
        type_label = {
            "quality_issue": "品質異常",
            "shipping_delay": "出貨延遲",
            "wrong_shipment": "錯發貨品",
            "general_inquiry": "一般查詢",
            "suggestion": "改善建議",
            "return_request": "退換貨",
            "warranty": "保固查詢",
        }.get(feedback_type, feedback_type)

        reply = f"您好，{customer}，\n\n"
        reply += f"感謝您的來信（案件編號：{ticket_id}）。\n\n"
        reply += f"我們已收到您關於「{type_label}」的回饋，{priority_icon}優先級：{priority}。\n"

        if order_info:
            reply += f"\n查詢到您的訂單 {order_ref}，目前狀態：{order_info.get('status', 'N/A')}。\n"

        reply += "\n我們正在積極處理中，稍後會有專人與您聯繫回覆。\n"
        reply += "如有緊急事項，請直接與我們聯繫。\n\n謝謝您的耐心等候。"

        action_map = {
            "quality_issue": "聯繫品質部門確認異常原因",
            "shipping_delay": "追蹤出貨單狀態並回覆新交期",
            "wrong_shipment": "安排退換貨流程",
            "general_inquiry": "查詢訂單狀態並回覆",
            "suggestion": "彙整至知識庫並評估可行性",
            "return_request": "啟動退換貨流程",
            "warranty": "查詢保固紀錄並回覆",
        }
        next_step = action_map.get(feedback_type, "調查案件內容並回覆")

        return {
            "event": "ticket_acknowledged",
            "ticket_id": ticket_id,
            "order_ref": order_ref or "",
            "customer": customer,
            "feedback_type": feedback_type,
            "priority": priority,
            "status": "received",
            "reply_content": reply,
            "next_step": next_step,
            "agent": AGENT_NAME,
        }


# ── 命令列介面 ───────────────────────────────────────────────────────────────

def demo(agent):
    scenarios = [
        ("CV-DEMO-001", "SO-2026-005", "ACME Corp", "quality_issue",
         "出貨的 SKU-001 有品質異常，外殼有刮傷，請協助處理。", "email", "high"),
        ("CV-DEMO-002", "SO-2026-006", "Globex Inc", "shipping_delay",
         "原本預計今天出貨，請問有延遲嗎？", "email", "medium"),
        ("CV-DEMO-003", "", "Initech", "suggestion",
         "建議可以提前一天發送出貨通知，方便我們安排收貨。", "email", "low"),
    ]

    for args in scenarios:
        ticket_id, order_ref, customer, ftype, content, channel, priority = args
        print(f"\n▶ 案件 {ticket_id}")
        result = agent.handle_feedback(ticket_id, order_ref, customer, ftype, content, channel, priority)
        print(f"  Priority: {result['priority']}")
        print(f"  Next: {result['next_step']}")

        # 更新狀態
        agent.update_ticket(ticket_id, "investigating",
                            action="已確認訂單狀態，正在調查中",
                            next_step="預計 2 小時內回覆")

    # 結案
    print("\n▶ 結案 CV-DEMO-001")
    agent.resolve_ticket("CV-DEMO-001",
                         "已確認品質異常原因，安排更換新品，預計 3 個工作天內出貨",
                         order_ref="SO-2026-005")


def interactive(agent):
    print(f"{AGENT_NAME} — 互動模式")
    print("format: <command> [args]")
    print("  feedback <ticket> <order> <customer> <type> <priority> <message>")
    print("  update <ticket> <status> [action]")
    print("  resolve <ticket> <resolution> [order]")
    print("  exit")
    while True:
        try:
            line = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not line or line.lower() in ("exit", "quit"):
            break
        parts = line.split(maxsplit=4)
        cmd = parts[0].lower()
        try:
            if cmd == "feedback":
                ticket, order, cust, ftype = parts[1:5]
                priority = parts[5] if len(parts) > 5 else "medium"
                msg = parts[6] if len(parts) > 6 else "客戶反饋"
                r = agent.handle_feedback(ticket, order, cust, ftype, msg, "email", priority)
                print(json.dumps(r, ensure_ascii=False, indent=2))
            elif cmd == "update":
                ticket, status = parts[1:3]
                action = parts[3] if len(parts) > 3 else ""
                r = agent.update_ticket(ticket, status, action)
                print(json.dumps(r, ensure_ascii=False, indent=2))
            elif cmd == "resolve":
                ticket = parts[1]
                resolution = parts[2]
                order = parts[3] if len(parts) > 3 else ""
                r = agent.resolve_ticket(ticket, resolution, order)
                print(json.dumps(r, ensure_ascii=False, indent=2))
            else:
                print(f"❌ 未知指令：{cmd}")
        except Exception as e:
            print(f"❌ 錯誤：{e}")


def main():
    parser = argparse.ArgumentParser(description=f"{AGENT_NAME} — OTD 售後服務專家")
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--erp-base", default=ERP_BASE)
    parser.add_argument("--interactive", "-i", action="store_true")
    args = parser.parse_args()
    agent = AfterServiceAgent(erp_base=args.erp_base)
    if args.demo:
        demo(agent)
    elif args.interactive:
        interactive(agent)
    else:
        demo(agent)


if __name__ == "__main__":
    main()
