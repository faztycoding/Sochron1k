from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sochron1k.main import create_app


@pytest.mark.anyio
@pytest.mark.parametrize("requested_mode", ["demo", "live"])
async def test_ac08_health_is_demo_only_and_never_claims_execution_ready(
    monkeypatch, requested_mode: str
) -> None:
    monkeypatch.setenv("TRADING_MODE", requested_mode)
    monkeypatch.setenv("AUTO_TRADING_ENABLED", "true")
    async with AsyncClient(
        transport=ASGITransport(app=create_app()), base_url="http://test"
    ) as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "sochron1k-api",
        "version": "0.1.0",
        "trading_mode": "demo",
        "auto_trading_enabled": False,
        "execution_ready": False,
    }
