from __future__ import annotations

import asyncio
import base64
import json
import os
import secrets
import signal
import sqlite3
import subprocess
import sys
import threading
import time
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from uuid import UUID

import httpx
import pytest
from sochron1k.chart import ChartSettings
from sochron1k.telemetry import DemoIdentity
from sochron_worker import sync_http
from sochron_worker.__main__ import main, process
from sochron_worker.sync_config import (
    SyncConfig,
    SyncConfigInvalid,
    load_config,
    origin,
    read_service_key,
)
from sochron_worker.sync_driver import (
    DestinationConflict,
    DestinationUnavailable,
    SendBudgetExhausted,
    SyncDriver,
)
from sochron_worker.sync_http import SupabaseDestination
from test_bar_history import archive as archive
from test_chart import setup_chart as setup_chart
from test_sync_driver import ORIGIN, OWNER, FakeDestination, reopen
from test_sync_driver import journal as journal


@pytest.fixture
def config(journal, tmp_path):
    key = tmp_path / "worker-key"
    key.write_text("sb_secret_" + secrets.token_urlsafe(32))
    key.chmod(0o600)
    binding = json.loads(journal.source.binding_json)
    return SyncConfig(
        journal.source.directory,
        journal.directory,
        UUID(journal.source.archive_id),
        DemoIdentity.model_validate(binding["identity"]),
        binding["offset"],
        ChartSettings.model_validate(binding["chart"]),
        OWNER,
        ORIGIN,
        key,
    )


def json_config(config):
    return dict(
        enabled=True,
        source_directory=str(config.source_directory),
        state_directory=str(config.state_directory),
        archive_id=str(config.archive_id),
        identity=config.identity.model_dump(mode="json"),
        offset_seconds=config.offset_seconds,
        chart=config.chart.model_dump(mode="json"),
        owner_id=str(config.owner_id),
        origin=config.origin,
        service_key_file=str(config.service_key_file),
    )


def configure(config, tmp_path, monkeypatch, data=None):
    path = tmp_path / "worker-config.json"
    path.write_text(json.dumps(json_config(config) if data is None else data))
    path.chmod(0o600)
    monkeypatch.setenv("SOCHRON_SYNC_CONFIG_FILE", str(path))
    return path


def response(data, *, status=200, headers=None):
    return httpx.Response(
        status,
        headers={"content-type": "application/json", **(headers or {})},
        stream=httpx.ByteStream(json.dumps(data).encode()),
    )


def test_private_config_roundtrip_and_disabled(config, tmp_path, monkeypatch):
    monkeypatch.delenv("SOCHRON_SYNC_CONFIG_FILE", raising=False)
    assert load_config() is None
    configure(config, tmp_path, monkeypatch)
    assert load_config() == config
    configure(config, tmp_path, monkeypatch, {"enabled": False})
    assert load_config() is None


@pytest.mark.parametrize("raises", [False, True])
def test_installed_entry_point_shares_sigterm_handler_and_restores_it(monkeypatch, raises):
    import sochron_worker.__main__ as entry

    previous = signal.getsignal(signal.SIGTERM)

    def invoke():
        assert signal.getsignal(signal.SIGTERM) is entry.stop
        if raises:
            raise SystemExit(0)
        return 17

    monkeypatch.setattr(entry, "main", invoke)
    if raises:
        with pytest.raises(SystemExit):
            entry.cli()
    else:
        assert entry.cli() == 17
    assert signal.getsignal(signal.SIGTERM) is previous


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com",
        "https://x.test/",
        "https://x.test/path",
        "https://x.test?key=secret",
        "https://u:p@x.test",
        "https://x.test#foo",
        "https://x.test:443",
        "https://x.test:99999",
        "https://x..test",
        "https://-x.test",
        "https://x_.test",
        "https://例.test",
        "https://X.test",
        "https://127.0.0.1",
        "http://localhost:54321",
        "http://127.0.0.1:80",
        "http://127.0.0.1:65536",
        "http://127.0.0.1:054321",
        "https://x.test\\@evil.test",
        " https://x.test",
        "https://x.test\n",
        "https://x.test\x00",
        "https://x.test.",
    ],
)
def test_ambiguous_origins_denied(url):
    with pytest.raises(SyncConfigInvalid):
        origin(url)


@pytest.mark.parametrize(
    "mode",
    [
        "public",
        "symlink",
        "hardlink",
        "oversize",
        "duplicate",
        "unknown",
        "offset",
        "same-dir",
        "numeric-disabled",
        "parent",
    ],
)
def test_config_denials_redacted(config, tmp_path, monkeypatch, mode):
    data = json_config(config)
    if mode == "unknown":
        data["untrusted"] = "do not print me"
    elif mode == "offset":
        data["offset_seconds"] = True
    elif mode == "same-dir":
        data["state_directory"] = data["source_directory"]
    elif mode == "numeric-disabled":
        data = {"enabled": 0}
    path = configure(config, tmp_path, monkeypatch, data)
    if mode == "public":
        path.chmod(0o644)
    elif mode == "parent":
        tmp_path.chmod(0o755)
    elif mode == "symlink":
        alias = tmp_path / "alias"
        alias.symlink_to(path)
        monkeypatch.setenv("SOCHRON_SYNC_CONFIG_FILE", str(alias))
    elif mode == "hardlink":
        os.link(path, tmp_path / "alias")
    elif mode == "oversize":
        path.write_text(" " * 16385)
    elif mode == "duplicate":
        path.write_text('{"enabled":false,"enabled":true}')
    with pytest.raises(SyncConfigInvalid, match=r"^SYNC_CONFIG_INVALID$"):
        load_config()


def legacy_key(role="service_role", expiry=4102444800):
    def part(value):
        return base64.urlsafe_b64encode(json.dumps(value).encode()).decode().rstrip("=")

    return ".".join(
        (part({"alg": "HS256"}), part({"role": role, "exp": expiry}), secrets.token_urlsafe(32))
    )


@pytest.mark.parametrize("kind", ["anon", "authenticated", "expired", "publishable", "newline"])
def test_wrong_service_keys_denied(config, kind):
    key = (
        legacy_key(kind)
        if kind in {"anon", "authenticated"}
        else (
            legacy_key(expiry=1)
            if kind == "expired"
            else "sb_publishable_" + secrets.token_urlsafe(32)
            if kind == "publishable"
            else "sb_secret_" + secrets.token_urlsafe(32) + "\r\nInjected: header"
        )
    )
    config.service_key_file.write_text(key)
    with pytest.raises(SyncConfigInvalid):
        read_service_key(config.service_key_file)


@pytest.mark.parametrize("legacy", [False, True])
def test_two_fixed_rpcs_exact_headers_payload_and_no_ack_shortcut(config, journal, legacy):
    if legacy:
        config.service_key_file.write_text(legacy_key())
    calls = []
    batch = journal.source.read()

    def handle(request):
        calls.append(request)
        assert request.method == "POST" and request.url.host == "127.0.0.1"
        assert request.headers["apikey"] == config.service_key_file.read_text()
        assert ("authorization" in request.headers) == legacy
        assert request.headers["accept-encoding"] == "identity"
        args = json.loads(request.content)
        assert args["p_owner_id"] == str(OWNER) and args["p_archive_id"] == str(config.archive_id)
        if request.url.path.endswith("sochron_store_native_m1"):
            assert args["p_rows"] == batch.wire_rows()
            return response({"ignored_ack": True}, headers={"set-cookie": "test=not-retained"})
        assert request.url.path == "/rest/v1/rpc/sochron_read_native_m1"
        assert "cookie" not in request.headers
        assert args["p_times"] == [r.cursor.time_server_s for r in batch.rows]
        return response(
            {
                "archive_id": batch.archive_id,
                "binding": json.loads(batch.binding_json),
                "rows": batch.wire_rows(),
            }
        )

    target = SupabaseDestination(config, transport=httpx.MockTransport(handle))
    assert SyncDriver(journal, target).step() == "VERIFIED"
    assert len(calls) == 2


@pytest.mark.parametrize("status", [301, 302, 307, 308, 400, 401, 403, 404, 429, 500, 503])
def test_errors_never_follow_redirects_or_advance(config, journal, status):
    calls = []

    def handle(request):
        calls.append(request)
        return response({}, status=status, headers={"location": "https://foreign.example.test"})

    target = SupabaseDestination(config, transport=httpx.MockTransport(handle))
    assert SyncDriver(journal, target).step() == "UNKNOWN"
    assert len(calls) == 1 and journal.status().cursor.receipt == 0


@pytest.mark.parametrize("kind", ["known", "unknown", "broken-json", "gzip", "length", "stream"])
def test_conflict_and_bounded_responses(config, journal, kind):
    def handle(request):
        if kind in {"known", "unknown"}:
            return response(
                {"code": "23505", "message": "NATIVE_BAR_CONFLICT" if kind == "known" else "other"},
                status=409,
            )
        if kind == "broken-json":
            return httpx.Response(
                200,
                headers={"content-type": "application/json"},
                stream=httpx.ByteStream(b'{"rows":[],"rows":[]}'),
            )
        return response(
            "x" * (262145 if kind == "stream" else 1),
            headers=(
                {"content-encoding": "gzip"}
                if kind == "gzip"
                else {"content-length": "262145"}
                if kind == "length"
                else {}
            ),
        )

    target = SupabaseDestination(config, transport=httpx.MockTransport(handle))
    if kind in {"known", "broken-json"}:
        with pytest.raises(DestinationConflict):
            target.read(journal.source.read())
    else:
        with pytest.raises(DestinationUnavailable):
            target.read(journal.source.read())


def test_overall_deadline_cancels_drip_response(config, journal, monkeypatch):
    closed = []

    class Drip(httpx.AsyncByteStream):
        async def __aiter__(self):
            while True:
                await asyncio.sleep(0.01)
                yield b" "

        async def aclose(self):
            closed.append(True)

    monkeypatch.setattr(sync_http, "TOTAL_SECONDS", 0.06)
    target = SupabaseDestination(
        config,
        transport=httpx.MockTransport(
            lambda r: httpx.Response(
                200, headers={"content-type": "application/json"}, stream=Drip()
            )
        ),
    )
    started = time.monotonic()
    assert SyncDriver(journal, target).step() == "UNKNOWN"
    assert time.monotonic() - started < 1 and closed


def test_real_loopback_no_environment_proxy_and_lost_response(config, journal, monkeypatch):
    effects = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            data = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            if self.path.endswith("sochron_store_native_m1"):
                effects.append(data)
                self.close_connection = True  # Accepted, then no HTTP response at all.
                return
            snapshot = dict(
                archive_id=data["p_archive_id"],
                binding=effects[0]["p_binding"],
                rows=effects[0]["p_rows"],
            )
            encoded = json.dumps(snapshot).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        target_config = replace(config, origin=f"http://127.0.0.1:{server.server_port}")
        # This journal is a fresh synthetic fixture, never an operator binding change.
        from sochron_worker.sync_journal import SyncJournal

        directory = config.state_directory.parent / "http-worker"
        directory.mkdir(mode=0o700)
        with SyncJournal(
            directory,
            journal.source,
            OWNER,
            target_config.origin,
            create=True,
            utc_now=journal._now,
        ) as state:
            monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:1")
            monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:1")
            monkeypatch.setenv("ALL_PROXY", "http://127.0.0.1:1")
            monkeypatch.setenv("NO_PROXY", "")
            monkeypatch.setenv("SSL_CERT_FILE", "/no-such-test-ca-file")
            driver = SyncDriver(state, SupabaseDestination(target_config))
            assert driver.step() == "UNKNOWN"
            assert driver.step() == "VERIFIED"
            assert len(effects) == 1
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_commands_disabled_and_redacted(config, tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("SOCHRON_SYNC_CONFIG_FILE", raising=False)
    assert main(["run", "--once"]) == 0
    assert json.loads(capsys.readouterr().out)["state"] == "DISABLED"
    secret = config.service_key_file.read_text()
    assert main(["run", "--secret", secret]) == 2
    output = capsys.readouterr()
    assert secret not in output.out + output.err and "SYNC_CONFIG_INVALID" in output.out
    path = configure(config, tmp_path, monkeypatch)
    path.chmod(0o644)
    assert main(["run"]) == 2
    assert secret not in capsys.readouterr().out


def test_runner_bounded_backoff_and_once(journal, capsys):
    target = FakeDestination()
    target.lose = target.read_fail = True
    sleeps = []
    assert process(journal, SyncDriver(journal, target), sleep=sleeps.append) == 3
    assert sleeps == [1, 2, 4, 8]
    assert target.calls == ["store", "read", "read", "read", "read"]
    assert journal.status().pending.attempts == 1
    assert "RETRY_BUDGET_EXHAUSTED" in capsys.readouterr().out
    target.read_fail = False
    assert process(journal, SyncDriver(journal, target), once=True) == 0


@pytest.mark.parametrize("accepted", [False, True])
def test_send_budget_survives_restart_but_final_unknown_can_reconcile(
    journal, setup_chart, accepted
):
    target = FakeDestination()
    target.ack_without_write = True
    driver = SyncDriver(journal, target)
    for _ in range(4):
        assert driver.step() == "PREPARED"
    target.ack_without_write = not accepted
    target.lose = accepted
    assert driver.step() == ("UNKNOWN" if accepted else "PREPARED")
    assert journal.status().pending.attempts == 5
    with reopen(journal, setup_chart) as restarted:
        if accepted:
            assert SyncDriver(restarted, target).step() == "VERIFIED"
        else:
            with pytest.raises(SendBudgetExhausted):
                SyncDriver(restarted, target).step()
            assert restarted.status().pending.attempts == 5
    assert target.calls.count("store") == 5


def test_init_and_status_need_no_service_key_or_network(config, tmp_path, monkeypatch, capsys):
    directory = tmp_path / "new-state"
    directory.mkdir(mode=0o700)
    config = replace(config, state_directory=directory)
    configure(config, tmp_path, monkeypatch)
    config.service_key_file.unlink()
    import sochron_worker.__main__ as entry

    def denied(*args, **kwargs):
        pytest.fail("init/status touched network credentials")

    monkeypatch.setattr(entry, "SupabaseDestination", denied)
    assert main(["init"]) == 0
    assert json.loads(capsys.readouterr().out)["state"] == "INITIALIZED"
    assert main(["status"]) == 0
    status = json.loads(capsys.readouterr().out)
    assert status["state"] == "LOCAL_STATUS" and status["cursor_receipt"] == 0
    assert main(["init"]) == 2
    assert "SYNC_JOURNAL_UNAVAILABLE" in capsys.readouterr().out


def test_oversized_request_and_wrong_archive_make_no_http_call(config, journal, monkeypatch):
    calls = []
    target = SupabaseDestination(config, transport=httpx.MockTransport(lambda r: calls.append(r)))
    batch = journal.source.read()
    with pytest.raises(DestinationConflict):
        target.store(replace(batch, archive_id=str(OWNER)))
    monkeypatch.setattr(sync_http, "MAX_HTTP_BYTES", 1)
    with pytest.raises(DestinationUnavailable):
        target.store(batch)
    assert calls == []


def test_real_cli_sigterm_retains_unknown_then_reconciles(config, tmp_path, monkeypatch):
    accepted, release = threading.Event(), threading.Event()
    effects = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            args = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            if self.path.endswith("sochron_store_native_m1"):
                effects.append(args)
                accepted.set()
                release.wait(10)
                self.close_connection = True
                return
            encoded = json.dumps(
                dict(
                    archive_id=args["p_archive_id"],
                    binding=effects[0]["p_binding"],
                    rows=effects[0]["p_rows"],
                )
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    directory = tmp_path / "cli-state"
    directory.mkdir(mode=0o700)
    config = replace(
        config, state_directory=directory, origin=f"http://127.0.0.1:{server.server_port}"
    )
    configure(config, tmp_path, monkeypatch)
    env = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join(
            str(Path(p).resolve()) for p in ("services/api/src", "services/worker/src")
        ),
    }
    command = [sys.executable, "-m", "sochron_worker"]
    child = None
    try:
        initial = subprocess.run(
            [*command, "init"], env=env, capture_output=True, text=True, timeout=10
        )
        assert initial.returncode == 0, initial.stdout + initial.stderr
        child = subprocess.Popen(
            [*command, "run", "--once"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        assert accepted.wait(5), "worker did not reach HTTP destination"
        child.send_signal(signal.SIGTERM)
        out, err = child.communicate(timeout=5)
        assert child.returncode == 130 and "STOPPED" in out and err == ""
        assert config.service_key_file.read_text() not in out
        with sqlite3.connect(directory / "sync.sqlite3") as db:
            assert db.execute("SELECT state,attempts FROM batches").fetchone() == ("UNKNOWN", 1)
            assert db.execute("SELECT receipt FROM meta").fetchone()[0] == 0
        release.set()
        restarted = subprocess.run(
            [*command, "run", "--once"], env=env, capture_output=True, text=True, timeout=10
        )
        assert restarted.returncode == 0, restarted.stdout + restarted.stderr
        assert json.loads(restarted.stdout)["state"] == "VERIFIED"
        assert len(effects) == 1
    finally:
        release.set()
        if child is not None and child.poll() is None:
            child.terminate()
            child.communicate(timeout=5)
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
