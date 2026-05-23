# OTD ERP 模擬層設計

_文件版本：v1.0 | 建立日期：2026-05-18 | 作者：Vesper | 狀態：草稿_

---

## 1. 設計目標

ERP 模擬層作為所有 OTD Agent 的統一資料介面，模擬真實 ERP 系統的 7 個核心模組，讓各 Agent 可以透過標準 API 進行資料讀寫，無需依賴真實 ERP 後端。

- **介面相容性**：介面定義即時與實體 ERP 相容，後續只需替換實作
- **狀態持久化**：以 SQLite 儲存所有訂單、料號、庫存等核心資料
- **可模擬異常**：內建資料異常模擬機制，供整合測試使用
- **簡單部署**：單一 Python 程序，零外部依賴（FastAPI + SQLite）

---

## 2. 模組架構

```
otd_erp_sim/
├── main.py                 # FastAPI 程式入口
├── models.py               # SQLAlchemy 資料模型
├── schemas.py              # Pydantic 請求和回應 Schema
├── seed_data.py            # 預設測試資料
├── requirements.txt        # 套件清單
└── README.md               # 使用說明
```

---

## 3. 介面規格

### 3.1 料號對照（Item Mapping）

```http
GET    /api/v1/items                    # 查詢料號清單
GET    /api/v1/items/{item_code}        # 查詢單一料號
POST   /api/v1/items                    # 建立料號
PUT    /api/v1/items/{item_code}        # 更新料號
```

### 3.2 PO 介面

```http
POST   /api/v1/po                       # 建立/接收 PO
GET    /api/v1/po                       # 查詢 PO 清單
GET    /api/v1/po/{po_id}               # 查詢單一 PO
PATCH  /api/v1/po/{po_id}               # 更新 PO 狀態
POST   /api/v1/po/{po_id}/convert       # 執行 PO→SO 轉換
```

### 3.3 SO 介面

```http
POST   /api/v1/so                       # 建立 SO
GET    /api/v1/so                       # 查詢 SO 清單
GET    /api/v1/so/{so_id}               # 查詢單一 SO
PATCH  /api/v1/so/{so_id}               # 更新 SO 狀態
GET    /api/v1/so/{so_id}/lines         # 查詢 SO 單身
```

### 3.4 ATP 介面（可承諾量）

```http
POST   /api/v1/atp/check                # ATP 交期試算
# Body: { "item_code": "SKU-001", "qty": 100, "request_date": "2026-06-15" }
```

### 3.5 CTP 介面（可交付能力）

```http
POST   /api/v1/ctp/check                # CTP 能力試算
# Body: { "item_code": "SKU-001", "qty": 100, "request_date": "2026-06-15" }
```

### 3.6 Pick/Pack/Ship 介面

```http
POST   /api/v1/shipping/create          # 建立出貨單
GET    /api/v1/shipping/{shipping_id}   # 查詢出貨單
PATCH  /api/v1/shipping/{shipping_id}/pack    # 執行包裝作業
PATCH  /api/v1/shipping/{shipping_id}/ship    # 執行出貨
```

### 3.7 Invoice 介面

```http
POST   /api/v1/invoice/create           # 建立發票
GET    /api/v1/invoice/{invoice_id}     # 查詢發票
```

### 3.8 Logistics 介面

```http
POST   /api/v1/logistics/arrange        # 安排出貨物流
GET    /api/v1/logistics/{tracking_no}  # 查詢物流狀態
POST   /api/v1/logistics/{tracking_no}/arrive  # 確認到貨
```

---

## 4. 資料模型

### 4.1 Item（料號）

```python
class Item(Base):
    item_code      # 料號（主鍵）
    description    # 品名規格
    unit           # 單位
    category       # 類別
    lead_time_days # 交期前置天數
    is_active      # 是否啟用
```

### 4.2 Customer（客戶）

```python
class Customer(Base):
    customer_id    # 客戶編號
    name           # 客戶名稱
    terms          # 交易條件
    contact_email  # 聯絡 Email
    is_active
```

### 4.3 PurchaseOrder（採購單）

```python
class PurchaseOrder(Base):
    po_id          # PO 單號
    customer_id    # 客戶
    po_date        # PO 日期
    status         # 狀態：pending / converted / cancelled
    remarks        # 備註
    lines[]        # POLine 單身
```

### 4.4 SalesOrder（銷貨單）

```python
class SalesOrder(Base):
    so_id          # SO 單號
    po_id          # 關聯 PO
    customer_id    # 客戶
    so_date        # SO 日期
    status         # 狀態：draft / confirmed / partial / completed / cancelled
    so_lines[]     # SOLine 單身
```

### 4.5 ATPCheck / CTPCheck（交期試算紀錄）

```python
class ATPCheck:
    check_id       # 紀錄 ID
    item_code      # 料號
    qty            # 數量
    request_date   # 需求日期
    available_date # 可承諾日期
    available_qty  # 可承諾數量
    result         # on_time / delayed / insufficient
```

### 4.6 Shipping（出貨單）

```python
class Shipping(Base):
    shipping_id    # 出貨單號
    so_id          # 關聯 SO
    status         # status：pending / packing / shipped / delivered
    pallet_count   # 棧板數
    container_type # 貨櫃規格
    customs_date   # 結關日
    tracking_no    # 物流追蹤號
```

### 4.7 Invoice（發票）

```python
class Invoice(Base):
    invoice_id     # 發票號碼
    shipping_id    # 關聯出貨單
    so_id          # 關聯 SO
    amount         # 金額
    issue_date     # 開立日期
    status         # draft / issued / paid
```

### 4.8 Logistics（物流追蹤）

```python
class Logistics:
    tracking_no    # 追蹤號（主鍵）
    shipping_id    # 關聯出貨單
    status         # booked / in_transit / arrived / delivered
    carrier        # 承運商
    eta            # 預估到貨日
    actual_arrival # 實際到貨
```

---

## 5. 訂單狀態機

```
PO Received ──► pending
                │
                ▼ PO→SO 轉換
SO Created  ──► draft ──► confirmed ──► partial ──► completed
                                           │
                                           ▼
                                    shipping ──► shipped ──► delivered
                                           │
                                           ▼
                                      invoice issued
```

---

## 6. 模擬策略

### 6.1 ATP 模擬規則

- 查詢料號歷史出貨量與在途量
- 可承諾量 = 安全庫存 + 在途量 - 已承諾量
- 可承諾日期 = 當前日期 + lead_time_days

### 6.2 CTP 模擬規則

- 與 ATP 相同基礎計算
- 加入產能限制假設（每日最大產量）
- 返回是否足夠及建議分批交貨

### 6.3 異常模擬

| 異常情境 | 觸發方式 |
|----------|----------|
| 庫存不足 | query param `?force_insufficient=true` |
| ATP/CTP 延遲 | query param `?force_delay=true` |
| ERP 故障 | query param `?simulate_error=true` |

---

## 7. API 認證

- 開發環境：無認證（`http://localhost:8001`）
- 預留 Header-based Token 介面
- OpenAPI 文件：`http://localhost:8001/docs`

---

## 8. 下一步

1. 實作 `models.py` + `schemas.py`
2. 實作 `main.py` 全部介面
3. 實作 `seed_data.py` 測試資料
4. 單元測試

---

_本文件為 ERP 模擬層設計第一版，後續隨開發進度更新。_
