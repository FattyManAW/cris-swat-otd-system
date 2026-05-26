"""Health check + root endpoint tests"""
import pytest


class TestHealth:
    def test_healthz(self, client):
        r = client.get("/healthz")
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert data["message"] == "OTD ERP Simulator is running"

    def test_root(self, client):
        r = client.get("/")
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True


class TestHealthERP:
    """erp_sim 版本的 health/hoot — 和 main.py 完全鏡像"""

    def test_healthz(self, client):
        r = client.get("/healthz")
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_root(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert r.json()["ok"] is True
