"""OTD 測試共用 fixtures — TestClient + temp-file SQLite, one fresh DB per test

Imports from erp_sim package so pytest-cov measures erp_sim/ coverage.
"""
import os
import sys
import tempfile

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

import erp_sim.main as _main_mod

# ── Import from erp_sim package (not root) so coverage counts erp_sim/ ──
import erp_sim.models as _models_mod

# ── Don't import main yet; it auto-runs create_all ──
# We'll import inside the fixture after patching the engine


@pytest.fixture
def client():
    """每個 test: 全新 SQLite file + 全新 import main"""
    import os

    fd, dbpath = tempfile.mkstemp(suffix=".db", prefix="otd_test_")
    os.close(fd)
    db_url = f"sqlite:///{dbpath}"

    _engine = create_engine(db_url, connect_args={"check_same_thread": False})
    _SessionLocal = sessionmaker(bind=_engine)

    # patch erp_sim.models module — so ALL code using erp_sim.models gets our engine
    _models_mod.engine = _engine
    _models_mod.SessionLocal = _SessionLocal

    # also patch the root models in case anything uses them (they're identical)
    import models
    models.engine = _engine
    models.SessionLocal = _SessionLocal

    from erp_sim.models import Base
    Base.metadata.create_all(bind=_engine)

    # patch erp_sim.main too
    _main_mod.engine = _engine
    _main_mod.SessionLocal = _SessionLocal

    from erp_sim.main import app, get_db

    def override_get_db():
        db = _SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    os.unlink(dbpath)


# ── Seed helpers ──────────────────────────────────────────────────────────

@pytest.fixture
def seed_item(client):
    r = client.post("/api/v1/items", json={
        "item_code": "CPU-001",
        "description": "測試 CPU",
        "unit": "PC",
        "category": "cpu",
        "lead_time_days": 5,
        "safety_stock": 100,
        "daily_capacity": 500,
    })
    assert r.status_code == 200, f"seed_item failed: {r.text}"
    return r.json()


@pytest.fixture
def seed_customer(client):
    r = client.post("/api/v1/customers", json={
        "customer_id": "CUST-001",
        "name": "測試客戶",
        "terms": "Net30",
        "contact_email": "test@example.com",
    })
    assert r.status_code == 200, f"seed_customer failed: {r.text}"
    return r.json()


@pytest.fixture
def seed_po(client, seed_item, seed_customer):
    r = client.post("/api/v1/po", json={
        "po_id": "PO-20260524-001",
        "customer_id": "CUST-001",
        "remarks": "測試 PO",
        "lines": [
            {"item_code": "CPU-001", "qty": 10, "unit_price": 100.0, "line_no": 1},
            {"item_code": "CPU-001", "qty": 20, "unit_price": 120.0, "line_no": 2},
        ]
    })
    assert r.status_code == 200, f"seed_po failed: {r.text}"
    return r.json()
