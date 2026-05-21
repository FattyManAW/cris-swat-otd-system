# Deploy Checklist — OTD ERP 模擬層

_建立日期：2026-05-21 | 作者：Vesper | 狀態：實戰驗證_

每次 `docker compose up -d --build` 前，逐項確認。

---

## Phase 0 — 部署前（Code）

- [ ] **Code changes committed** — `git status` 乾淨
- [ ] **Dockerfile `COPY` 含所有子目錄** — 若加了新檔案/目錄，確認 Dockerfile `COPY` 語句涵蓋
  - ❌ `COPY *.py ./` → 只複製根目錄，漏掉 `erp_sim/` 等子目錄
  - ✅ `COPY . ./` → 複製全部
- [ ] **Code endpoint 改了 → compose HEALTHCHECK path 同步** — 若改了 `main.py` 的 health endpoint，同步更新 `docker-compose.yml` 的 HEALTHCHECK `test` 路徑
  - 例子：`/health` → `/healthz`，compose 也要改
- [ ] **Health endpoint 用 127.0.0.1 不用 localhost** — Docker 容器內部 localhost 偶爾 DNS 逾時
  - ✅ `http://127.0.0.1:8004/healthz`
  - ❌ `http://localhost:8004/health`

---

## Phase 1 — Build 前

- [ ] **`GIT_COMMIT` env 有值** — Dockerfile `ARG GIT_COMMIT` 需要 build-time env
  ```bash
  export GIT_COMMIT=$(git rev-parse --short HEAD)
  ```
  - ❌ 沒帶 env → commit=unknown
  - ✅ `export GIT_COMMIT=<hash> && docker compose up -d --build`

---

## Phase 2 — Build & Deploy

- [ ] **Build with env** — `export GIT_COMMIT=<hash> && docker compose up -d --build`
- [ ] **npm build 後 chmod**（前端） — `chmod -R 755 frontend/dist/`
  - ❌ npm build 產出 600 perms → nginx worker 無法讀取 → 403
- [ ] **等待容器啟動** — `docker ps` 確認 `(healthy)` 或至少 `(healthy)` status
- [ ] **若有 nginx，等待 frontend dist** — nginx container 需要在 volume mount 後有檔案可讀

---

## Phase 3 — Verify（部署後）

- [ ] **容器狀態 healthy** — `docker ps | grep healthy`
- [ ] **`/healthz` → 200** — `curl -sS -o /dev/null -w "%{http_code}" http://localhost:8004/healthz`
- [ ] **8 routes 全 200** — 最少 smoke test：
  | Endpoint | Method | 預期 |
  |----------|--------|------|
  | `/healthz` | GET | 200 |
  | `/` | GET | 200 |
  | `/api/v1/items` | GET | 200 |
  | `/api/v1/atp/check` | POST | 200 |
  | `/api/v1/shipping/create` | POST | 200（正確的驗證錯誤） |
  | `/api/v1/invoice/create` | POST | 200（正確的驗證錯誤） |
  | `/api/v1/logistics/arrange` | POST | 200（正確的驗證錯誤） |
  | `/api/v1/po` | GET | 200 |
- [ ] **`erp_sim/` 檔案在容器內** — `docker exec otd-api ls /app/erp_sim/`（確認 `COPY` 沒漏）
- [ ] **Seed data 載入** — `GET /api/v1/items` 應回傳 seed data（100 items）

---

## Phase 4 — Commit Parity 確認

- [ ] **GIT_COMMIT 比對**：
  ```bash
  # Container 內
  docker exec otd-api cat /app/GIT_COMMIT
  # Repo
  git -C /path/to/otd-docker rev-parse --short HEAD
  ```
  - ✅ 兩者相同 → commit parity 綠燈
  - ❌ 不同 → container 落後，需要 rebuild

---

## 已知問題歷史（血淚教訓）

| 日期 | 問題 | 根因 | 修復 |
|------|------|------|------|
| 2026-05-20 | commit=unknown | `GIT_COMMIT` env 沒帶 | `export GIT_COMMIT=<hash> && docker compose up -d --build` |
| 2026-05-20 | nginx 403 | npm build 權限 600 | `chmod -R 755 frontend/dist/` |
| 2026-05-21 | erp_sim/ 漏裝 | Dockerfile `COPY *.py ./` 不含子目錄 | 改 `COPY . ./` |
| 2026-05-21 | container unhealthy | HEALTHCHECK 打 `/health` 但 endpoint 是 `/healthz` | compose path 同步 |
| 2026-05-21 | localhost DNS 逾時 | Docker 內部 localhost 偶爾解析失敗 | 永遠用 127.0.0.1 |

---

_本文檔為 OTD 部署實戰經驗累積，持續更新。_
