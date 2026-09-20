from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest
from sochron1k.policy_evidence import NewsGateFrame
from sochron_worker.news_gate import (
    CalendarGateway,
    NewsGateCollector,
    NewsGateUnavailable,
)
from sochron_worker.news_gate_cli import main as news_main
from sochron_worker.news_gate_cli import process
from sochron_worker.news_gate_config import (
    NewsGateConfig,
    NewsGateConfigInvalid,
    load_news_gate_config,
)

TOKEN = "n" * 48


@dataclass
class Clock:
    utc: datetime = datetime(2026, 9, 20, 3, 0, tzinfo=UTC)

    def now(self) -> datetime:
        return self.utc


@pytest.fixture
def private_directory(tmp_path: Path) -> Path:
    path = (tmp_path / "private").resolve()
    path.mkdir(mode=0o700)
    return path


@pytest.fixture
def config(private_directory: Path) -> NewsGateConfig:
    token = private_directory / "calendar.token"
    token.write_text(TOKEN)
    token.chmod(0o600)
    return NewsGateConfig(
        origin="https://calendar.example.com",
        credential_file=token,
        output_file=private_directory / "news.json",
        currencies=("USD",),
        impacts=("high",),
        blackout_before_seconds=1_800,
        blackout_after_seconds=1_800,
        poll_seconds=60,
    )


def event(clock: Clock, identifier: str, seconds: float = 0, **updates) -> dict:
    value = {
        "event_id": identifier,
        "scheduled_at_utc": (clock.utc + timedelta(seconds=seconds)).isoformat(),
        "currency": "USD",
        "impact": "high",
        "status": "scheduled",
    }
    value.update(updates)
    return value


def window(clock: Clock, config: NewsGateConfig, events=(), **updates) -> dict:
    value = {
        "protocol": "sochron.calendar-window.v1",
        "source_id": "licensed-calendar-fixture",
        "revision": "source-revision-1",
        "published_at_utc": clock.utc.isoformat(),
        "coverage_from_utc": (
            clock.utc - timedelta(seconds=config.blackout_after_seconds)
        ).isoformat(),
        "coverage_until_utc": (
            clock.utc
            + timedelta(seconds=config.blackout_before_seconds, microseconds=1)
        ).isoformat(),
        "complete": True,
        "events": list(events),
    }
    value.update(updates)
    return value


def response(payload: object, *, status=200, headers=None) -> httpx.Response:
    selected = {"content-type": "application/json"}
    if headers:
        selected.update(headers)
    return httpx.Response(
        status,
        headers=selected,
        stream=httpx.ByteStream(json.dumps(payload).encode()),
    )


def collector(config, clock, handler) -> NewsGateCollector:
    gateway = CalendarGateway(config, transport=httpx.MockTransport(handler))
    return NewsGateCollector(config, gateway, utc_now=clock.now)


def write_config(path: Path, config: NewsGateConfig, **updates) -> None:
    value = {
        "enabled": True,
        "origin": config.origin,
        "credential_file": str(config.credential_file),
        "output_file": str(config.output_file),
        "currencies": list(config.currencies),
        "impacts": list(config.impacts),
        "blackout_before_seconds": config.blackout_before_seconds,
        "blackout_after_seconds": config.blackout_after_seconds,
        "poll_seconds": config.poll_seconds,
    }
    value.update(updates)
    path.write_text(json.dumps(value))
    path.chmod(0o600)


def test_ac01_unset_and_exact_disabled_configuration_are_inert(
    monkeypatch, private_directory, capsys
):
    monkeypatch.delenv("SOCHRON_NEWS_GATE_CONFIG_FILE", raising=False)
    assert load_news_gate_config() is None
    assert news_main(["status"]) == 0
    assert json.loads(capsys.readouterr().out) == {
        "state": "DISABLED",
        "news_ready": False,
        "execution_ready": False,
        "auto_trading_enabled": False,
    }

    path = private_directory / "disabled.json"
    path.write_text('{"enabled":false}')
    path.chmod(0o600)
    monkeypatch.setenv("SOCHRON_NEWS_GATE_CONFIG_FILE", str(path))
    assert load_news_gate_config() is None


def test_ac01_loads_exact_private_config_and_rejects_expansion(
    monkeypatch, private_directory, config
):
    path = private_directory / "collector.json"
    write_config(path, config, currencies=["USD", "EUR"], impacts=["high", "medium"])
    monkeypatch.setenv("SOCHRON_NEWS_GATE_CONFIG_FILE", str(path))
    loaded = load_news_gate_config()
    assert loaded.currencies == ("EUR", "USD")
    assert loaded.impacts == ("high", "medium")

    write_config(path, config, unexpected=True)
    with pytest.raises(NewsGateConfigInvalid):
        load_news_gate_config()
    write_config(path, config, origin="http://127.0.0.1:54321")
    with pytest.raises(NewsGateConfigInvalid):
        load_news_gate_config()
    write_config(path, config, credential_file=str(config.output_file))
    with pytest.raises(NewsGateConfigInvalid):
        load_news_gate_config()
    write_config(path, config)
    path.chmod(0o644)
    with pytest.raises(NewsGateConfigInvalid):
        load_news_gate_config()


def test_ac01_ac05_rejects_linked_output_and_permissive_directory(
    monkeypatch, private_directory, config
):
    path = private_directory / "collector.json"
    write_config(path, config)
    monkeypatch.setenv("SOCHRON_NEWS_GATE_CONFIG_FILE", str(path))
    target = private_directory / "target.json"
    target.write_text("{}")
    target.chmod(0o600)
    os.link(target, config.output_file)
    with pytest.raises(NewsGateConfigInvalid):
        load_news_gate_config()
    config.output_file.unlink()
    private_directory.chmod(0o750)
    with pytest.raises(NewsGateConfigInvalid):
        load_news_gate_config()


def test_ac02_ac04_fetches_exact_window_and_publishes_deterministic_gate(config):
    clock = Clock()
    observed_requests = []
    events = (
        event(clock, "ended-at-boundary", -1_800),
        event(clock, "blocking-event", 0),
        event(clock, "cancelled-event", 60, status="cancelled"),
        event(clock, "starts-at-boundary", 1_800),
    )

    def handle(request: httpx.Request) -> httpx.Response:
        observed_requests.append(request)
        return response(window(clock, config, events))

    gate = collector(config, clock, handle).refresh()
    assert gate.blocking_event_ids == ("blocking-event", "starts-at-boundary")
    assert gate.blocked is True
    assert gate.observed_at_utc == clock.utc
    assert gate.revision.startswith("source-revision-1.sha256-")
    assert len(gate.revision) == len("source-revision-1.sha256-") + 64
    stored = NewsGateFrame.model_validate_json(config.output_file.read_text())
    assert stored == gate
    assert os.stat(config.output_file).st_mode & 0o777 == 0o600

    request = observed_requests[0]
    assert request.method == "GET"
    assert request.url.path == "/v1/calendar-window"
    assert request.headers["authorization"] == "Bearer " + TOKEN
    assert request.headers["accept-encoding"] == "identity"
    assert request.url.params["currencies"] == "USD"
    assert request.url.params["impacts"] == "high"
    assert request.url.params["from"].endswith("Z")
    assert request.url.params["until"].endswith("Z")

    repeated = collector(config, clock, handle).refresh()
    assert repeated == gate


def test_ac03_receipt_time_and_coverage_are_checked_after_response(config):
    clock = Clock()
    value = window(
        clock,
        config,
        coverage_from_utc=(clock.utc - timedelta(minutes=31)).isoformat(),
        coverage_until_utc=(clock.utc + timedelta(minutes=31)).isoformat(),
    )

    def delayed(request):
        clock.utc += timedelta(seconds=1)
        return response(value)

    gate = collector(config, clock, delayed).refresh()
    assert gate.observed_at_utc == datetime(2026, 9, 20, 3, 0, 1, tzinfo=UTC)

    exact_clock = Clock()
    exact = window(exact_clock, config)

    def outside_attestation(request):
        exact_clock.utc += timedelta(microseconds=1)
        return response(exact)

    with pytest.raises(NewsGateUnavailable):
        collector(config, exact_clock, outside_attestation).refresh()


@pytest.mark.parametrize(
    "mutation",
    [
        lambda value, clock, config: value.update(complete=False),
        lambda value, clock, config: value.update(extra="untrusted"),
        lambda value, clock, config: value.update(
            published_at_utc=(clock.utc - timedelta(seconds=301)).isoformat()
        ),
        lambda value, clock, config: value.update(
            published_at_utc=(clock.utc + timedelta(microseconds=1)).isoformat()
        ),
        lambda value, clock, config: value.update(
            coverage_from_utc=(clock.utc - timedelta(seconds=1_799)).isoformat()
        ),
        lambda value, clock, config: value.update(
            coverage_until_utc=(clock.utc + timedelta(seconds=1_800)).isoformat()
        ),
        lambda value, clock, config: value.update(
            events=[event(clock, "duplicate"), event(clock, "duplicate", 1)]
        ),
        lambda value, clock, config: value.update(
            events=[event(clock, "later", 1), event(clock, "earlier")]
        ),
        lambda value, clock, config: value.update(
            events=[event(clock, "wrong-currency", currency="EUR")]
        ),
        lambda value, clock, config: value.update(
            events=[event(clock, "wrong-impact", impact="medium")]
        ),
        lambda value, clock, config: value.update(
            events=[event(clock, "outside", 1_801)]
        ),
    ],
)
def test_ac03_rejects_incomplete_stale_or_incoherent_windows(config, mutation):
    clock = Clock()
    value = window(clock, config)
    mutation(value, clock, config)
    with pytest.raises(NewsGateUnavailable):
        collector(config, clock, lambda request: response(value)).refresh()
    assert not config.output_file.exists()


@pytest.mark.parametrize(
    "factory",
    [
        lambda value: httpx.Response(302, headers={"location": "https://other.example/"}),
        lambda value: httpx.Response(
            200,
            headers={"content-type": "text/plain"},
            stream=httpx.ByteStream(json.dumps(value).encode()),
        ),
        lambda value: httpx.Response(
            200,
            headers={"content-type": "application/json", "content-encoding": "gzip"},
            stream=httpx.ByteStream(json.dumps(value).encode()),
        ),
        lambda value: httpx.Response(
            200,
            headers={"content-type": "application/json", "content-length": "262145"},
            stream=httpx.ByteStream(b"{}"),
        ),
        lambda value: httpx.Response(
            200,
            headers={"content-type": "application/json"},
            stream=httpx.ByteStream(b"{" + b" " * 262_144),
        ),
    ],
)
def test_ac02_rejects_transport_expansion_and_oversized_content(config, factory):
    clock = Clock()
    value = window(clock, config)
    with pytest.raises(NewsGateUnavailable):
        collector(config, clock, lambda request: factory(value)).refresh()


def test_ac03_rejects_duplicate_json_keys(config):
    clock = Clock()
    raw = (
        json.dumps(window(clock, config))[:-1]
        + ',"complete":true}'
    ).encode()
    reply = httpx.Response(
        200,
        headers={"content-type": "application/json"},
        stream=httpx.ByteStream(raw),
    )
    with pytest.raises(NewsGateUnavailable):
        collector(config, clock, lambda request: reply).refresh()


def test_ac05_failed_refresh_preserves_last_good_gate(config):
    clock = Clock()
    good = collector(
        config,
        clock,
        lambda request: response(window(clock, config, (event(clock, "blocked"),))),
    ).refresh()
    before = config.output_file.read_bytes()
    before_inode = config.output_file.stat().st_ino

    unavailable = collector(config, clock, lambda request: response({}, status=503))
    with pytest.raises(NewsGateUnavailable):
        unavailable.refresh()
    assert config.output_file.read_bytes() == before
    assert config.output_file.stat().st_ino == before_inode
    assert NewsGateFrame.model_validate_json(before) == good


def test_ac05_rejects_symlink_output(config, private_directory):
    target = private_directory / "target.json"
    target.write_text("keep")
    target.chmod(0o600)
    config.output_file.symlink_to(target)
    clock = Clock()
    with pytest.raises(NewsGateUnavailable):
        collector(
            config,
            clock,
            lambda request: response(window(clock, config)),
        ).refresh()
    assert target.read_text() == "keep"


def test_ac06_cli_is_redacted_and_retry_budget_is_bounded(
    monkeypatch, private_directory, config, capsys
):
    path = private_directory / "collector.json"
    write_config(path, config)
    monkeypatch.setenv("SOCHRON_NEWS_GATE_CONFIG_FILE", str(path))
    assert news_main(["status"]) == 0
    status = json.loads(capsys.readouterr().out)
    assert status == {
        "state": "CONFIGURED",
        "news_ready": False,
        "execution_ready": False,
        "auto_trading_enabled": False,
    }
    assert news_main(["invalid", TOKEN]) == 2
    assert TOKEN not in capsys.readouterr().out

    class FailingCollector:
        def refresh(self):
            raise NewsGateUnavailable()

    sleeps = []
    assert process(config, FailingCollector(), once=False, sleep=sleeps.append) == 3
    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert [line["state"] for line in lines] == [
        "UNAVAILABLE",
        "UNAVAILABLE",
        "UNAVAILABLE",
        "UNAVAILABLE",
        "UNAVAILABLE",
        "RETRY_BUDGET_EXHAUSTED",
    ]
    assert sleeps == [2, 4, 8, 16]
