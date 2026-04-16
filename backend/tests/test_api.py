"""Integration tests for API endpoints (no DB required)"""
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestCalculatorAPI:
    @pytest.mark.asyncio
    async def test_calculate_basic(self, client):
        r = await client.post("/api/v1/calculate", json={
            "pair": "EUR/USD",
            "direction": "BUY",
            "account_balance": 1000,
            "risk_percent": 2,
            "entry_price": 1.085,
        })
        assert r.status_code == 200
        data = r.json()
        assert data["lot_size"] > 0
        assert data["risk_reward"] > 0
        assert "warnings" in data

    @pytest.mark.asyncio
    async def test_calculate_with_sl_tp(self, client):
        r = await client.post("/api/v1/calculate", json={
            "pair": "USD/JPY",
            "direction": "SELL",
            "account_balance": 500,
            "risk_percent": 1.5,
            "entry_price": 150.0,
            "sl_pips": 25,
            "tp_pips": 50,
        })
        assert r.status_code == 200
        data = r.json()
        assert data["sl_pips"] == pytest.approx(25.0)
        assert data["tp_pips"] == pytest.approx(50.0)

    @pytest.mark.asyncio
    async def test_calculate_eurjpy(self, client):
        r = await client.post("/api/v1/calculate", json={
            "pair": "EUR/JPY",
            "direction": "BUY",
            "account_balance": 2000,
            "risk_percent": 1,
            "entry_price": 165.0,
            "sl_pips": 40,
            "tp_pips": 80,
        })
        assert r.status_code == 200
        data = r.json()
        assert data["risk_reward"] == pytest.approx(2.0)

    @pytest.mark.asyncio
    async def test_calculate_invalid_pair(self, client):
        r = await client.post("/api/v1/calculate", json={
            "pair": "GBP/USD",
            "direction": "BUY",
            "account_balance": 1000,
            "risk_percent": 2,
            "entry_price": 1.25,
        })
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_calculate_invalid_direction(self, client):
        r = await client.post("/api/v1/calculate", json={
            "pair": "EUR/USD",
            "direction": "HOLD",
            "account_balance": 1000,
            "risk_percent": 2,
            "entry_price": 1.085,
        })
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_calculate_high_risk_warnings(self, client):
        r = await client.post("/api/v1/calculate", json={
            "pair": "EUR/USD",
            "direction": "BUY",
            "account_balance": 1000,
            "risk_percent": 8,
            "entry_price": 1.085,
        })
        assert r.status_code == 200
        data = r.json()
        assert len(data["warnings"]) > 0


class TestAnalysisSessionAPI:
    @pytest.mark.asyncio
    async def test_session(self, client):
        r = await client.get("/api/v1/analysis/session/current")
        assert r.status_code == 200
        data = r.json()
        assert "session" in data
        assert "is_dead_zone" in data


class TestSchemaValidation:
    @pytest.mark.asyncio
    async def test_calculator_missing_fields(self, client):
        r = await client.post("/api/v1/calculate", json={"pair": "EUR/USD"})
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_calculator_negative_balance(self, client):
        r = await client.post("/api/v1/calculate", json={
            "pair": "EUR/USD",
            "direction": "BUY",
            "account_balance": -100,
            "risk_percent": 2,
            "entry_price": 1.085,
        })
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_calculator_risk_over_10(self, client):
        r = await client.post("/api/v1/calculate", json={
            "pair": "EUR/USD",
            "direction": "BUY",
            "account_balance": 1000,
            "risk_percent": 15,
            "entry_price": 1.085,
        })
        assert r.status_code == 422


class TestSecurityHeaders:
    @pytest.mark.asyncio
    async def test_security_headers(self, client):
        r = await client.post("/api/v1/calculate", json={
            "pair": "EUR/USD",
            "direction": "BUY",
            "account_balance": 1000,
            "risk_percent": 2,
            "entry_price": 1.085,
        })
        assert r.headers.get("x-content-type-options") == "nosniff"
        assert r.headers.get("x-frame-options") == "DENY"

    @pytest.mark.asyncio
    async def test_rate_limit_headers(self, client):
        r = await client.post("/api/v1/calculate", json={
            "pair": "EUR/USD",
            "direction": "BUY",
            "account_balance": 1000,
            "risk_percent": 2,
            "entry_price": 1.085,
        })
        assert "x-ratelimit-limit" in r.headers
        assert "x-ratelimit-remaining" in r.headers
