"""Synthetic, network-isolated container oracle. Never a production receiver."""

import hashlib
import json
import os
import secrets
import shutil
import sqlite3
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from uuid import uuid4

BASE = Path("/worker")
EVIDENCE = BASE / "evidence"
CONFIG = BASE / "config/config.json"
KEY = BASE / "config/key"


def fingerprint():
    with sqlite3.connect("file:/worker/source/bars.sqlite3?mode=ro", uri=True) as db:
        return hashlib.sha256("\n".join(db.iterdump()).encode()).hexdigest()


def effects():
    db = sqlite3.connect(EVIDENCE / "effects.sqlite3", timeout=2)
    db.execute("pragma synchronous=FULL")
    return db


def inspect():
    with effects() as db:
        stores = db.execute("select count(*) from requests where kind='store'").fetchone()[0]
        reads = db.execute("select count(*) from requests where kind='read'").fetchone()[0]
    result = dict(
        stores=stores,
        reads=reads,
        source_unchanged=fingerprint() == (EVIDENCE / "source.sha256").read_text(),
    )
    if (BASE / "state/sync.sqlite3").exists():
        with sqlite3.connect("file:/worker/state/sync.sqlite3?mode=ro", uri=True) as db:
            result["batches"] = db.execute("select state,attempts from batches").fetchall()
            result["receipt"] = db.execute("select receipt from meta").fetchone()[0]
    print(json.dumps(result))


def serve():
    os.umask(0o077)
    shutil.copyfile("/fixture/bars.sqlite3", BASE / "source/bars.sqlite3")
    (BASE / "source/bars.sqlite3").chmod(0o600)
    binding = json.loads(Path("/fixture/binding.json").read_text())
    KEY.write_text("sb_secret_" + secrets.token_urlsafe(32))
    CONFIG.write_text(
        json.dumps(
            dict(
                enabled=True,
                source_directory="/worker/source",
                state_directory="/worker/state",
                archive_id=binding["archive_id"],
                identity=binding["binding"]["identity"],
                offset_seconds=binding["binding"]["offset"],
                chart=binding["binding"]["chart"],
                owner_id=str(uuid4()),
                origin="http://127.0.0.1:8765",
                service_key_file=str(KEY),
            )
        )
    )
    with effects() as db:
        db.execute("create table requests (kind text not null, payload text not null)")
    (EVIDENCE / "source.sha256").write_text(fingerprint())

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_GET(self):
            self.send_response(200 if self.path == "/ready" else 404)
            self.end_headers()

        def do_POST(self):
            try:
                assert self.headers.get("apikey") == KEY.read_text()
                size = int(self.headers.get("Content-Length", "0"))
                assert 0 < size <= 262144
                args = json.loads(self.rfile.read(size))
                config = json.loads(CONFIG.read_text())
                assert args["p_owner_id"] == config["owner_id"]
                assert args["p_archive_id"] == config["archive_id"]
                kind = {
                    "/rest/v1/rpc/sochron_store_native_m1": "store",
                    "/rest/v1/rpc/sochron_read_native_m1": "read",
                }[self.path]
                with effects() as db:
                    db.execute("insert into requests values (?,?)", (kind, json.dumps(args)))
                deadline = time.monotonic() + 45
                while not (EVIDENCE / "release").exists():
                    if time.monotonic() >= deadline:
                        raise TimeoutError()
                    time.sleep(0.05)
                if kind == "store":
                    # Acceptance was committed above, but deliberately no HTTP acknowledgment.
                    self.close_connection = True
                    return
                with effects() as db:
                    stored = json.loads(
                        db.execute(
                            "select payload from requests where kind='store' order by rowid limit 1"
                        ).fetchone()[0]
                    )
                assert args["p_times"] == [row["bar"]["time_server_s"] for row in stored["p_rows"]]
                body = json.dumps(
                    dict(
                        archive_id=stored["p_archive_id"],
                        binding=stored["p_binding"],
                        rows=stored["p_rows"],
                    )
                ).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except BrokenPipeError, ConnectionResetError:
                pass  # The stopped worker deliberately abandons an in-flight request.
            except Exception:
                (EVIDENCE / "error").touch()
            finally:
                self.close_connection = True

    ThreadingHTTPServer(("127.0.0.1", 8765), Handler).serve_forever()


if __name__ == "__main__":
    action = sys.argv[1]
    if action == "serve":
        serve()
    elif action == "inspect":
        inspect()
    elif action == "release":
        (EVIDENCE / "release").touch()
    elif action == "unsafe-config":
        CONFIG.chmod(0o644)
    elif action == "safe-config":
        CONFIG.chmod(0o600)
    elif action == "check-logs":
        # Log text arrives on stdin; report only a boolean, never the generated key.
        logs = sys.stdin.read()
        assert KEY.read_text() not in logs
        assert not (EVIDENCE / "error").exists()
    elif action == "remove-key":
        KEY.unlink(missing_ok=True)
    else:
        raise SystemExit(2)
