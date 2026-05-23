# ── OTD ERP Makefile ──────────────────────────────
# Usage: make test-v2  →  跑 E2E test suite（73 checks）

.PHONY: test-v2 test help

test-v2:
	python3 test_e2e_v2.py

test: test-v2

help:
	@echo "make test-v2  跑 E2E 測試 (test_e2e_v2.py)"
	@echo "make test     同上"