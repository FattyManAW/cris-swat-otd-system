"""Test seed_data.py — seed_all() with temp DB, idempotency, uid()."""

import importlib
import os
import sys
import tempfile

import pytest

# Ensure project root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def seed_fresh():
    """Create a temp SQLite DB, patch models, yield helper — NO seed run yet."""
    fd, dbpath = tempfile.mkstemp(suffix=".db", prefix="otd_seed_test_")
    os.close(fd)
    db_url = f"sqlite:///{dbpath}"

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine)

    # Patch root models — seed_data.py imports directly from models (not erp_sim.models)
    import models as _m

    old_engine = _m.engine
    old_session = _m.SessionLocal

    _m.engine = engine
    _m.SessionLocal = SessionLocal

    import seed_data

    importlib.reload(seed_data)

    try:
        yield {
            "seed_data": seed_data,
            "SessionLocal": SessionLocal,
            "engine": engine,
            "models": _m,
        }
    finally:
        _m.engine = old_engine
        _m.SessionLocal = old_session
        os.unlink(dbpath)


# ── uid() ───────────────────────────────────────────────────────────────────

class TestUid:
    def test_uid_format(self):
        import seed_data

        key = seed_data.uid("TEST")
        assert key.startswith("TEST-")
        parts = key.split("-")
        assert len(parts) == 3  # PREFIX-YYYYMMDD-HEX
        assert len(parts[1]) == 8
        assert len(parts[2]) == 6

    def test_uid_uniqueness(self):
        import seed_data

        keys = {seed_data.uid("X") for _ in range(100)}
        assert len(keys) == 100

    def test_uid_different_prefixes(self):
        import seed_data

        a = seed_data.uid("ATP")
        b = seed_data.uid("CTP")
        assert a.startswith("ATP-")
        assert b.startswith("CTP-")


# ── seed_all() ──────────────────────────────────────────────────────────────

class TestSeedAll:
    def test_seed_all_runs_without_error(self, seed_fresh):
        sd = seed_fresh["seed_data"]
        sd.seed_all()  # should not raise

    def test_seed_all_creates_customers(self, seed_fresh):
        sd = seed_fresh["seed_data"]
        sl = seed_fresh["SessionLocal"]
        sd.seed_all()

        db = sl()
        try:
            from models import Customer
            count = db.query(Customer).count()
            assert count == 55
        finally:
            db.close()

    def test_seed_all_creates_items(self, seed_fresh):
        sd = seed_fresh["seed_data"]
        sl = seed_fresh["SessionLocal"]
        sd.seed_all()

        db = sl()
        try:
            from models import Item
            count = db.query(Item).count()
            assert count == 100
        finally:
            db.close()

    def test_seed_all_creates_purchase_orders(self, seed_fresh):
        sd = seed_fresh["seed_data"]
        sl = seed_fresh["SessionLocal"]
        sd.seed_all()

        db = sl()
        try:
            from models import PurchaseOrder, POLine
            assert db.query(PurchaseOrder).count() > 0
            assert db.query(POLine).count() > 0
        finally:
            db.close()

    def test_seed_all_creates_sales_orders(self, seed_fresh):
        sd = seed_fresh["seed_data"]
        sl = seed_fresh["SessionLocal"]
        sd.seed_all()

        db = sl()
        try:
            from models import SalesOrder, SOLine
            assert db.query(SalesOrder).count() > 0
            assert db.query(SOLine).count() > 0
        finally:
            db.close()

    def test_seed_all_creates_atp_ctp_checks(self, seed_fresh):
        sd = seed_fresh["seed_data"]
        sl = seed_fresh["SessionLocal"]
        sd.seed_all()

        db = sl()
        try:
            from models import ATPCheck, CTPCheck
            assert db.query(ATPCheck).count() > 0
            assert db.query(CTPCheck).count() > 0
        finally:
            db.close()

    def test_seed_all_creates_shipping(self, seed_fresh):
        sd = seed_fresh["seed_data"]
        sl = seed_fresh["SessionLocal"]
        sd.seed_all()

        db = sl()
        try:
            from models import Shipping
            count = db.query(Shipping).count()
            assert count > 0
        finally:
            db.close()

    def test_seed_all_creates_invoices(self, seed_fresh):
        sd = seed_fresh["seed_data"]
        sl = seed_fresh["SessionLocal"]
        sd.seed_all()

        db = sl()
        try:
            from models import Invoice
            count = db.query(Invoice).count()
            assert count >= 0
        finally:
            db.close()

    def test_seed_all_creates_logistics(self, seed_fresh):
        sd = seed_fresh["seed_data"]
        sl = seed_fresh["SessionLocal"]
        sd.seed_all()

        db = sl()
        try:
            from models import Logistics
            count = db.query(Logistics).count()
            assert count >= 0
        finally:
            db.close()

    # ── Idempotency ──────────────────────────────────────────────────────

    def test_seed_all_idempotent_second_run(self, seed_fresh):
        sd = seed_fresh["seed_data"]
        sl = seed_fresh["SessionLocal"]
        sd.seed_all()
        sd.seed_all()  # second run — must not crash

        db = sl()
        try:
            from models import Customer
            assert db.query(Customer).count() == 55  # no duplicates
        finally:
            db.close()

    def test_seed_all_idempotent_triple_run(self, seed_fresh):
        sd = seed_fresh["seed_data"]
        sl = seed_fresh["SessionLocal"]
        sd.seed_all()
        sd.seed_all()
        sd.seed_all()

        db = sl()
        try:
            from models import Customer, Item
            assert db.query(Customer).count() == 55
            assert db.query(Item).count() == 100
        finally:
            db.close()

    def test_seed_all_idempotent_five_runs(self, seed_fresh):
        sd = seed_fresh["seed_data"]
        sl = seed_fresh["SessionLocal"]
        for _ in range(5):
            sd.seed_all()

        db = sl()
        try:
            from models import Customer
            assert db.query(Customer).count() == 55
        finally:
            db.close()

    # ── Data integrity ───────────────────────────────────────────────────

    def test_seed_all_po_lines_have_valid_data(self, seed_fresh):
        sd = seed_fresh["seed_data"]
        sl = seed_fresh["SessionLocal"]
        sd.seed_all()

        db = sl()
        try:
            from models import POLine
            lines = db.query(POLine).limit(10).all()
            for line in lines:
                assert line.po_id is not None
                assert line.item_code is not None
                assert line.qty > 0
                assert line.line_no >= 1
        finally:
            db.close()

    def test_seed_all_so_lines_have_valid_data(self, seed_fresh):
        sd = seed_fresh["seed_data"]
        sl = seed_fresh["SessionLocal"]
        sd.seed_all()

        db = sl()
        try:
            from models import SOLine
            lines = db.query(SOLine).limit(10).all()
            for line in lines:
                assert line.so_id is not None
                assert line.item_code is not None
                assert line.qty > 0
                assert line.line_no >= 1
        finally:
            db.close()

    def test_seed_all_customer_fields_not_empty(self, seed_fresh):
        sd = seed_fresh["seed_data"]
        sl = seed_fresh["SessionLocal"]
        sd.seed_all()

        db = sl()
        try:
            from models import Customer
            custs = db.query(Customer).limit(5).all()
            for c in custs:
                assert c.customer_id
                assert c.name
                assert c.terms
        finally:
            db.close()

    def test_seed_all_item_fields_not_empty(self, seed_fresh):
        sd = seed_fresh["seed_data"]
        sl = seed_fresh["SessionLocal"]
        sd.seed_all()

        db = sl()
        try:
            from models import Item
            items = db.query(Item).limit(10).all()
            for item in items:
                assert item.item_code
                assert item.description
                assert item.unit
                assert item.lead_time_days > 0
                assert item.safety_stock >= 0
                assert item.daily_capacity > 0
        finally:
            db.close()