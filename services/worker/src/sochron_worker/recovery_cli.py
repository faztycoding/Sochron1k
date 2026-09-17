"""Explicit offline backup/verify/isolated-restore command; no implicit activation."""

import argparse
import json
import signal
import time
from datetime import UTC, datetime

from .recovery_bundle import BundleUnavailable, backup_bundle, restore_bundle, verify_bundle
from .sync_config import canonical_path


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise BundleUnavailable()


def emit(state, **fields):
    print(
        json.dumps(dict(state=state, execution_ready=False, auto_trading_enabled=False, **fields)),
        flush=True,
    )


def main(argv=None):
    try:
        parser = Parser(
            prog="sochron-recovery",
            description="Offline recovery; explicit private config, never resumes trading",
        )
        parser.add_argument("action", choices=("backup", "verify", "restore"))
        parser.add_argument("--config", required=True)
        parser.add_argument("--bundle")
        parser.add_argument("--output")
        args = parser.parse_args(argv)
        if (
            (args.action == "backup" and (args.bundle or not args.output))
            or (args.action == "verify" and (not args.bundle or args.output))
            or (args.action == "restore" and (not args.bundle or not args.output))
        ):
            raise BundleUnavailable()
        config = canonical_path(args.config)
        start = time.monotonic()
        if args.action == "backup":
            result = backup_bundle(config, canonical_path(args.output))
            state = "BACKUP_CREATED"
        elif args.action == "verify":
            result = verify_bundle(config, canonical_path(args.bundle))
            state = "BUNDLE_VERIFIED"
        else:
            result = restore_bundle(
                config, canonical_path(args.bundle), canonical_path(args.output)
            )
            state = "INSPECTION_CREATED"
        manifest, audit = result["manifest"], result["audit"]
        emit(
            state,
            elapsed_seconds=time.monotonic() - start,
            capture_age_seconds=(
                datetime.now(UTC) - datetime.fromisoformat(manifest["capture_start"])
            ).total_seconds(),
            bundle_sha256=result["bundle_sha256"],
            command_unknown=audit["commands"]["unknown"],
            total_halts=audit["commands"]["total_halts"],
            sync_pending=audit["sync"]["pending"],
            broker_reconciliation="NOT_RUN",
            destination_reconciliation="NOT_RUN",
        )
        return 0
    except KeyboardInterrupt:
        emit("STOPPED")
        return 130
    except Exception:
        emit("RECOVERY_BUNDLE_UNAVAILABLE")
        return 2


def stop(signum, frame):
    raise KeyboardInterrupt()


def cli():
    previous = signal.signal(signal.SIGTERM, stop)
    try:
        return main()
    finally:
        signal.signal(signal.SIGTERM, previous)


if __name__ == "__main__":
    raise SystemExit(cli())
