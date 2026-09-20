# ADR-039: Admit normalized target evidence without granting release authority

- Status: accepted for local implementation; target verification pending
- Date: 2026-09-20
- Contract: SCN-036

## Context

The Demo readiness ledger names target compilation, broker round trip and recovery
as required gates, but previously had no boundary through which reviewed target
results could be represented. Treating a screenshot, arbitrary log or manually
edited `passed=true` value as a gate result would confuse operator input with
evidence and could make the dashboard look release-ready without a reproducible
source, artifact or owner-decision binding.

The repository has no selected VPS, MT5 terminal, Demo credential or authority to
place a broker order. A local implementation therefore must accept no external
side effect and must not claim that a synthetic fixture happened on a target.

## Decision

Add a disabled-by-default, query-only reader for one private manifest and exactly
three normalized reports: `target_artifact`, `broker_round_trip` and
`recovery_observability`. The configuration pins the reviewed source revision,
target artifact hash, owner-decision revision/time, manifest path and freshness
limit. The manifest pins the ordered report names, byte lengths and SHA-256
digests; every report repeats the same bindings and uses a fixed ordered check set.

Private files must be canonical, owner-owned, owner-private, bounded, regular and
single-link. Reads fail closed on symlinks, hard links, replacement, permission
drift, duplicate JSON keys, digest drift, invalid time or incomplete check claims.
The API exposes only redacted hashes, UTC times and fixed states through the
owner-authenticated `GET /owner/target-evidence` route.

`PASS` maps to `evidence_admitted`, not `passed` or `release_ready`. Admission means
only that the normalized bundle is intact, current and internally coherent. The
read model cannot create evidence, authorize a round trip, operate MT5, release a
halt or enable Auto Trading. Operational authorization remains a separate final
gate, and all safety flags remain literal false.

## Consequences

- The UI can show the exact API position and distinguish missing, admitted, failed,
  stale and invalid target evidence without exposing paths or target identifiers.
- A target verifier can be implemented later without giving it API or UI authority;
  it must atomically produce the fixed normalized bundle from retained raw evidence.
- A valid bundle is still not independent proof that the underlying event occurred.
  Target execution, verifier integrity, broker confirmation, fault tests and owner
  authorization must be reviewed separately before any Demo release decision.
- Base Compose passes only an optional config path. It mounts no target evidence,
  starts no verifier and remains inert by default.
