"""erp_sim conftest — patches erp_sim.models for per-test DB"""
import os
import sys

import pytest

# Ensure project root is importable
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import erp_sim.models as _erp_mod


@pytest.fixture
def client():
    import tempfile
    fd, dbpath = tempfile.mkstemp(suffix=".db", prefix="erp_test_")
    os.close(fd)
    db_url = f"sqlite:///{dbpath}"

    _engine = create_engine(db_url, connect_args={"check_same_thread": False})
    _SessionLocal = sessionmaker(bind=_engine)

    _erp_mod.engine = _engine
    _erp_mod.SessionLocal = _SessionLocal

    from erp_sim.models import Base
    Base.metadata.create_all(bind=_engine)

    import erp_sim.main as erp_main
    erp_main.engine = _engine
    erp_main.SessionLocal = _SessionLocal

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
