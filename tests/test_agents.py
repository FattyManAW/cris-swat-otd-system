"""Agent unit tests — mock requests layer, test agent logic for all 5 agents.

AfterServiceAgent, ATPCTPAgent, CustomerServiceAgent, LogisticsAgent, POtoSOAgent
"""

import json
from datetime import datetime
from unittest.mock import Mock, PropertyMock, patch

import pytest

# ════════════════════════════════════════════════════════════════════════════
# Shared mock utilities
# ════════════════════════════════════════════════════════════════════════════

def mock_response(status_code=200, json_data=None):
    r = Mock()
    r.status_code = status_code
    r.json.return_value = json_data or {}
    r.raise_for_status = Mock()
    return r


def mock_http_error(status_code=404, detail="Not Found"):
    import requests
    r = Mock(spec=requests.Response)
    r.status_code = status_code
    r.json.return_value = {"detail": detail}
    r.raise_for_status.side_effect = requests.HTTPError(f"{status_code}: {detail}")
    return r


# ════════════════════════════════════════════════════════════════════════════
# After Service Agent
# ════════════════════════════════════════════════════════════════════════════

class TestAfterServiceAgent:
    def _make_agent(self):
        from agents.after_service_agent.agent import AfterServiceAgent
        return AfterServiceAgent(erp_base="http://mock:8001")

    def test_handle_feedback_normal(self):
        agent = self._make_agent()
        with patch('requests.get') as mock_get:
            mock_get.return_value = mock_response(200, {
                "so_id": "SO-001", "status": "confirmed",
                "customer_id": "CUST-001",
            })
            result = agent.handle_feedback(
                "TKT-001", "SO-001", "ACME Corp",
                "general_inquiry", "出貨進度查詢", "email", "medium",
            )
        assert result["event"] == "ticket_acknowledged"
        assert result["ticket_id"] == "TKT-001"
        assert result["priority"] == "medium"
        assert "ACME Corp" in result["reply_content"]

    def test_handle_feedback_urgent_boost(self):
        agent = self._make_agent()
        with patch('requests.get') as mock_get:
            mock_get.return_value = mock_response(200, {
                "so_id": "SO-002", "status": "draft",
            })
            # "破損" in content should boost priority
            result = agent.handle_feedback(
                "TKT-002", "SO-002", "Globex",
                "quality_issue", "貨物破損嚴重，請緊急處理", "email", "medium",
            )
        # quality_issue(+1) + urgency keyword(+1) → medium → high → emergency
        assert result["priority"] == "emergency"

    def test_handle_feedback_order_not_found(self):
        agent = self._make_agent()
        with patch('requests.get') as mock_get:
            mock_get.return_value = mock_http_error(404, "不存在")
            result = agent.handle_feedback(
                "TKT-003", "SO-NOPE", "Initech",
                "shipping_delay", "等了很久", "email", "low",
            )
        # Should still succeed with empty order_info
        assert result["event"] == "ticket_acknowledged"
        # shipping_delay boost=1, "等了很久" no urgency keyword
        # low(0) + 1 = 1 → medium
        assert result["priority"] == "medium"

    def test_update_ticket(self):
        agent = self._make_agent()
        result = agent.update_ticket("TKT-001", "investigating",
                                     action="查詢中", next_step="2h 回覆")
        assert result["event"] == "ticket_updated"
        assert result["status"] == "investigating"
        assert "updated_at" in result

    def test_resolve_ticket(self):
        agent = self._make_agent()
        result = agent.resolve_ticket("TKT-001", "已更換新品", order_ref="SO-001")
        assert result["event"] == "ticket_resolved"
        assert result["status"] == "resolved"
        assert "resolved_at" in result

    def test_adjust_priority_emergency_keyword(self):
        from agents.after_service_agent.agent import AfterServiceAgent
        new = AfterServiceAgent._adjust_priority("quality_issue", "產品破損緊急處理", "medium")
        assert new == "emergency"

    def test_build_reply_with_order(self):
        from agents.after_service_agent.agent import AfterServiceAgent
        order_info = {"status": "shipped"}
        reply = AfterServiceAgent._build_reply(
            "T-1", "SO-1", "ACME", "quality_issue",
            "bad", "high", order_info,
        )
        assert "T-1" in reply["reply_content"]
        assert reply["feedback_type"] == "quality_issue"
        assert "SO-1" in reply["reply_content"]

    def test_handle_feedback_po_order(self):
        """Cover PO order_ref branch in handle_feedback"""
        agent = self._make_agent()
        with patch('requests.get') as mock_get:
            mock_get.return_value = mock_response(200, {
                "po_id": "PO-001", "status": "pending",
            })
            result = agent.handle_feedback(
                "TKT-PO", "PO-001", "ACME",
                "general_inquiry", "PO 進度查詢", "email", "low",
            )
        assert result["event"] == "ticket_acknowledged"

    def test_handle_feedback_po_order_404(self):
        agent = self._make_agent()
        with patch('requests.get') as mock_get:
            mock_get.return_value = mock_http_error(404)
            result = agent.handle_feedback(
                "TKT-PO2", "PO-FAKE", "ACME",
                "general_inquiry", "查詢", "email", "low",
            )
        assert result["event"] == "ticket_acknowledged"

    def test_build_reply_all_types(self):
        """Cover all feedback types in _build_reply"""
        from agents.after_service_agent.agent import AfterServiceAgent
        types_and_labels = [
            ("return_request", "退換貨"),
            ("warranty", "保固查詢"),
            ("something_new", "something_new"),  # fallback
        ]
        for ftype, _expected_label in types_and_labels:
            reply = AfterServiceAgent._build_reply(
                "T-1", "SO-1", "ACME", ftype,
                "test", "medium", {"status": "draft"},
            )
            assert reply["event"] == "ticket_acknowledged"
            assert reply["feedback_type"] == ftype

    def test_adjust_priority_downgrade(self):
        from agents.after_service_agent.agent import AfterServiceAgent
        # suggestion + no urgency keyword → downgrade medium → low
        new = AfterServiceAgent._adjust_priority("suggestion", "平凡建議", "medium")
        assert new == "low"

    def test_adjust_priority_edge_lowest(self):
        from agents.after_service_agent.agent import AfterServiceAgent
        # suggestion on low stays low
        new = AfterServiceAgent._adjust_priority("suggestion", "ok", "low")
        assert new == "low"

    def test_adjust_priority_edge_highest(self):
        from agents.after_service_agent.agent import AfterServiceAgent
        # quality_issue + urgency on emergency stays emergency
        new = AfterServiceAgent._adjust_priority("quality_issue", "緊急", "emergency")
        assert new == "emergency"

    def test_adjust_priority_unknown_type(self):
        from agents.after_service_agent.agent import AfterServiceAgent
        new = AfterServiceAgent._adjust_priority("bogus", "沒事", "medium")
        assert new == "medium"

    def test_demo(self):
        from agents.after_service_agent.agent import AfterServiceAgent, demo
        agent = AfterServiceAgent(erp_base="http://mock:8001")
        with patch('requests.get') as mock_get:
            mock_get.side_effect = [
                mock_response(200, {"so_id": "SO-2026-005", "status": "confirmed"}),
                mock_response(200, {"so_id": "SO-2026-006", "status": "shipped"}),
            ]
            demo(agent)

    def test_main_cli(self):
        from agents.after_service_agent import agent as mod
        with patch.object(mod, 'demo') as mock_demo:
            with patch('sys.argv', ['agent.py']):
                mod.main()
            mock_demo.assert_called_once()

    def test_main_cli_demo_flag(self):
        from agents.after_service_agent import agent as mod
        with patch.object(mod, 'demo') as mock_demo:
            with patch('sys.argv', ['agent.py', '--demo']):
                mod.main()
            mock_demo.assert_called_once()

    def test_interactive_exit(self):
        from agents.after_service_agent.agent import AfterServiceAgent, interactive
        agent = AfterServiceAgent(erp_base="http://mock:8001")
        with patch('builtins.input', side_effect=EOFError):
            interactive(agent)

    def test_interactive_quit(self):
        from agents.after_service_agent.agent import AfterServiceAgent, interactive
        agent = AfterServiceAgent(erp_base="http://mock:8001")
        with patch('builtins.input', side_effect=["exit"]):
            interactive(agent)

    def test_interactive_empty_line(self):
        from agents.after_service_agent.agent import AfterServiceAgent, interactive
        agent = AfterServiceAgent(erp_base="http://mock:8001")
        with patch('builtins.input', side_effect=["", "exit"]):
            interactive(agent)

    def test_interactive_feedback(self):
        from agents.after_service_agent.agent import AfterServiceAgent, interactive
        agent = AfterServiceAgent(erp_base="http://mock:8001")
        with patch('builtins.input', side_effect=[
            "feedback T1 SO-1 ACME quality_issue high urgent_msg",
            "exit",
        ]), patch('requests.get') as mock_get:
            mock_get.return_value = mock_response(200, {"so_id": "SO-1", "status": "confirmed"})
            interactive(agent)

    def test_interactive_update(self):
        from agents.after_service_agent.agent import AfterServiceAgent, interactive
        agent = AfterServiceAgent(erp_base="http://mock:8001")
        with patch('builtins.input', side_effect=[
            "update T1 investigating action_taken",
            "exit",
        ]):
            interactive(agent)

    def test_interactive_resolve(self):
        from agents.after_service_agent.agent import AfterServiceAgent, interactive
        agent = AfterServiceAgent(erp_base="http://mock:8001")
        with patch('builtins.input', side_effect=[
            "resolve T1 done SO-1",
            "exit",
        ]):
            interactive(agent)

    def test_interactive_unknown_cmd(self):
        from agents.after_service_agent.agent import AfterServiceAgent, interactive
        agent = AfterServiceAgent(erp_base="http://mock:8001")
        with patch('builtins.input', side_effect=["bogus", "exit"]):
            interactive(agent)

    def test_module_main_covers_block(self):
        """Ensure the __main__ block code is reached"""
        # Run main() with controlled argv to cover __main__ block
        from agents.after_service_agent import agent as mod
        with patch.object(mod, 'demo'), patch('sys.argv', ['agent.py', '--demo']):
            mod.main()


# ════════════════════════════════════════════════════════════════════════════
# ATP / CTP Agent
# ════════════════════════════════════════════════════════════════════════════

class TestATPCTPAgent:
    def _make_agent(self):
        from agents.atp_ctp_agent.agent import ATPCTPAgent
        return ATPCTPAgent(erp_base="http://mock:8001")

    def test_check_item(self):
        agent = self._make_agent()
        with patch('requests.get') as mock_get:
            mock_get.return_value = mock_response(200, {
                "item_code": "CPU-001", "description": "高階 CPU",
                "lead_time_days": 5, "safety_stock": 100, "daily_capacity": 500,
            })
            item = agent.check_item("CPU-001")
        assert item["item_code"] == "CPU-001"
        assert item["description"] == "高階 CPU"

    def test_atp_check_on_time(self):
        agent = self._make_agent()
        with patch('requests.post') as mock_post:
            mock_post.return_value = mock_response(200, {
                "check_id": "ATP-01", "item_code": "CPU-001",
                "qty": 50, "result": "on_time", "remarks": "可承諾",
                "available_qty": 100, "available_date": "2026-06-06",
            })
            result = agent.atp_check("CPU-001", 50, "2026-06-01")
        assert result["result"] == "on_time"

    def test_ctp_check_delayed(self):
        agent = self._make_agent()
        with patch('requests.post') as mock_post:
            mock_post.return_value = mock_response(200, {
                "check_id": "CTP-01", "item_code": "CPU-001",
                "qty": 9999, "result": "insufficient",
                "available_qty": 100, "batch_recommended": 20,
                "remarks": "產能不足",
            })
            result = agent.ctp_check("CPU-001", 9999, "2026-06-01",
                                     force_insufficient=True)
        assert result["result"] == "insufficient"

    def test_process_inquiry_success(self):
        agent = self._make_agent()
        with patch('requests.get') as mock_get, patch('requests.post') as mock_post:
            mock_get.return_value = mock_response(200, {
                "item_code": "CPU-001", "description": "測試 CPU",
                "lead_time_days": 5, "safety_stock": 100, "daily_capacity": 500,
            })
            mock_post.side_effect = [
                mock_response(200, {"check_id": "ATP-01", "item_code": "CPU-001",
                                    "qty": 50, "result": "on_time", "remarks": "可承諾",
                                    "available_qty": 50, "available_date": "2026-06-06"}),
                mock_response(200, {"check_id": "CTP-01", "item_code": "CPU-001",
                                    "qty": 50, "result": "on_time", "remarks": "可交付",
                                    "available_qty": 50, "available_date": "2026-06-06",
                                    "batch_recommended": 1}),
            ]
            result = agent.process_inquiry("INQ-001", "CPU-001", 50, "2026-06-01",
                                           customer="ACME")
        assert result["event"] == "atp_ctp_result"
        assert result["final_result"] == "on_time"
        assert result["item_code"] == "CPU-001"

    def test_process_inquiry_item_not_found(self):
        agent = self._make_agent()
        with patch('requests.get') as mock_get:
            mock_get.return_value = mock_http_error(404, "料號不存在")
            result = agent.process_inquiry("INQ-ERR", "BOGUS", 10, "2026-06-01")
        assert result["event"] == "atp_ctp_error"

    def test_process_inquiry_atp_error(self):
        agent = self._make_agent()
        with patch('requests.get') as mock_get, patch('requests.post') as mock_post:
            mock_get.return_value = mock_response(200, {
                "item_code": "CPU-001", "description": "CPU",
                "lead_time_days": 5, "safety_stock": 100, "daily_capacity": 500,
            })
            mock_post.return_value = mock_http_error(500, "Server Error")
            result = agent.process_inquiry("INQ-ERR2", "CPU-001", 50, "2026-06-01")
        assert result["event"] == "atp_ctp_error"

    def test_process_inquiry_ctp_error(self):
        agent = self._make_agent()
        with patch('requests.get') as mock_get, patch('requests.post') as mock_post:
            mock_get.return_value = mock_response(200, {
                "item_code": "CPU-001", "description": "CPU",
                "lead_time_days": 5, "safety_stock": 100, "daily_capacity": 500,
            })
            mock_post.side_effect = [
                mock_response(200, {"check_id": "ATP-01", "item_code": "CPU-001",
                                    "qty": 50, "result": "on_time", "remarks": "OK",
                                    "available_qty": 50, "available_date": "2026-06-06"}),
                mock_http_error(500, "CTP Error"),
            ]
            result = agent.process_inquiry("INQ-CTP-ERR", "CPU-001", 50, "2026-06-01")
        assert result["event"] == "atp_ctp_error"

    def test_atp_check_with_force_delay(self):
        agent = self._make_agent()
        with patch('requests.post') as mock_post:
            mock_post.return_value = mock_response(200, {
                "check_id": "ATP-01", "item_code": "CPU-001",
                "qty": 50, "result": "delayed", "remarks": "延遲",
                "available_qty": 50, "available_date": "2026-06-10",
            })
            result = agent.atp_check("CPU-001", 50, "2026-06-01",
                                     force_delay=True, force_insufficient=False)
        assert result["result"] == "delayed"

    def test_ctp_check_force_delay(self):
        agent = self._make_agent()
        with patch('requests.post') as mock_post:
            mock_post.return_value = mock_response(200, {
                "check_id": "CTP-01", "item_code": "CPU-001",
                "qty": 50, "result": "delayed", "remarks": "延遲",
                "available_qty": 50, "available_date": "2026-06-10",
                "batch_recommended": 2,
            })
            result = agent.ctp_check("CPU-001", 50, "2026-06-01",
                                     force_insufficient=False, force_delay=True)
        assert result["result"] == "delayed"

    def test_build_summary_all_results(self):
        from agents.atp_ctp_agent.agent import ATPCTPAgent
        for result_type in ["on_time", "delayed", "insufficient", "bogus"]:
            item = {"item_code": "CPU-001", "description": "CPU", "lead_time_days": 5}
            atp = {"result": "on_time"}
            ctp = {"result": result_type, "remarks": "test"}
            final = {"result": result_type, "available_qty": 100, "available_date": "2026-06-06"}
            summary = ATPCTPAgent._build_summary("REF-1", item, atp, ctp, final)
            assert summary["final_result"] == result_type
            assert summary["lead_time_days"] == 5

    def test_demo_atp_ctp(self):
        from agents.atp_ctp_agent.agent import ATPCTPAgent, demo
        agent = ATPCTPAgent(erp_base="http://mock:8001")
        with patch('requests.get') as mock_get, patch('requests.post') as mock_post:
            mock_get.return_value = mock_response(200, {
                "item_code": "E2E-SKU-001", "description": "Test",
                "lead_time_days": 5, "safety_stock": 100, "daily_capacity": 500,
            })
            mock_post.return_value = mock_response(200, {
                "item_code": "E2E-SKU-001", "qty": 100, "result": "on_time",
                "remarks": "OK", "available_qty": 100, "available_date": "2026-06-15",
                "batch_recommended": 1,
            })
            results = demo(agent)
        assert len(results) == 3

    def test_main_atp_ctp(self):
        from agents.atp_ctp_agent import agent as mod
        with patch.object(mod, 'demo') as mock_demo:
            with patch('sys.argv', ['agent.py']):
                mod.main()
            mock_demo.assert_called_once()

    def test_main_atp_ctp_demo(self):
        from agents.atp_ctp_agent import agent as mod
        with patch.object(mod, 'demo') as mock_demo:
            with patch('sys.argv', ['agent.py', '--demo']):
                mod.main()
            mock_demo.assert_called_once()

    def test_interactive_atp_exit(self):
        from agents.atp_ctp_agent.agent import ATPCTPAgent, interactive
        agent = ATPCTPAgent(erp_base="http://mock:8001")
        with patch('builtins.input', side_effect=["exit"]):
            interactive(agent)

    def test_interactive_atp_eof(self):
        from agents.atp_ctp_agent.agent import ATPCTPAgent, interactive
        agent = ATPCTPAgent(erp_base="http://mock:8001")
        with patch('builtins.input', side_effect=EOFError):
            interactive(agent)

    def test_interactive_atp_empty(self):
        from agents.atp_ctp_agent.agent import ATPCTPAgent, interactive
        agent = ATPCTPAgent(erp_base="http://mock:8001")
        with patch('builtins.input', side_effect=["", "exit"]):
            interactive(agent)

    def test_interactive_atp_invalid_count(self):
        from agents.atp_ctp_agent.agent import ATPCTPAgent, interactive
        agent = ATPCTPAgent(erp_base="http://mock:8001")
        with patch('builtins.input', side_effect=["abc def ghi", "exit"]):
            interactive(agent)

    def test_interactive_atp_query(self):
        from agents.atp_ctp_agent.agent import ATPCTPAgent, interactive
        agent = ATPCTPAgent(erp_base="http://mock:8001")
        with patch('builtins.input', side_effect=[
            "CPU-001 100 2026-06-15", "exit",
        ]), patch('requests.get') as mock_get, patch('requests.post') as mock_post:
            mock_get.return_value = mock_response(200, {
                "item_code": "CPU-001", "description": "CPU",
                "lead_time_days": 5, "safety_stock": 100, "daily_capacity": 500,
            })
            mock_post.return_value = mock_response(200, {
                "item_code": "CPU-001", "qty": 100, "result": "on_time",
                "remarks": "OK", "available_qty": 100, "available_date": "2026-06-15",
                "batch_recommended": 1,
            })
            interactive(agent)

    def test_interactive_atp_too_few_args(self):
        from agents.atp_ctp_agent.agent import ATPCTPAgent, interactive
        agent = ATPCTPAgent(erp_base="http://mock:8001")
        with patch('builtins.input', side_effect=["just_one", "exit"]):
            interactive(agent)

    def test_module_main_covers_atp_block(self):
        from agents.atp_ctp_agent import agent as mod
        with patch.object(mod, 'demo'), patch('sys.argv', ['agent.py', '--demo']):
            mod.main()


# ════════════════════════════════════════════════════════════════════════════
# Customer Service Agent
# ════════════════════════════════════════════════════════════════════════════

class TestCustomerServiceAgent:
    def _make_agent(self):
        from agents.customer_service_agent.agent import CustomerServiceAgent
        return CustomerServiceAgent(erp_base="http://mock:8001")

    def test_process_inquiry_success(self):
        agent = self._make_agent()
        with patch('requests.get') as mock_get, patch('requests.post') as mock_post:
            mock_get.return_value = mock_response(200, {
                "item_code": "CPU-001", "description": "高階 CPU",
            })
            mock_post.return_value = mock_response(200, {
                "item_code": "CPU-001", "qty": 100, "result": "on_time",
                "remarks": "可承諾 100 件",
            })
            result = agent.process_inquiry(
                "INQ-CS-001",
                [{"item_code": "CPU-001", "qty": 100}],
                "2026-06-15", "ACME Corp",
            )
        assert result["event"] == "inquiry_replied"
        assert result["items_count"] == 1
        assert "✅" in result["content"]

    def test_process_inquiry_mixed_items(self):
        agent = self._make_agent()
        with patch('requests.get') as mock_get, patch('requests.post') as mock_post:
            mock_get.side_effect = [
                mock_response(200, {"item_code": "CPU-001", "description": "CPU"}),
                mock_http_error(404, "不存在"),  # second item not found
            ]
            mock_post.return_value = mock_response(200, {
                "item_code": "CPU-001", "qty": 50, "result": "on_time",
                "remarks": "OK",
            })
            result = agent.process_inquiry(
                "INQ-CS-002",
                [
                    {"item_code": "CPU-001", "qty": 50},
                    {"item_code": "BOGUS", "qty": 30},
                ],
                "2026-06-15", "ACME",
            )
        # Bogus item filtered, only valid item processed
        assert result["items_count"] == 1  # only valid items passed to _build_reply
        assert len(result["atp_summary"]) == 1  # but only 1 ATP ran

    def test_process_inquiry_all_invalid(self):
        agent = self._make_agent()
        with patch('requests.get') as mock_get:
            mock_get.return_value = mock_http_error(404, "不存在")
            result = agent.process_inquiry(
                "INQ-BAD", [{"item_code": "BOGUS", "qty": 1}], "2026-06-15",
            )
        assert result["result"] == "rejected"

    def test_check_so_status(self):
        agent = self._make_agent()
        with patch('requests.get') as mock_get:
            mock_get.side_effect = [
                mock_response(200, {"so_id": "SO-001", "status": "confirmed"}),
                mock_response(200, [{"line_no": 1, "item_code": "CPU-001"}]),
            ]
            so = agent.check_so_status("SO-001")
        assert so["so_id"] == "SO-001"
        assert len(so["lines"]) == 1

    def test_send_asn(self):
        agent = self._make_agent()
        with patch('requests.get') as mock_get:
            mock_get.side_effect = [
                mock_response(200, {"so_id": "SO-001", "customer_id": "CUST-001",
                                    "status": "confirmed"}),
                mock_response(200, [{"line_no": 1}]),
                mock_response(200, {"shipping_id": "SH-001", "status": "packing"}),
            ]
            result = agent.send_asn("SO-001", "SH-001")
        assert result["event"] == "asn_issued"
        assert result["customer_id"] == "CUST-001"

    def test_send_shipping_notice(self):
        agent = self._make_agent()
        result = agent.send_shipping_notice("SO-001", "TRK-001")
        assert result["event"] == "shipping_notice_sent"
        assert result["tracking_no"] == "TRK-001"

    def test_send_invoice(self):
        agent = self._make_agent()
        with patch('requests.get') as mock_get:
            mock_get.return_value = mock_response(200, {
                "invoice_id": "INV-001", "so_id": "SO-001", "amount": 5000.0,
            })
            result = agent.send_invoice("INV-001")
        assert result["event"] == "invoice_sent"
        assert result["amount"] == 5000.0

    def test_handle_customer_voice(self):
        agent = self._make_agent()
        result = agent.handle_customer_voice("PO-001", "出貨了嗎?", "progress_inquiry")
        assert result["event"] == "customer_voice_received"
        assert result["handled_by"] == "Customer Service Agent"

    def test_patch_method(self):
        agent = self._make_agent()
        with patch('requests.patch') as mock_patch:
            mock_patch.return_value = mock_response(200, {"result": "ok"})
            result = agent._patch("/api/v1/test", params={"key": "val"})
        assert result["result"] == "ok"

    def test_process_inquiry_atp_partial_fail(self):
        """One item ATP succeeds, another fails"""
        agent = self._make_agent()
        with patch('requests.get') as mock_get, patch('requests.post') as mock_post:
            mock_get.side_effect = [
                mock_response(200, {"item_code": "CPU-001", "description": "CPU"}),
                mock_response(200, {"item_code": "MEM-001", "description": "Memory"}),
            ]
            mock_post.side_effect = [
                mock_response(200, {"item_code": "CPU-001", "qty": 10, "result": "on_time",
                                    "remarks": "OK"}),
                mock_http_error(500, "ATP Fail"),
            ]
            result = agent.process_inquiry(
                "INQ-CS-PART",
                [{"item_code": "CPU-001", "qty": 10},
                 {"item_code": "MEM-001", "qty": 5}],
                "2026-06-15", "ACME",
            )
        assert result["event"] == "inquiry_replied"
        assert len(result["atp_summary"]) == 1

    def test_build_reply_all_results(self):
        from agents.customer_service_agent.agent import CustomerServiceAgent
        items = [
            {"item_code": "CPU-001", "description": "CPU", "qty": 10},
            {"item_code": "MEM-001", "description": "RAM", "qty": 20},
            {"item_code": "GPU-001", "description": "GPU", "qty": 5},
        ]
        atp_results = [
            {"item_code": "CPU-001", "qty": 10, "result": "on_time", "remarks": "可承諾"},
            {"item_code": "MEM-001", "qty": 20, "result": "delayed", "remarks": "略延"},
            {"item_code": "GPU-001", "qty": 5, "result": "insufficient", "remarks": "不足"},
        ]
        reply = CustomerServiceAgent._build_reply(
            "INQ-1", "ACME", "email", items, atp_results,
        )
        assert "✅" in reply["content"]
        assert "⚠️" in reply["content"]
        assert "❌" in reply["content"]
        assert reply["items_count"] == 3

    def test_send_invoice_no_so(self):
        agent = self._make_agent()
        with patch('requests.get') as mock_get:
            mock_get.return_value = mock_response(200, {
                "invoice_id": "INV-001", "amount": 5000.0,
            })
            result = agent.send_invoice("INV-001")
        assert result["event"] == "invoice_sent"
        assert result["amount"] == 5000.0
        assert result["so_id"] == ""

    def test_process_inquiry_other_channel(self):
        agent = self._make_agent()
        with patch('requests.get') as mock_get, patch('requests.post') as mock_post:
            mock_get.return_value = mock_response(200, {
                "item_code": "CPU-001", "description": "CPU",
            })
            mock_post.return_value = mock_response(200, {
                "item_code": "CPU-001", "qty": 100, "result": "on_time",
                "remarks": "OK",
            })
            result = agent.process_inquiry(
                "INQ-CS-WEB",
                [{"item_code": "CPU-001", "qty": 100}],
                "2026-06-15", "ACME", channel="web",
            )
        assert result["channel"] == "web"

    def test_demo_cs(self):
        from agents.customer_service_agent.agent import CustomerServiceAgent, demo
        agent = CustomerServiceAgent(erp_base="http://mock:8001")
        with patch('requests.get') as mock_get, patch('requests.post') as mock_post:
            mock_get.side_effect = [
                mock_response(200, {"item_code": "E2E-SKU-001", "description": "SKU001"}),
                mock_response(200, {"item_code": "E2E-SKU-001", "description": "SKU001"}),
                mock_response(200, {"item_code": "E2E-SKU-003", "description": "SKU003"}),
                # send_asn
                mock_response(200, {"so_id": "E2E-SO-001", "status": "confirmed", "customer_id": "CUST-001"}),
                mock_response(200, [{"line_no": 1}]),
                mock_response(200, {"shipping_id": "E2E-SHP-001", "status": "packing"}),
            ]
            mock_post.side_effect = [
                mock_response(200, {"item_code": "E2E-SKU-001", "qty": 100, "result": "on_time", "remarks": "OK"}),
                mock_response(200, {"item_code": "E2E-SKU-001", "qty": 50, "result": "on_time", "remarks": "OK"}),
                mock_response(200, {"item_code": "E2E-SKU-003", "qty": 30, "result": "on_time", "remarks": "OK"}),
            ]
            demo(agent)

    def test_main_cs(self):
        from agents.customer_service_agent import agent as mod
        with patch.object(mod, 'demo') as mock_demo:
            with patch('sys.argv', ['agent.py']):
                mod.main()
            mock_demo.assert_called_once()

    def test_main_cs_demo(self):
        from agents.customer_service_agent import agent as mod
        with patch.object(mod, 'demo') as mock_demo:
            with patch('sys.argv', ['agent.py', '--demo']):
                mod.main()
            mock_demo.assert_called_once()

    def test_interactive_cs_exit(self):
        from agents.customer_service_agent.agent import CustomerServiceAgent, interactive
        agent = CustomerServiceAgent(erp_base="http://mock:8001")
        with patch('builtins.input', side_effect=["exit"]):
            interactive(agent)

    def test_interactive_cs_eof(self):
        from agents.customer_service_agent.agent import CustomerServiceAgent, interactive
        agent = CustomerServiceAgent(erp_base="http://mock:8001")
        with patch('builtins.input', side_effect=EOFError):
            interactive(agent)

    def test_interactive_cs_empty(self):
        from agents.customer_service_agent.agent import CustomerServiceAgent, interactive
        agent = CustomerServiceAgent(erp_base="http://mock:8001")
        with patch('builtins.input', side_effect=["", "exit"]):
            interactive(agent)

    def test_interactive_cs_query(self):
        from agents.customer_service_agent.agent import CustomerServiceAgent, interactive
        agent = CustomerServiceAgent(erp_base="http://mock:8001")
        with patch('builtins.input', side_effect=[
            "inquiry INQ-1 CPU-001 10 2026-06-15", "exit",
        ]), patch('requests.get') as mock_get, patch('requests.post') as mock_post:
            mock_get.return_value = mock_response(200, {"item_code": "CPU-001", "description": "CPU"})
            mock_post.return_value = mock_response(200, {"item_code": "CPU-001", "qty": 10, "result": "on_time", "remarks": "OK"})
            interactive(agent)

    def test_interactive_cs_so(self):
        from agents.customer_service_agent.agent import CustomerServiceAgent, interactive
        agent = CustomerServiceAgent(erp_base="http://mock:8001")
        with patch('builtins.input', side_effect=["so SO-001", "exit"]), \
             patch('requests.get') as mock_get:
            mock_get.side_effect = [
                mock_response(200, {"so_id": "SO-001", "status": "confirmed"}),
                mock_response(200, [{"line_no": 1}]),
            ]
            interactive(agent)

    def test_interactive_cs_asn(self):
        from agents.customer_service_agent.agent import CustomerServiceAgent, interactive
        agent = CustomerServiceAgent(erp_base="http://mock:8001")
        with patch('builtins.input', side_effect=["asn SO-001 SH-001", "exit"]), \
             patch('requests.get') as mock_get:
            mock_get.side_effect = [
                mock_response(200, {"so_id": "SO-001", "status": "confirmed", "customer_id": "CUST"}),
                mock_response(200, [{"line_no": 1}]),
                mock_response(200, {"shipping_id": "SH-001", "status": "packing"}),
            ]
            interactive(agent)

    def test_interactive_cs_voice(self):
        from agents.customer_service_agent.agent import CustomerServiceAgent, interactive
        agent = CustomerServiceAgent(erp_base="http://mock:8001")
        with patch('builtins.input', side_effect=["voice PO-001 progress msg", "exit"]):
            interactive(agent)

    def test_interactive_cs_unknown(self):
        from agents.customer_service_agent.agent import CustomerServiceAgent, interactive
        agent = CustomerServiceAgent(erp_base="http://mock:8001")
        with patch('builtins.input', side_effect=["bogus", "exit"]):
            interactive(agent)


# ════════════════════════════════════════════════════════════════════════════
# Logistics Agent
# ════════════════════════════════════════════════════════════════════════════

class TestLogisticsAgent:
    def _make_agent(self):
        from agents.logistics_agent.agent import LogisticsAgent
        return LogisticsAgent(erp_base="http://mock:8001")

    def _shipping_resp(self, tracking_no=None):
        return mock_response(200, {
            "shipping_id": "SH-001", "so_id": "SO-001",
            "status": "shipped",
            "tracking_no": tracking_no,
        })

    def _logistics_resp(self, tracking_no="TRK-001", status="booked"):
        return mock_response(200, {
            "tracking_no": tracking_no, "status": status,
            "carrier": "DHL", "shipping_id": "SH-001",
        })

    def test_arrange_shipment_new(self):
        agent = self._make_agent()
        with patch('requests.get') as mock_get, patch('requests.post') as mock_post:
            mock_get.return_value = self._shipping_resp(tracking_no=None)
            mock_post.return_value = self._logistics_resp("TRK-001", "booked")
            result = agent.arrange_shipment("SH-001", "DHL", "Shanghai", "LAX")
        assert result["event"] == "shipment_arranged"
        assert result["tracking_no"] == "TRK-001"

    def test_arrange_shipment_already_has_tracking(self):
        agent = self._make_agent()
        with patch('requests.get') as mock_get:
            mock_get.side_effect = [
                self._shipping_resp(tracking_no="TRK-EXIST"),
                self._logistics_resp("TRK-EXIST", "in_transit"),
                mock_response(200, [{"status": "booked"}, {"status": "in_transit"}]),
            ]
            result = agent.arrange_shipment("SH-001")
        assert "TRK-EXIST" in str(result)

    def test_depart(self):
        agent = self._make_agent()
        with patch('requests.post') as mock_post:
            mock_post.return_value = self._logistics_resp(status="in_transit")
            result = agent.depart("TRK-001", origin_port="KHH", vessel_flight="BR-123")
        assert result["status"] == "in_transit"

    def test_customs_start(self):
        agent = self._make_agent()
        with patch('requests.post') as mock_post:
            mock_post.return_value = self._logistics_resp(status="customs")
            result = agent.customs_start("TRK-001", "LAX", "BL-001")
        assert result["status"] == "customs"

    def test_customs_hold(self):
        agent = self._make_agent()
        with patch('requests.post') as mock_post:
            mock_post.return_value = self._logistics_resp(status="customs_hold")
            result = agent.customs_hold("TRK-001", "文件查驗")
        assert result["status"] == "customs_hold"

    def test_customs_clear(self):
        agent = self._make_agent()
        with patch('requests.post') as mock_post:
            mock_post.return_value = self._logistics_resp(status="in_transit")
            result = agent.customs_clear("TRK-001", "放行")
        assert result["status"] == "in_transit"

    def test_arrive(self):
        agent = self._make_agent()
        with patch('requests.post') as mock_post:
            mock_post.return_value = self._logistics_resp(status="arrived")
            result = agent.arrive("TRK-001", "已送達")
        assert result["status"] == "arrived"

    def test_partial_arrive(self):
        agent = self._make_agent()
        with patch('requests.post') as mock_post:
            mock_post.return_value = self._logistics_resp(status="partial_delivery")
            result = agent.partial_arrive("TRK-001", 5, 5)
        assert result["status"] == "partial_delivery"

    def test_deliver_sign(self):
        agent = self._make_agent()
        with patch('requests.post') as mock_post:
            mock_post.return_value = self._logistics_resp(status="delivered")
            result = agent.deliver_sign("TRK-001", "張三", "簽收完成")
        assert result["status"] == "delivered"

    def test_mark_failed(self):
        agent = self._make_agent()
        with patch('requests.post') as mock_post:
            mock_post.return_value = self._logistics_resp(status="failed")
            result = agent.mark_failed("TRK-001", "地址錯誤", "無法送達")
        assert result["status"] == "failed"

    def test_reroute(self):
        agent = self._make_agent()
        with patch('requests.post') as mock_post:
            mock_post.return_value = mock_response(200, {
                "tracking_no": "TRK-001", "status": "reroute",
                "carrier": "FedEx",
            })
            result = agent.reroute("TRK-001", "FedEx", "更正地址")
        assert result["status"] == "reroute"
        assert result["carrier"] == "FedEx"

    def test_track_shipment(self):
        agent = self._make_agent()
        with patch('requests.get') as mock_get:
            mock_get.return_value = self._logistics_resp("TRK-001", "in_transit")
            result = agent.track_shipment("TRK-001")
        assert result["event"] == "tracking_queried"
        assert result["status"] == "in_transit"

    def test_track_shipment_full(self):
        agent = self._make_agent()
        with patch('requests.get') as mock_get:
            mock_get.side_effect = [
                self._logistics_resp("TRK-001", "delivered"),
                mock_response(200, [
                    {"status": "booked"}, {"status": "in_transit"},
                    {"status": "arrived"}, {"status": "delivered"},
                ]),
            ]
            result = agent.track_shipment_full("TRK-001")
        assert len(result["events"]) == 4
        assert result["chain"] == ["booked", "in_transit", "arrived", "delivered"]

    def test_list_active(self):
        agent = self._make_agent()
        with patch('requests.get') as mock_get:
            mock_get.return_value = mock_response(200, [
                {"tracking_no": "TRK-001", "status": "in_transit", "carrier": "DHL"},
            ])
            result = agent.list_active()
        assert result["count"] == 1

    def test_process_full(self):
        agent = self._make_agent()
        with patch('requests.get') as mock_get, patch('requests.post') as mock_post:
            # arrange → get shipping; track_shipment_full → get logistics + events
            mock_get.side_effect = [
                self._shipping_resp(tracking_no=None),
                self._logistics_resp("TRK-FULL", "delivered"),
                mock_response(200, [
                    {"status": "booked"}, {"status": "in_transit"},
                    {"status": "customs"}, {"status": "in_transit"},
                    {"status": "arrived"}, {"status": "delivered"},
                ]),
            ]
            # each post returns a logistics response
            mock_post.side_effect = [
                self._logistics_resp("TRK-FULL", "booked"),       # arrange
                self._logistics_resp("TRK-FULL", "in_transit"),   # depart
                self._logistics_resp("TRK-FULL", "customs"),      # customs
                self._logistics_resp("TRK-FULL", "in_transit"),   # clear
                self._logistics_resp("TRK-FULL", "arrived"),      # arrive
                self._logistics_resp("TRK-FULL", "delivered"),    # sign
            ]
            result = agent.process_full("SH-001", signed_by="李四")
        assert result["event"] == "logistics_complete"

    def test_process_full_no_sign(self):
        agent = self._make_agent()
        with patch('requests.get') as mock_get, patch('requests.post') as mock_post:
            mock_get.side_effect = [
                self._shipping_resp(tracking_no=None),
                self._logistics_resp("TRK-FULL2", "arrived"),
                mock_response(200, [{"status": "booked"}, {"status": "arrived"}]),
            ]
            mock_post.side_effect = [
                self._logistics_resp("TRK-FULL2", "booked"),
                self._logistics_resp("TRK-FULL2", "in_transit"),
                self._logistics_resp("TRK-FULL2", "customs"),
                self._logistics_resp("TRK-FULL2", "in_transit"),
                self._logistics_resp("TRK-FULL2", "arrived"),
            ]
            result = agent.process_full("SH-002")
        assert result["event"] == "logistics_complete"

    def test_gen_tracking_with_dash(self):
        agent = self._make_agent()
        tk = agent._gen_tracking("SH-ABC123")
        assert tk == "TRK-ABC123"

    def test_gen_tracking_no_dash(self):
        agent = self._make_agent()
        tk = agent._gen_tracking("SH001")
        assert tk.startswith("TRK-")
        # TRK- + 8 hex chars = 12
        assert len(tk) == 12

    def test_list_active_with_carrier(self):
        agent = self._make_agent()
        with patch('requests.get') as mock_get:
            mock_get.return_value = mock_response(200, [])
            result = agent.list_active(carrier="DHL")
        assert result["count"] == 0

    def test_demo_logistics(self):
        from agents.logistics_agent.agent import LogisticsAgent, demo
        agent = LogisticsAgent(erp_base="http://mock:8001")
        with patch('requests.post') as mock_post, patch('requests.get') as mock_get:
            # seed data posts
            mock_post.side_effect = [
                mock_response(200, {}),  # seed item
                mock_response(200, {}),  # seed customer
                mock_response(200, {}),  # seed PO
                mock_response(200, {}),  # convert
                mock_response(200, {}),  # create shipping
                # arrange
                mock_response(200, {"tracking_no": "TRK-E2E-001", "carrier": "DHL"}),
                # depart
                mock_response(200, {"tracking_no": "TRK-E2E-001", "status": "in_transit"}),
                # customs
                mock_response(200, {"tracking_no": "TRK-E2E-001", "status": "customs"}),
                # clear
                mock_response(200, {"tracking_no": "TRK-E2E-001", "status": "in_transit"}),
                # arrive
                mock_response(200, {"tracking_no": "TRK-E2E-001", "status": "arrived"}),
                # arrange tk2
                mock_response(200, {"tracking_no": "TRK-CUSTOMS-DEMO"}),
                # depart tk2
                mock_response(200, {"tracking_no": "TRK-CUSTOMS-DEMO", "status": "in_transit"}),
                # customs tk2
                mock_response(200, {"tracking_no": "TRK-CUSTOMS-DEMO", "status": "customs"}),
                # hold tk2
                mock_response(200, {"tracking_no": "TRK-CUSTOMS-DEMO", "status": "customs_hold"}),
                # clear tk2
                mock_response(200, {"tracking_no": "TRK-CUSTOMS-DEMO", "status": "in_transit"}),
                # arrive tk2
                mock_response(200, {"tracking_no": "TRK-CUSTOMS-DEMO", "status": "arrived"}),
                # arrange tk3
                mock_response(200, {"tracking_no": "TRK-FAIL-DEMO"}),
                # depart tk3
                mock_response(200, {"tracking_no": "TRK-FAIL-DEMO", "status": "in_transit"}),
                # fail tk3
                mock_response(200, {"tracking_no": "TRK-FAIL-DEMO", "status": "failed"}),
                # reroute tk3
                mock_response(200, {"tracking_no": "TRK-FAIL-DEMO", "status": "reroute", "carrier": "FedEx"}),
            ]
            mock_get.side_effect = [
                # arrange_shipment shipping get
                mock_response(200, {"shipping_id": "LGT-SHP-001", "so_id": "LGT-SO-001",
                                    "status": "shipped", "tracking_no": None, "customs_date": None}),
                # track_shipment_full for tk
                mock_response(200, {"tracking_no": "TRK-E2E-001", "status": "arrived", "carrier": "DHL"}),
                mock_response(200, [{"status": "booked"}, {"status": "arrived"}]),
                # active
                mock_response(200, []),
            ]
            demo(agent)

    def test_main_logistics(self):
        from agents.logistics_agent import agent as mod
        with patch.object(mod, 'demo') as mock_demo:
            with patch('sys.argv', ['agent.py']):
                mod.main()
            mock_demo.assert_called_once()

    def test_main_logistics_demo(self):
        from agents.logistics_agent import agent as mod
        with patch.object(mod, 'demo') as mock_demo:
            with patch('sys.argv', ['agent.py', '--demo']):
                mod.main()
            mock_demo.assert_called_once()

    def test_interactive_logistics_exit(self):
        from agents.logistics_agent.agent import LogisticsAgent, interactive
        agent = LogisticsAgent(erp_base="http://mock:8001")
        with patch('builtins.input', side_effect=["exit"]):
            interactive(agent)

    def test_interactive_logistics_eof(self):
        from agents.logistics_agent.agent import LogisticsAgent, interactive
        agent = LogisticsAgent(erp_base="http://mock:8001")
        with patch('builtins.input', side_effect=EOFError):
            interactive(agent)

    def test_interactive_logistics_empty(self):
        from agents.logistics_agent.agent import LogisticsAgent, interactive
        agent = LogisticsAgent(erp_base="http://mock:8001")
        with patch('builtins.input', side_effect=["", "exit"]):
            interactive(agent)

    def test_interactive_logistics_arrange(self):
        from agents.logistics_agent.agent import LogisticsAgent, interactive
        agent = LogisticsAgent(erp_base="http://mock:8001")
        with patch('builtins.input', side_effect=["arrange SH-001", "exit"]), \
             patch('requests.get') as mock_get, patch('requests.post') as mock_post:
            mock_get.return_value = mock_response(200, {
                "shipping_id": "SH-001", "so_id": "SO-001",
                "status": "shipped", "tracking_no": None,
            })
            mock_post.return_value = mock_response(200, {"tracking_no": "TRK-001", "carrier": "DHL"})
            interactive(agent)

    def test_interactive_logistics_depart(self):
        from agents.logistics_agent.agent import LogisticsAgent, interactive
        agent = LogisticsAgent(erp_base="http://mock:8001")
        with patch('builtins.input', side_effect=["depart TRK-001 SH port", "exit"]), \
             patch('requests.post') as mock_post:
            mock_post.return_value = mock_response(200, {"status": "in_transit"})
            interactive(agent)

    def test_interactive_logistics_customs(self):
        from agents.logistics_agent.agent import LogisticsAgent, interactive
        agent = LogisticsAgent(erp_base="http://mock:8001")
        with patch('builtins.input', side_effect=["customs TRK-001 LA bl", "exit"]), \
             patch('requests.post') as mock_post:
            mock_post.return_value = mock_response(200, {"status": "customs"})
            interactive(agent)

    def test_interactive_logistics_hold(self):
        from agents.logistics_agent.agent import LogisticsAgent, interactive
        agent = LogisticsAgent(erp_base="http://mock:8001")
        with patch('builtins.input', side_effect=["hold TRK-001 reason", "exit"]), \
             patch('requests.post') as mock_post:
            mock_post.return_value = mock_response(200, {"status": "customs_hold"})
            interactive(agent)

    def test_interactive_logistics_clear(self):
        from agents.logistics_agent.agent import LogisticsAgent, interactive
        agent = LogisticsAgent(erp_base="http://mock:8001")
        with patch('builtins.input', side_effect=["clear TRK-001 note", "exit"]), \
             patch('requests.post') as mock_post:
            mock_post.return_value = mock_response(200, {"status": "in_transit"})
            interactive(agent)

    def test_interactive_logistics_arrive(self):
        from agents.logistics_agent.agent import LogisticsAgent, interactive
        agent = LogisticsAgent(erp_base="http://mock:8001")
        with patch('builtins.input', side_effect=["arrive TRK-001 note", "exit"]), \
             patch('requests.post') as mock_post:
            mock_post.return_value = mock_response(200, {"status": "arrived"})
            interactive(agent)

    def test_interactive_logistics_partial(self):
        from agents.logistics_agent.agent import LogisticsAgent, interactive
        agent = LogisticsAgent(erp_base="http://mock:8001")
        with patch('builtins.input', side_effect=["partial TRK-001 5 3", "exit"]), \
             patch('requests.post') as mock_post:
            mock_post.return_value = mock_response(200, {"status": "partial_delivery"})
            interactive(agent)

    def test_interactive_logistics_sign(self):
        from agents.logistics_agent.agent import LogisticsAgent, interactive
        agent = LogisticsAgent(erp_base="http://mock:8001")
        with patch('builtins.input', side_effect=["sign TRK-001 張三 到了", "exit"]), \
             patch('requests.post') as mock_post:
            mock_post.return_value = mock_response(200, {"status": "delivered"})
            interactive(agent)

    def test_interactive_logistics_fail(self):
        from agents.logistics_agent.agent import LogisticsAgent, interactive
        agent = LogisticsAgent(erp_base="http://mock:8001")
        with patch('builtins.input', side_effect=["fail TRK-001 reason note", "exit"]), \
             patch('requests.post') as mock_post:
            mock_post.return_value = mock_response(200, {"status": "failed"})
            interactive(agent)

    def test_interactive_logistics_reroute(self):
        from agents.logistics_agent.agent import LogisticsAgent, interactive
        agent = LogisticsAgent(erp_base="http://mock:8001")
        with patch('builtins.input', side_effect=["reroute TRK-001 FedEx", "exit"]), \
             patch('requests.post') as mock_post:
            mock_post.return_value = mock_response(200, {"status": "reroute"})
            interactive(agent)

    def test_interactive_logistics_track(self):
        from agents.logistics_agent.agent import LogisticsAgent, interactive
        agent = LogisticsAgent(erp_base="http://mock:8001")
        with patch('builtins.input', side_effect=["track TRK-001", "exit"]), \
             patch('requests.get') as mock_get:
            mock_get.side_effect = [
                mock_response(200, {"tracking_no": "TRK-001", "status": "in_transit"}),
                mock_response(200, [{"status": "booked"}]),
            ]
            interactive(agent)

    def test_interactive_logistics_active(self):
        from agents.logistics_agent.agent import LogisticsAgent, interactive
        agent = LogisticsAgent(erp_base="http://mock:8001")
        with patch('builtins.input', side_effect=["active DHL", "exit"]), \
             patch('requests.get') as mock_get:
            mock_get.return_value = mock_response(200, [])
            interactive(agent)

    def test_interactive_logistics_full_cmd(self):
        from agents.logistics_agent.agent import LogisticsAgent, interactive
        agent = LogisticsAgent(erp_base="http://mock:8001")
        with patch('builtins.input', side_effect=["full SH-001", "exit"]), \
             patch('requests.get') as mock_get, patch('requests.post') as mock_post:
            mock_get.side_effect = [
                mock_response(200, {"shipping_id": "SH-001", "so_id": "SO-001",
                                    "status": "shipped", "tracking_no": None}),
            ]
            mock_post.side_effect = [
                mock_response(200, {"tracking_no": "TRK-F", "carrier": "DHL"}),
                mock_response(200, {"status": "in_transit"}),
                mock_response(200, {"status": "customs"}),
                mock_response(200, {"status": "in_transit"}),
                mock_response(200, {"status": "arrived"}),
            ]
            interactive(agent)

    def test_interactive_logistics_unknown(self):
        from agents.logistics_agent.agent import LogisticsAgent, interactive
        agent = LogisticsAgent(erp_base="http://mock:8001")
        with patch('builtins.input', side_effect=["bogus", "exit"]):
            interactive(agent)


# ════════════════════════════════════════════════════════════════════════════
# PO-to-SO Agent
# ════════════════════════════════════════════════════════════════════════════

class TestPOtoSOAgent:
    def _make_agent(self):
        from agents.po_to_so_agent.agent import POtoSOAgent
        return POtoSOAgent(erp_base="http://mock:8001")

    def _po_resp(self):
        return mock_response(200, {
            "po_id": "PO-001", "customer_id": "CUST-001",
            "status": "pending",
        })

    def test_get_items(self):
        agent = self._make_agent()
        with patch('requests.get') as mock_get:
            mock_get.return_value = mock_response(200, [
                {"item_code": "CPU-001"}, {"item_code": "MEM-001"},
            ])
            items = agent.get_items()
        assert len(items) == 2

    def test_get_po(self):
        agent = self._make_agent()
        with patch('requests.get') as mock_get:
            mock_get.side_effect = [
                self._po_resp(),
                mock_response(200, [{"item_code": "CPU-001", "qty": 10, "unit_price": 100.0,
                                     "delivery_date": "2026-06-01", "line_no": 1}]),
            ]
            po = agent.get_po("PO-001")
        assert po["po_id"] == "PO-001"
        assert len(po["lines"]) == 1

    def test_validate_items(self):
        agent = self._make_agent()
        with patch('requests.get') as mock_get:
            mock_get.return_value = mock_response(200, [
                {"item_code": "CPU-001"}, {"item_code": "MEM-001"},
            ])
            valid, invalid = agent.validate_items(["CPU-001", "BOGUS"])
        assert valid == ["CPU-001"]
        assert invalid == ["BOGUS"]

    def test_validate_items_all_invalid(self):
        agent = self._make_agent()
        with patch('requests.get') as mock_get:
            mock_get.return_value = mock_response(200, [])
            valid, invalid = agent.validate_items(["BOGUS1", "BOGUS2"])
        assert valid == []
        assert len(invalid) == 2

    def test_convert_po_to_so_success(self):
        agent = self._make_agent()
        with patch('requests.get') as mock_get, patch('requests.post') as mock_post:
            mock_get.side_effect = [
                # get_po
                self._po_resp(),
                # get_po_lines
                mock_response(200, [
                    {"item_code": "CPU-001", "qty": 10, "unit_price": 100.0,
                     "delivery_date": "2026-06-01", "line_no": 1},
                ]),
                # get_items for validate
                mock_response(200, [{"item_code": "CPU-001"}]),
            ]
            mock_post.return_value = mock_response(200, {
                "so_id": "SO-2026-001", "status": "draft",
            })
            result = agent.convert_po_to_so("PO-001", so_id="SO-2026-001")
        assert result["event"] == "so_created"
        assert result["so_id"] == "SO-2026-001"
        assert result["total_amount"] == 1000.0

    def test_convert_po_to_so_with_contract_prices(self):
        agent = self._make_agent()
        with patch('requests.get') as mock_get, patch('requests.post') as mock_post:
            mock_get.side_effect = [
                self._po_resp(),
                mock_response(200, [
                    {"item_code": "CPU-001", "qty": 5, "unit_price": 200.0,
                     "delivery_date": "2026-06-01", "line_no": 1},
                ]),
                mock_response(200, [{"item_code": "CPU-001"}]),
            ]
            mock_post.return_value = mock_response(200, {
                "so_id": "SO-001", "status": "draft",
            })
            result = agent.convert_po_to_so("PO-001", so_id="SO-001",
                                            contract_prices={"CPU-001": 150.0})
        # contract_price 150 * qty 5 = 750
        assert result["total_amount"] == 750.0

    def test_convert_po_to_so_invalid_items(self):
        agent = self._make_agent()
        with patch('requests.get') as mock_get:
            mock_get.side_effect = [
                self._po_resp(),
                mock_response(200, [
                    {"item_code": "BOGUS", "qty": 10, "unit_price": 100.0,
                     "delivery_date": "2026-06-01", "line_no": 1},
                ]),
                mock_response(200, []),  # no items in ERP
            ]
            result = agent.convert_po_to_so("PO-001")
        assert result["event"] == "so_creation_blocked"
        assert "BOGUS" in result["invalid_items"]

    def test_convert_po_to_so_error(self):
        agent = self._make_agent()
        with patch('requests.get') as mock_get:
            mock_get.return_value = mock_http_error(404, "PO 不存在")
            result = agent.convert_po_to_so("PO-FAKE")
        assert result["event"] == "po_to_so_error"

    def test_get_so(self):
        agent = self._make_agent()
        with patch('requests.get') as mock_get:
            mock_get.side_effect = [
                mock_response(200, {"so_id": "SO-001", "status": "confirmed"}),
                mock_response(200, [{"line_no": 1, "item_code": "CPU-001"}]),
            ]
            so = agent.get_so("SO-001")
        assert so["so_id"] == "SO-001"
        assert len(so["lines"]) == 1

    def test_update_so_status(self):
        agent = self._make_agent()
        with patch('requests.patch') as mock_patch:
            mock_patch.return_value = mock_response(200, {
                "so_id": "SO-001", "status": "confirmed",
            })
            result = agent.update_so_status("SO-001", "confirmed", "OK")
        assert result["status"] == "confirmed"

    def test_validate_items_http_error(self):
        agent = self._make_agent()
        with patch('requests.get') as mock_get:
            mock_get.return_value = mock_http_error(500, "Server error")
            valid, invalid = agent.validate_items(["CPU-001"])
        assert valid == []
        assert invalid == ["CPU-001"]

    def test_convert_po_already_converted(self):
        agent = self._make_agent()
        with patch('requests.get') as mock_get:
            mock_get.return_value = mock_response(200, {
                "po_id": "PO-001", "customer_id": "CUST-001",
                "status": "converted",
            })
            result = agent.convert_po_to_so("PO-001")
        assert result["event"] == "po_to_so_error"
        assert "已轉換" in result["remarks"]

    def test_convert_po_so_create_error(self):
        agent = self._make_agent()
        with patch('requests.get') as mock_get, patch('requests.post') as mock_post:
            mock_get.side_effect = [
                self._po_resp(),
                mock_response(200, [
                    {"item_code": "CPU-001", "qty": 10, "unit_price": 100.0,
                     "delivery_date": "2026-06-01", "line_no": 1},
                ]),
                mock_response(200, [{"item_code": "CPU-001"}]),
            ]
            mock_post.return_value = mock_http_error(500, "DB Error")
            result = agent.convert_po_to_so("PO-001")
        assert result["event"] == "po_to_so_error"

    def test_convert_po_no_contract_price(self):
        """Contract price dict does not contain the item — should use unit_price"""
        agent = self._make_agent()
        with patch('requests.get') as mock_get, patch('requests.post') as mock_post:
            mock_get.side_effect = [
                self._po_resp(),
                mock_response(200, [
                    {"item_code": "CPU-001", "qty": 5, "unit_price": 200.0,
                     "delivery_date": "2026-06-01", "line_no": 1},
                ]),
                mock_response(200, [{"item_code": "CPU-001"}]),
            ]
            mock_post.return_value = mock_response(200, {
                "so_id": "SO-001", "status": "draft",
            })
            result = agent.convert_po_to_so("PO-001", contract_prices={"OTHER": 150.0})
        # contract doesn't have CPU-001, so unit_price 200 * qty 5 = 1000
        assert result["total_amount"] == 1000.0

    def test_demo_po_to_so(self):
        from agents.po_to_so_agent.agent import POtoSOAgent, demo
        agent = POtoSOAgent(erp_base="http://mock:8001")
        with patch('requests.get') as mock_get, patch('requests.post') as mock_post:
            mock_get.side_effect = [
                # get_po
                mock_response(200, {"po_id": "E2E-PO-001", "customer_id": "CUST", "status": "pending"}),
                # get_po_lines
                mock_response(200, [{"item_code": "SKU-001", "qty": 10, "unit_price": 50.0,
                                     "delivery_date": "2026-06-15", "line_no": 1}]),
                # get_items for validate
                mock_response(200, [{"item_code": "SKU-001"}]),
            ]
            mock_post.return_value = mock_response(200, {
                "so_id": "E2E-SO-001", "status": "draft",
                "lines": [{"item_code": "SKU-001", "qty": 10}],
            })
            results = demo(agent)
        assert len(results) == 1
        assert results[0]["event"] == "so_created"

    def test_main_po_to_so(self):
        from agents.po_to_so_agent import agent as mod
        with patch.object(mod, 'demo') as mock_demo:
            with patch('sys.argv', ['agent.py']):
                mod.main()
            mock_demo.assert_called_once()

    def test_main_po_demo_flag(self):
        from agents.po_to_so_agent import agent as mod
        with patch.object(mod, 'demo') as mock_demo:
            with patch('sys.argv', ['agent.py', '--demo']):
                mod.main()
            mock_demo.assert_called_once()

    def test_interactive_po_exit(self):
        from agents.po_to_so_agent.agent import POtoSOAgent, interactive
        agent = POtoSOAgent(erp_base="http://mock:8001")
        with patch('builtins.input', side_effect=["exit"]):
            interactive(agent)

    def test_interactive_po_eof(self):
        from agents.po_to_so_agent.agent import POtoSOAgent, interactive
        agent = POtoSOAgent(erp_base="http://mock:8001")
        with patch('builtins.input', side_effect=EOFError):
            interactive(agent)

    def test_interactive_po_empty(self):
        from agents.po_to_so_agent.agent import POtoSOAgent, interactive
        agent = POtoSOAgent(erp_base="http://mock:8001")
        with patch('builtins.input', side_effect=["", "exit"]):
            interactive(agent)

    def test_interactive_po_convert(self):
        from agents.po_to_so_agent.agent import POtoSOAgent, interactive
        agent = POtoSOAgent(erp_base="http://mock:8001")
        with patch('builtins.input', side_effect=["convert PO-001 SO-001", "exit"]), \
             patch('requests.get') as mock_get, patch('requests.post') as mock_post:
            mock_get.side_effect = [
                mock_response(200, {"po_id": "PO-001", "customer_id": "CUST", "status": "pending"}),
                mock_response(200, [{"item_code": "CPU-001", "qty": 10, "unit_price": 100.0,
                                     "delivery_date": "2026-06-15", "line_no": 1}]),
                mock_response(200, [{"item_code": "CPU-001"}]),
            ]
            mock_post.return_value = mock_response(200, {"so_id": "SO-001", "status": "draft"})
            interactive(agent)

    def test_interactive_po_query(self):
        from agents.po_to_so_agent.agent import POtoSOAgent, interactive
        agent = POtoSOAgent(erp_base="http://mock:8001")
        with patch('builtins.input', side_effect=["query SO-001", "exit"]), \
             patch('requests.get') as mock_get:
            mock_get.side_effect = [
                mock_response(200, {"so_id": "SO-001", "status": "draft"}),
                mock_response(200, [{"line_no": 1}]),
            ]
            interactive(agent)

    def test_interactive_po_status(self):
        from agents.po_to_so_agent.agent import POtoSOAgent, interactive
        agent = POtoSOAgent(erp_base="http://mock:8001")
        with patch('builtins.input', side_effect=["status SO-001 confirmed", "exit"]), \
             patch('requests.patch') as mock_patch:
            mock_patch.return_value = mock_response(200, {"so_id": "SO-001", "status": "confirmed"})
            interactive(agent)

    def test_interactive_po_unknown(self):
        from agents.po_to_so_agent.agent import POtoSOAgent, interactive
        agent = POtoSOAgent(erp_base="http://mock:8001")
        with patch('builtins.input', side_effect=["bogus", "exit"]):
            interactive(agent)

    def test_convert_with_auto_so_id(self):
        """No so_id provided, auto-generated one should be used"""
        agent = self._make_agent()
        po_resp = mock_response(200, {
            "po_id": "PO-20260524-ABC", "customer_id": "CUST-001",
            "status": "pending",
        })
        with patch('requests.get') as mock_get, patch('requests.post') as mock_post:
            mock_get.side_effect = [
                po_resp,
                mock_response(200, [{"item_code": "CPU-001", "qty": 5, "unit_price": 100.0,
                                     "delivery_date": "2026-06-01", "line_no": 1}]),
                mock_response(200, [{"item_code": "CPU-001"}]),
            ]
            mock_post.return_value = mock_response(200, {
                "so_id": "SO-AUTO", "status": "draft",
            })
            result = agent.convert_po_to_so("PO-20260524-ABC")
        # the mock returns SO-AUTO but agent also sets so_id if missing
        assert result["event"] == "so_created"
        assert result["total_amount"] == 500.0
