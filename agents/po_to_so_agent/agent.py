"""
PO-to-SO Agent — 訂單轉換專家

負責接收客戶 PO，進行料號對照，在 ERP 模擬層建立 SO 單頭與單身，
回傳轉換結果或列出問題料號等待人工確認。

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
AGENT_NAME = "PO-to-SO Agent"


# ── 核心邏輯 ────────────────────────────────────────────────────────────────

class POtoSOAgent:
    """PO 轉 SO Agent"""

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

    def _patch(self, path: str, params: Optional[dict] = None) -> dict:
        r = requests.patch(f"{self.erp_base}{path}", params=params or {})
        r.raise_for_status()
        return r.json()

    # ── 公開 API ──

    def get_items(self) -> list[dict]:
        """取得所有可用料號"""
        return self._get("/api/v1/items")

    def get_po(self, po_id: str) -> dict:
        """查詢 PO 明細"""
        po = self._get(f"/api/v1/po/{po_id}")
        po["lines"] = self._get(f"/api/v1/po/{po_id}/lines")
        return po

    def validate_items(self, item_codes: list[str]) -> tuple[list[str], list[str]]:
        """
        驗證料號是否存在於 ERP。

        Returns: (valid_codes, invalid_codes)
        """
        try:
            all_items = self.get_items()
            valid_set = {i["item_code"] for i in all_items}
        except requests.HTTPError:
            valid_set = set()

        valid = [c for c in item_codes if c in valid_set]
        invalid = [c for c in item_codes if c not in valid_set]
        return valid, invalid

    def convert_po_to_so(self, po_id: str, so_id: Optional[str] = None,
                         contract_prices: Optional[dict] = None) -> dict:
        """
        將 PO 轉換為 SO。

        流程：
        1. 查詢 PO 及其單身
        2. 驗證所有料號存在
        3. 若有無效料號，返回問題清單
        4. 調用 ERP 模擬層建立 SO
        5. 回傳結果

        Args:
            po_id: PO 單號
            so_id: 指定 SO 單號（可選，自動生成）
            contract_prices: 合約單價 {item_code: price}
        """
        contract_prices = contract_prices or {}
        print(f"\n{'='*60}")
        print(f"[{AGENT_NAME}] PO → SO 轉換")
        print(f"  PO：{po_id}")
        print(f"{'='*60}")

        # Step 1: 查詢 PO
        try:
            po = self.get_po(po_id)
        except requests.HTTPError as e:
            return self._error_result(po_id, f"PO 查詢失敗：{e}")

        print(f"  📋 PO 狀態：{po['status']}")
        print(f"  👤 客戶：{po['customer_id']}")

        if po["status"] == "converted":
            return self._error_result(po_id, f"PO {po_id} 已轉換為 SO")

        # Step 2: 驗證料號
        item_codes = [line["item_code"] for line in po["lines"]]
        valid_items, invalid_items = self.validate_items(item_codes)

        if invalid_items:
            msg = f"以下料號不存在於 ERP：{', '.join(invalid_items)}，請人工確認"
            print(f"  ⚠️ {msg}")
            return {
                "event": "so_creation_blocked",
                "po_id": po_id,
                "invalid_items": invalid_items,
                "remarks": msg,
                "agent": AGENT_NAME,
            }

        print(f"  ✅ 料號驗證通過：{len(valid_items)} 筆")

        # Step 3: 建立 SO
        so_id = so_id or f"SO-{datetime.now().strftime('%Y%m%d')}-{requests.utils.requote_uri(po_id[-6:])}"

        try:
            so = self._post(f"/api/v1/po/{po_id}/convert", {}, params={"so_id": so_id})
        except requests.HTTPError as e:
            return self._error_result(po_id, f"SO 建立失敗：{e}")

        # Step 4: 計算總金額
        total = sum(
            line.get("qty", 0) * (contract_prices.get(line["item_code"], line.get("unit_price", 0))
            if contract_prices.get(line["item_code"]) else line.get("unit_price", 0))
            for line in po["lines"]
        )

        print(f"  📄 SO 建立完成：{so['so_id']}")
        print(f"  📊 單頭單身：{len(so.get('lines', po['lines']))} 筆")
        print(f"  💰 總金額：{total:,.1f}")

        return {
            "event": "so_created",
            "po_id": po_id,
            "so_id": so.get("so_id", so_id),
            "customer_id": po["customer_id"],
            "line_count": len(po["lines"]),
            "total_amount": total,
            "status": so.get("status", "draft"),
            "unmapped_items": [],
            "agent": AGENT_NAME,
        }

    def get_so(self, so_id: str) -> dict:
        """查詢 SO 明細（含單身）"""
        so = self._get(f"/api/v1/so/{so_id}")
        so["lines"] = self._get(f"/api/v1/so/{so_id}/lines")
        return so

    def update_so_status(self, so_id: str, status: str,
                         remarks: Optional[str] = None) -> dict:
        """更新 SO 狀態"""
        return self._patch(f"/api/v1/so/{so_id}", params={"status": status, "remarks": remarks or ""})

    # ── 輔助方法 ──

    @staticmethod
    def _error_result(po_id: str, msg: str) -> dict:
        return {
            "event": "po_to_so_error",
            "po_id": po_id,
            "result": "error",
            "remarks": msg,
            "agent": AGENT_NAME,
        }


# ── 命令列介面 ───────────────────────────────────────────────────────────────

def demo(agent: POtoSOAgent):
    """執行示範流程"""
    scenarios = [
        # (label, po_id, so_id, contract_prices)
        ("正常轉換", "E2E-PO-001", "E2E-SO-001", {}),
    ]

    results = []
    for label, po_id, so_id, prices in scenarios:
        print(f"\n▶ {label}")
        result = agent.convert_po_to_so(po_id, so_id, prices)
        results.append(result)
        print(f"  Result: {result.get('event')}")

    return results


def interactive(agent: POtoSOAgent):
    """互動模式"""
    print(f"{AGENT_NAME} — 互動模式")
    print("指令：")
    print("  convert <po_id> [so_id]  — 執行 PO→SO 轉換")
    print("  query <so_id>            — 查詢 SO")
    print("  status <so_id> <status>   — 更新 SO 狀態")
    print("  exit                     — 離開\n")

    while True:
        try:
            line = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not line or line.lower() in ("exit", "quit"):
            break

        parts = line.split(maxsplit=2)
        cmd = parts[0].lower()

        try:
            if cmd == "convert":
                po_id = parts[1]
                so_id = parts[2] if len(parts) > 2 else None
                result = agent.convert_po_to_so(po_id, so_id)
                print(json.dumps(result, ensure_ascii=False, indent=2))

            elif cmd == "query":
                so_id = parts[1]
                so = agent.get_so(so_id)
                print(json.dumps(so, ensure_ascii=False, indent=2))

            elif cmd == "status":
                so_id, status = parts[1], parts[2]
                result = agent.update_so_status(so_id, status)
                print(json.dumps(result, ensure_ascii=False, indent=2))

            else:
                print(f"❌ 未知指令：{cmd}")

        except Exception as e:
            print(f"❌ 錯誤：{e}")


def main():
    parser = argparse.ArgumentParser(description=f"{AGENT_NAME} — OTD 訂單轉換專家")
    parser.add_argument("--demo", action="store_true", help="執行示範流程")
    parser.add_argument("--erp-base", default=ERP_BASE, help="ERP 模擬層位址")
    parser.add_argument("--interactive", "-i", action="store_true", help="互動模式")
    args = parser.parse_args()

    agent = POtoSOAgent(erp_base=args.erp_base)

    if args.demo:
        demo(agent)
    elif args.interactive:
        interactive(agent)
    else:
        demo(agent)


if __name__ == "__main__":
    main()
