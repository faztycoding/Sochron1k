# Demo readiness ledger

Status: SCN-031 provides a redacted API/UI inventory of what is configured,
connected or still unrun. SCN-036 adds a separate query-only normalized target
evidence reader. Neither boundary is an execution preflight, release approval or
unattended-Demo gate. Auto Trading remains off.

## UI and API positions

| Surface | Browser route | API route | Meaning |
| --- | --- | --- | --- |
| Connection map | `GET /api/ui/connections` | `GET /ui/connections` | the readiness read model itself is available |
| Demo admission ledger | `GET /api/ui/demo-readiness` | `GET /ui/demo-readiness` | nine redacted gate states and their API/source locations |
| Target evidence detail | `GET /api/owner/target-evidence` | `GET /owner/target-evidence` | owner-authenticated redacted admission state for rows 06-08 |
| UI anchor | `#demo-readiness` | n/a | full-width ledger after command lifecycle |

The connection/readiness responses are public; target evidence requires the active
owner session. All three are bounded and `Cache-Control: no-store`. They contain
no account reference, configured broker/server/symbol value, owner UUID, file path,
URL, password, token or credential. The browser renders the fixed route inventory
even when the status response fails validation.

## Optional owner decision record

Create a dedicated directory and JSON file owned by the API UID with modes `0700`
and `0600` (or stricter). Use an absolute canonical path; symlinks, public parent
directories, unknown fields and files over 16 KiB fail startup. This is operational
metadata, not a secret file, and must not contain an account reference or any
credential.

```json
{
  "protocol": "sochron.demo-owner-decisions.v1",
  "decision_revision": "reviewed-demo-plan-revision",
  "recorded_at_utc": "2026-09-20T08:00:00Z",
  "owner_approved": true,
  "broker_name": "reviewed-broker-name",
  "demo_server": "reviewed-demo-server",
  "account_currency": "USD",
  "starting_capital": "10000.00",
  "symbol": "reviewed-broker-symbol",
  "account_mode": "retail_hedging",
  "trading_hours_policy_ref": "reviewed-hours-policy",
  "overnight_policy": "flat",
  "target_executor": "hostinger_wine",
  "target_region": "reviewed-region",
  "monthly_budget_thb": "1000.00",
  "alert_destination_ref": "reviewed-alert-route",
  "halt_release_authority_ref": "named-authority-record",
  "approved_secret_channel_ref": "approved-channel-record",
  "rpo_seconds": 300,
  "rto_seconds": 1800,
  "magic_number": 910001
}
```

Point `SOCHRON_DEMO_READINESS_CONFIG_FILE` to that path before API startup.
Missing configuration yields `owner_decisions=missing`; a valid record yields only
`recorded`. None of its values are returned to the browser.

## State boundary

- `recorded` means the complete owner decision schema validated.
- `configured` means local integration settings exist.
- `awaiting_source` means a configured boundary still lacks current evidence.
- `connected` means an existing component has current observations; it is not
  target-release proof.
- `degraded` stops progression and requires inspection.
- `not_run` means no admitted target evidence exists.
- `evidence_admitted` means a fixed normalized report is intact, current and bound;
  it is not independent proof or release approval.
- `evidence_failed` means a complete normalized target report contains a failure.
- `not_authorized` means the required explicit operation was not authorized.

This increment deliberately has no `passed` gate state. The target admission schema
can represent normalized local or future target output, but the current repository
contains synthetic evidence only. EA compile/artifact identity, a bounded Demo
open-to-close round trip, broker-side SL, target restart and network-loss tests,
alerts, backup/restore, burn-in and explicit authorization remain `NOT RUN`. See the
[target evidence runbook](target-evidence.md).

## Local verification

```bash
.venv/bin/python -m pytest -q tests/test_target_evidence.py tests/test_demo_readiness.py tests/test_api_safety.py tests/test_owner_auth.py
npx -y -p node@24.21.0 npm run test --workspace @sochron1k/web
```

These checks use local synthetic state only. They make no hosted, broker or target
write and cannot clear any actual Demo release gate.
