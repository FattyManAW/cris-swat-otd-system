# OTD 模擬工廠系統 — 操作說明與案例導覽

## 目錄
1. [系統簡介](#1-系統簡介)
2. [啟動步驟](#2-啟動步驟)
3. [完整操作案例](#3-完整操作案例)
4. [API 操作範例](#4-api-操作範例)
5. [OTD Agent 說明](#5-otd-agent-說明)

---

## 1. 系統簡介

OTD（Order-to-Delivery）模擬工廠系統是一套完整的接單到出貨流程可視化系統，涵蓋以下階段：

```
詢單 → ATP/CTP 試算 → PO 接收 → SO 建立 → 生產追蹤 → ASN 發出 → Pick/Pack/Ship → Invoice → Logistics → 到貨
```

### 系統組成

| 組件 | 說明 |
|------|------|
| **ERP 模擬層** | FastAPI + SQLite，提供 30+ API 端點 |
| **OTD Agent 群** | 5 個 Agent 驅動各流程階段 |
| **視覺設計** | 流程圖、色彩系統、儀表板規範 |

### 預設數據

系統內建 3 個客戶和 5 個料號：

**客戶：**
| 客戶ID | 名稱 | 付款條件 |
|--------|------|----------|
| CUST-001 | ACME Corp | Net30 |
| CUST-002 | Globex Inc | Net60 |
| CUST-003 | Initech | Net30 |

**料號：**
| 料號 | 描述 | 單位 | 前置時間 | 日產能 |
|------|------|------|----------|--------|
| SKU-001 | 電子零件 A型 | PC | 7天 | 2,000 |
| SKU-002 | 電子零件 B型 | PC | 10天 | 1,500 |
| SKU-003 | 外殼組件 | SET | 14天 | 500 |
| SKU-004 | 包裝材料 | PKG | 3天 | 5,000 |
| SKU-005 | 軟體授權 | LIC | 1天 | 99,999 |

---

## 2. 啟動步驟

### Step 1：安裝依賴

```bash
cd erp_sim
pip install -r requirements.txt
```

### Step 2：啟動 ERP 模擬層

```bash
python main.py
```

ERP 模擬層將在 `http://localhost:8001` 運行。

### Step 3：驗證服務

```bash
curl http://localhost:8001/healthz
```

回傳：`{"ok":true,"message":"OTD ERP Simulator is running"}` ✅

### Step 4：瀏覽 API 文件

打開 http://localhost:8001/docs 可以看到所有 API 端點的互動文件。

---

## 3. 完整操作案例

本案例示範一個完整 OTD 流程：**ACME Corp 訂購電子零件 A型 3,000 個**。

### Step 1：查詢可用料號

```bash
curl http://localhost:8001/api/v1/items
```

查看所有料號資訊，選擇需要的料號。

### Step 2：查詢客戶資料

```bash
curl http://localhost:8001/api/v1/customers
```

查看客戶付款條件和聯絡方式。

### Step 3：建立詢價單（Inquiry）

客戶 ACME Corp 詢價購買 SKU-001 電子零件 A型 3,000 個。

### Step 4：ATP/CTP 交期試算

**ATP（Available-to-Promise）** — 確認料號庫存和可承諾數量：

```bash
curl -X POST http://localhost:8001/api/v1/atp/check \
  -H "Content-Type: application/json" \
  -d '{"item_code": "SKU-001", "quantity": 3000, "request_date": "2026-05-20"}'
```

**CTP（Capable-to-Promise）** — 確認產能能否在指定交期前完成：

```bash
curl -X POST http://localhost:8001/api/v1/ctp/check \
  -H "Content-Type: application/json" \
  -d '{"item_code": "SKU-001", "quantity": 3000, "required_date": "2026-06-01"}'
```

### Step 5：接收 PO

ATP/CTP 通過後，接收客戶正式訂單：

```bash
curl -X POST http://localhost:8001/api/v1/po \
  -H "Content-Type: application/json" \
  -d '{
    "po_id": "PO-20260518-001",
    "customer_id": "CUST-001",
    "order_date": "2026-05-18",
    "requested_delivery": "2026-06-01",
    "lines": [
      {"item_code": "SKU-001", "quantity": 3000, "unit_price": 150}
    ]
  }'
```

### Step 6：PO 轉 SO

PO 審核通過後，轉換為銷貨單：

```bash
curl -X POST "http://localhost:8001/api/v1/po/PO-20260518-001/convert"
```

### Step 7：查詢 SO

```bash
curl http://localhost:8001/api/v1/so/SO-20260518-001
```

### Step 8：更新 SO 狀態（生產進行中）

```bash
curl -X PATCH "http://localhost:8001/api/v1/so/SO-20260518-001" \
  -H "Content-Type: application/json" \
  -d '{"status": "in_production"}'
```

### Step 9：建立 ASN（出貨通知）

```bash
curl -X POST http://localhost:8001/api/v1/shipping/create \
  -H "Content-Type: application/json" \
  -d '{
    "so_id": "SO-20260518-001",
    "carrier": "DHL",
    "estimated_arrival": "2026-06-03"
  }'
```

### Step 10：Pack（包裝出貨）

```bash
curl -X PATCH "http://localhost:8001/api/v1/shipping/SHP-{id}/pack"
```

### Step 11：Ship（出貨）

```bash
curl -X PATCH "http://localhost:8001/api/v1/shipping/SHP-{id}/ship"
```

### Step 12：建立 Invoice

```bash
curl -X POST http://localhost:8001/api/v1/invoice/create \
  -H "Content-Type: application/json" \
  -d '{"so_id": "SO-20260518-001", "total_amount": 450000}'
```

### Step 13：安排物流

```bash
curl -X POST http://localhost:8001/api/v1/logistics/arrange \
  -H "Content-Type: application/json" \
  -d '{"shipping_id": "SHP-{id}", "warehouse": "TW-TPE", "destination": "US-LAX"}'
```

### Step 14：確認到貨

```bash
curl -X POST "http://localhost:8001/api/v1/logistics/TRK-{id}/arrive"
```

### ✅ 完整流程結束！

從詢單到到貨，OTD 流程全部完成。

---

## 4. API 操作範例

### 4-1 料號管理

```bash
# 列出所有料號
GET /api/v1/items

# 查詢單一料號
GET /api/v1/items/SKU-001

# 新增料號
POST /api/v1/items
{"item_code": "SKU-006", "description": "新料號", "unit": "PC", "category": "electronics", "lead_time_days": 5, "safety_stock": 100, "daily_capacity": 1000}
```

### 4-2 客戶管理

```bash
# 列出所有客戶
GET /api/v1/customers

# 查詢單一客戶
GET /api/v1/customers/CUST-001

# 新增客戶
POST /api/v1/customers
{"customer_id": "CUST-004", "name": "新客戶", "terms": "Net30", "contact_email": "contact@new.com"}
```

### 4-3 PO 管理

```bash
# 列出所有 PO
GET /api/v1/po

# 查詢單一 PO
GET /api/v1/po/PO-20260518-001

# 查詢 PO 明細
GET /api/v1/po/PO-20260518-001/lines
```

### 4-4 SO 管理

```bash
# 列出所有 SO
GET /api/v1/so

# 查詢單一 SO
GET /api/v1/so/SO-20260518-001

# 更新 SO
PATCH /api/v1/so/SO-20260518-001
{"status": "in_production"}
```

### 4-5 出貨管理

```bash
# 建立出貨單
POST /api/v1/shipping/create
{"so_id": "SO-20260518-001", "carrier": "DHL", "estimated_arrival": "2026-06-03"}

# 查詢出貨單
GET /api/v1/shipping/SHP-{id}

# 包裝
PATCH /api/v1/shipping/SHP-{id}/pack

# 出貨
PATCH /api/v1/shipping/SHP-{id}/ship
```

### 4-6 Invoice 管理

```bash
# 建立發票
POST /api/v1/invoice/create
{"so_id": "SO-20260518-001", "total_amount": 450000}

# 查詢發票
GET /api/v1/invoice/INV-{id}
```

### 4-7 Logistics 管理

```bash
# 安排物流
POST /api/v1/logistics/arrange
{"shipping_id": "SHP-{id}", "warehouse": "TW-TPE", "destination": "US-LAX"}

# 查詢物流
GET /api/v1/logistics/TRK-{id}

# 確認到貨
POST /api/v1/logistics/TRK-{id}/arrive
```

---

## 5. OTD Agent 說明

| Agent | 職責 | 觸發條件 |
|-------|------|----------|
| **CS Agent** | 客服流程（詢單回覆、ASN 通知、出貨通知、Invoice 通知） | 新詢單 / 出貨完成 |
| **ATP/CTP Agent** | 交期試算（庫存檢查 + 產能檢查） | 收到詢單 |
| **PO-to-SO Agent** | PO 審核通過後轉換為 SO | PO 審核完成 |
| **Logistics Agent** | 物流處理（報關、出貨、到貨確認） | SO 建立 / 出貨完成 |
| **After Service Agent** | 售後服務（客戶反饋、案件追蹤） | 到貨完成 / 客戶回饋 |

---

## 快速參考

| 動作 | API |
|------|-----|
| 啟動 ERP | `cd erp_sim && python main.py` |
| 驗證服務 | `curl http://localhost:8001/healthz` |
| API 文件 | http://localhost:8001/docs |
| 詢價試算 | `POST /api/v1/atp/check` |
| 產能試算 | `POST /api/v1/ctp/check` |
| 建立 PO | `POST /api/v1/po` |
| PO 轉 SO | `POST /api/v1/po/{id}/convert` |
| 出貨通知 | `POST /api/v1/shipping/create` |
| 包裝出貨 | `PATCH /api/v1/shipping/{id}/pack` + `ship` |
| 建立發票 | `POST /api/v1/invoice/create` |
| 安排物流 | `POST /api/v1/logistics/arrange` |
| 確認到貨 | `POST /api/v1/logistics/{id}/arrive` |
