"""Agent unit tests — mock requests layer, test agent logic for all 5 agents.

AfterServiceAgent, ATPCTPAgent, CustomerServiceAgent, LogisticsAgent, POtoSOAgent
"""

import pytest
import json
from unittest.mock import Mock, patch, PropertyMock
from datetime import datetime


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