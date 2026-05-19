#!/bin/bash
# ════════════════════════════════════════════════════════════════
#  OTD ERP 模擬層 — 一鍵啟動腳本
#  用法: ./start.sh [--logs|--stop|--status|--rebuild|--help]
# ════════════════════════════════════════════════════════════════
set -euo pipefail

GREEN='\033[0;32m'; CYAN='\033[0;36m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
API_PORT=8004; NGINX_PORT=8040

CMD="${1:-start}"
case "$CMD" in
  --help|-h)
    echo "OTD ERP 一鍵啟動: ./start.sh [--logs|--stop|--status|--rebuild|--help]"
    exit 0 ;;
  --status)
    curl -sf "http://localhost:${API_PORT}/healthz" 2>/dev/null && echo -e "${GREEN}✅ API running on :${API_PORT}${NC}" || echo -e "${RED}❌ API not running${NC}"
    curl -sf "http://localhost:${NGINX_PORT}/" 2>/dev/null && echo -e "${GREEN}✅ Dashboard on :${NGINX_PORT}${NC}" || echo -e "${RED}❌ Dashboard not running${NC}"
    exit 0 ;;
  --stop)
    docker compose down 2>/dev/null
    echo -e "${GREEN}✅ Stopped${NC}"; exit 0 ;;
esac

# ── Start ──
if ! command -v docker &>/dev/null; then echo -e "${RED}Docker required${NC}"; exit 1; fi

echo -e "${CYAN}🐳 Building & starting OTD ERP...${NC}"
docker compose down 2>/dev/null || true
[ "$CMD" = "--rebuild" ] && docker compose build --no-cache
docker compose up -d --build

echo -e "${CYAN}⏳ Waiting for health check...${NC}"
for i in $(seq 1 30); do
  if curl -sf "http://localhost:${API_PORT}/healthz" &>/dev/null; then break; fi
  sleep 2
done

echo ""
echo -e "${GREEN}═══════════════════════════════${NC}"
echo -e "${GREEN}  🎉 OTD ERP 啟動成功！${NC}"
echo -e "${GREEN}═══════════════════════════════${NC}"
echo -e "  API:          http://localhost:${API_PORT}"
echo -e "  Swagger:      http://localhost:${API_PORT}/docs"
echo -e "  Dashboard:    http://localhost:${NGINX_PORT}"
echo ""

# Verify
curl -sf "http://localhost:${API_PORT}/healthz" && echo -e "${GREEN}✅ API healthy${NC}" || echo -e "${RED}❌ API unhealthy${NC}"
curl -sf "http://localhost:${API_PORT}/api/v1/customers" | python3 -c "import sys,json; print(f'   Customers: {len(json.load(sys.stdin))}')" 2>/dev/null
curl -sf "http://localhost:${API_PORT}/api/v1/so" | python3 -c "import sys,json; print(f'   Sales Orders: {len(json.load(sys.stdin))}')" 2>/dev/null

echo ""
echo "  停止: ./start.sh --stop"
[ "$CMD" = "--logs" ] && docker compose logs -f