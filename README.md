# OTD 模擬工廠系統 - 部署包

完整模擬工廠接單到出貨（OTD）流程的可視化系統，以 OpenClaw Agent 群為事件驅動核心。

## 快速啟動

### 1. 啟動 ERP 模擬層
```bash
cd erp_sim
pip install -r requirements.txt
python main.py
```
ERP 模擬層將在 http://localhost:8001 運行

### 2. 驗證 ERP 模擬層
```bash
curl http://localhost:8001/healthz
```

### 3. Agent 實現
所有 Agent 的 SOUL.md + agent.py 位於 `agents/` 目錄：

| Agent | 職責 |
|---|---|
| atp_ctp_agent | ATP/CTP 交期試算 |
| customer_service_agent | 客服流程（詢單/ASN/出貨通知/Invoice）|
| po_to_so_agent | PO 轉 SO |
| logistics_agent | 物流處理（報關/出貨/到貨）|
| after_service_agent | 售後服務（客戶反饋/案件追蹤）|

## OTD 完整流程

詢單 → ATP/CTP 試算 → PO 接收 → SO 建立 → 生產追蹤 → ASN 發出 → Pick/Pack/Ship → Invoice → Logistics → 售後

## 架構

- **ERP 模擬層**：`erp_sim/` — FastAPI + SQLite
- **OTD Agent 群**：`agents/` — 5 個 Agent（SOUL + Python 實現）
- **設計文件**：`docs/` — 視覺設計 + 架構設計

## 開發者

CRIS SWAT AI Team — Luna (lead), Vesper (架構), Vision (設計), Forge (開發)

## License

Internal use — CRIS SWAT Project
