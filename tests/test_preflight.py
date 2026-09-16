from __future__ import annotations

from datetime import timedelta

import pytest
from sochron1k.models import TradeMode
from sochron1k.preflight import PreflightDenied, validate_preflight


def test_ac01_accepts_exact_demo_identity(
    policy, account, contract, market, intent, observed_at
) -> None:
    validate_preflight(policy, account, contract, market, intent, now=observed_at)


@pytest.mark.parametrize("mode", [TradeMode.REAL, TradeMode.CONTEST, TradeMode.UNKNOWN])
def test_ac01_denies_every_non_demo_mode(
    mode, policy, account, contract, market, intent, observed_at
) -> None:
    candidate = account.model_copy(update={"trade_mode": mode})
    with pytest.raises(PreflightDenied, match="Demo") as error:
        validate_preflight(policy, candidate, contract, market, intent, now=observed_at)
    assert error.value.code == "NON_DEMO_ACCOUNT"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("account_ref", "another-demo"),
        ("server", "Other-Server"),
        ("currency", "USD"),
        ("margin_mode", "netting"),
    ],
)
def test_ac01_denies_mismatched_identity(
    field, value, policy, account, contract, market, intent, observed_at
) -> None:
    candidate = account.model_copy(update={field: value})
    with pytest.raises(PreflightDenied) as error:
        validate_preflight(policy, candidate, contract, market, intent, now=observed_at)
    assert error.value.code == "IDENTITY_MISMATCH"


def test_ac01_denies_stale_price(policy, account, contract, market, intent, observed_at) -> None:
    stale = market.model_copy(
        update={
            "event_time": observed_at - timedelta(seconds=7),
            "received_time": observed_at - timedelta(seconds=6),
        }
    )
    with pytest.raises(PreflightDenied) as error:
        validate_preflight(policy, account, contract, stale, intent, now=observed_at)
    assert error.value.code == "STALE_PRICE"


def test_ac01_denies_expired_command(
    policy, account, contract, market, intent, observed_at
) -> None:
    expired = intent.model_copy(update={"expires_at": observed_at})
    with pytest.raises(PreflightDenied) as error:
        validate_preflight(policy, account, contract, market, expired, now=observed_at)
    assert error.value.code == "EXPIRED_COMMAND"
