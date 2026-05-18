# OTD 整體系統架構設計

_文件版本：v1.0 | 建立日期：2026-05-18 | 作者：Vesper | 狀態：草稿_

---

## 1. 架構設計原則

| 原則 | 說明 |
|------|------|
| **事件驅動** | 每個流程節點以 Event 為驅動，前一步完成觸發下一步 |
| **Agent 串接** | OpenClaw Agent 作為流程驅動核心，每個角色由一個 Agent 承擔 |
| **ERP 模擬層** | ERP 操作經由模擬層介接，不直接修改後端實體系統 |
| **Webhook 入口** | 所有外部輸入（mail、Line、B2B）統一經 Webhook 入口進入 |
| **可視化優先** | 前端可視化面板同步展示所有事件與狀態 |

---

## 2. 系統分層架構

```
┌─────────────────────────────────────────────────────────────┐
│                     可視化層 (Visualization Layer)            │
│         流程面板 / 狀態追蹤 / 異常警示 / 報表               │
├─────────────────────────────────────────────────────────────┤
│                   API 網關層 (API Gateway)                   │
│         REST API + Webhook + SSE / WebSocket 推送           │
├──────────┬──────────┬──────────┬──────────┬─────────────────┤
│  Customer│  ATP/CTP │  PO-to-SO│ Customer │   After Service │
│  Service │  Agent   │  Agent   │ Service  │      Agent      │
│   Agent  │          │          │  Agent   │                 │
│  (介面A) │  (介面B) │  (介面C) │  (介面D) │   (介面E)        │
├──────────┴──────────┴──────────┴──────────┴─────────────────┤
│               ERP 模擬層 (ERP Simulation Layer)              │
│    PO / SO / ATP / CTP / Pick-Pack-Ship / Invoice           │
├─────────────────────────────────────────────────────────────┤
│              事件總線 (Event Bus / State Store)              │
│        訂單狀態機 + 事件佇列 + 流程持久化                    │
└─────────────────────────────────────────────────────────────┘
         ↑ Webhook              ↑ Webhook              ↑
    客戶/業務觸發            ERP 回呼通知           異常告警觸發
```

---

## 3. 事件驅動流程（OTD 事件串）

### 3.1 事件定義

| 事件名稱 | 觸發條件 | 負責 Agent | 下一步事件 |
|----------|----------|------------|------------|
| `inquiry_received` | 客戶詢單進來（mail/Line/B2B） | Customer Service Agent | → `inquiry_replied` |
| `po_received` | 客戶寄送正式 PO | Customer Service Agent | → `po_processing` |
| `po_processing` | PO 內容解析確認 | PO-to-SO Agent | → `so_created` |
| `so_created` | ERP SO 建立完成 | Customer Service Agent | → `so_monitoring` |
| `so_monitoring` | 生產/採購進度更新 | Customer Service Agent | → `asn_issued` |
| `asn_issued` | ASN 預出貨通知發出 | Customer Service Agent | → `shipping` |
| `shipping` | Pick/Pack/Ship 作業完成 | Customer Service Agent | → `invoice_sent` |
| `invoice_sent` | Invoice & Shipping 文件寄出 | — | → `order_closed` |
| `customer_voice` | 客戶反饋 / 異常通報 | After Service Agent | → `ticket_handled` |

### 3.2 ATP/CTP 交期試算流程

```
詢單收到 (inquiry_received)
       │
       ▼
ATP/CTP Agent ──► ERP 模擬層 (查詢庫存/產能)
       │
       ▼
交期回覆 → 觸發 inquiry_replied → 回到 CS Agent 主流程
```

---

## 4. Agent 角色與責任矩陣

| Agent | 角色 | 主要介接 | 輸出事件 |
|-------|------|----------|----------|
| **Customer Service Agent** | 詢單接收、進度追蹤、出貨通知、報關聯繫 | Webhook + ERP 模擬層 | inquiry_replied, so_monitoring, asn_issued, shipping, invoice_sent |
| **ATP/CTP Agent** | 交期試算、核貨回覆 | ERP 模擬層 (ATP/CTP 介面) | atp_result, ctp_result |
| **PO-to-SO Agent** | PO→SO 轉換、料號對照、ERP 單頭單身建立 | ERP 模擬層 (PO/SO 介面) | so_created |
| **Logistics Agent** | 報關文件、出貨安排、到貨確認 | ERP 模擬層 (物流介面) | shipping, delivery_confirmed |
| **After Service Agent** | 客戶聲音處理、售後追蹤 | Webhook + ERP 模擬層 | ticket_handled |

---

## 5. Webhook 觸發機制

### 5.1 入口 Webhook

| 入口 | 來源 | 處理 |
|------|------|------|
| `POST /webhook/inquiry` | mail parser / Line Bot / B2B 平台 | → inquiry_received 事件 |
| `POST /webhook/po` | mail parser / B2B 平台 | → po_received 事件 |
| `POST /webhook/customer-voice` | mail / 客服系統 | → customer_voice 事件 |
| `POST /webhook/erp-callback` | ERP 模擬層回呼 | 狀態同步事件 |

### 5.2 Webhook Payload 範本

```json
{
  "event": "po_received",
  "order_ref": "PO-2026-005",
  "customer": "ACME Corp",
  "items": [
    { "item_code": "SKU-001", "qty": 100, "delivery_date": "2026-06-15" }
  ],
  "received_at": "2026-05-18T10:30:00+08:00",
  "source": "email"
}
```

---

## 6. ERP 模擬層設計

### 6.1 介面清單

| 模組 | 功能 | 模擬方式 |
|------|------|----------|
| **PO 介面** | PO 接收、內容解析 | 檔案上傳 / Webhook payload |
| **SO 介面** | SO 單頭單身建立、料號對照 | REST API + 本地狀態庫 |
| **ATP 介面** | 可承諾量查詢 | 模擬數據（預留實體介接擴充） |
| **CTP 介面** | 可交付能力試算 | 模擬數據（預留實體介接擴充） |
| **Pick/Pack/Ship** | 出貨文書作業 | REST API + 狀態機 |
| **Invoice** | 發票文件產出 | 文件模板 + PDF 生成 |
| **Logistics** | 報關、貨櫃、到貨 | REST API + 狀態追蹤 |

### 6.2 狀態機（Order State Machine）

```
詢單 → 報價確認 → PO收到 → SO建立 → 生產/採購 → 出貨準備 → 出貨 → 發票 → 完成
                            │                             │
                            ▼                             ▼
                        ATP/CTP試算               Pick/Pack/Ship
```

---

## 7. Agent 串接機制

### 7.1 串接模式

```
Webhook 入口
    │
    ▼
Customer Service Agent (Router)
    │
    ├── 詢單回覆 ──→ ATP/CTP Agent ──→ CS Agent 主流程繼續
    │
    ├── PO 轉 SO ──→ PO-to-SO Agent ──→ CS Agent 監控
    │
    ├── 出貨通知 ──→ Logistics Agent ──→ CS Agent 跟催
    │
    └── 異常/回饋 ──→ After Service Agent ──→ CS Agent 結案
```

### 7.2 協作要點

- **OpenClaw Task System** 作為 Agent 間任務分派機制
- **Board Memory** 作為共享狀態儲存（訂單狀態、進度記錄）
- **Task Comment** 作為 Agent 間協作通訊
- **Cron Job** 作為週期性追蹤（SO 進度巡檢、ASN 到時提醒）

---

## 8. 可視化面板對應

| 可視化元素 | 資料來源 | 更新機制 |
|-----------|----------|----------|
| 訂單流程圖（Funnel） | Event Bus 狀態機 | SSE 即時推送 |
| 各步驟狀態 | Agent Task System | SSE 即時推送 |
| Agent 處理進度 | Task Comment 活動 | 輪詢 / 推送 |
| 異常警示 | Customer Voice 事件 | Webhook + SSE |
| ATP/CTP 試算結果 | ATP/CTP Agent | REST API |
| 物流追蹤 | Logistics Agent | REST API |

---

## 9. 文件對應關係

| 架構元件 | 對應任務 | 關係 |
|----------|----------|------|
| 本文件 | ba1f7b20（本任務） | 上游依據 |
| ERP 模擬層 | 0901a7c8 | 下游依賴本文件介面設計 |
| Agent 角色設計 | 各 Agent 任務 | 下游依賴本文件 Agent 設計 |
| 可視化面板 | fc9910bf | 下游依賴本文件 API 設計 |
| 端對端整合測試 | 0323532c | 下游驗證依據 |
| 主任務（fa273118） | fa273118 | 本文件為其架構基礎 |

---

## 10. 風險與開放事項

| 風險 | 緩解措施 |
|------|----------|
| Agent 串接順序錯誤導致流程中斷 | 以狀態機保證單向前進，每一步驗證後才觸發下一步 |
| ERP 模擬層與實際系統差異 | 模擬層介面定義即時與實體 ERP 相容，後續只需替換實作 |
| Webhook 來源不可信 | 加入簽章驗證（HMAC），目前先以內部測試為主 |
| 並發訂單處理 | 每個 order_ref 為獨立流程實例，互不干擾 |

---

## 11. 下一步建議

1. **ERP 介接模擬層**（0901a7c8）— 優先開發，是所有 Agent 的資料基礎
2. **Event Bus / 狀態機實作** — 配合 ERP 模擬層同步開發
3. **各 Agent 依角色分工** — 依照本文件 Section 4 矩陣逐一建立
4. **可視化面板**（fc9910bf）— Agent 串接完成後可同步進行

---

_本文件為 OTD 系統架構第一版設計，後續隨開發進度持續更新。_
