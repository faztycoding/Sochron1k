# ADR-034: Demo readiness is a redacted gate ledger

## Status

Accepted for the Demo monitoring surface.

## Context

The dashboard exposed a truthful global lock but represented four release gaps as
hard-coded Thai strings. That list could not distinguish an owner decision from a
loaded configuration, live source observation or target-host evidence, and it did
not identify which browser API would eventually populate each surface.

The repository already has authoritative component status objects. It does not
have a signed target-evidence store, a release-admission service or authorization
for a broker round trip. Treating configuration presence as readiness would
violate the Demo safety boundary.

## Decision

Add one public, no-store `/ui/demo-readiness` projection. Its fixed gate IDs and
safe source/action codes are the compatibility contract; the web client owns the
Thai presentation text. Runtime gates are derived only from existing component
state. Target artifact, round-trip, recovery and operational-authorization gates
remain explicitly unrun or unauthorized.

Owner choices are admitted through a versioned private JSON file. The file is
non-secret and intentionally omits credentials and account references, but is
still protected as owner-only operational metadata. Its values never cross the
public readiness boundary; only the fact that the complete decision record was
validated is exposed as `recorded`.

The endpoint has no positive release state in this increment. All safety booleans
are literal false except `demo_only`, which is literal true. A later target
evidence reader will need its own contract, provenance, expiry and fault tests
before any gate can become passed.

## Consequences

- Operators can see exactly which integration surface and source class blocks
  each dashboard area without exposing private target details.
- The UI can fail closed while still explaining all expected gates and routes.
- Configuration, connectivity and target evidence remain distinct states.
- This model cannot be reused as an execution preflight or broker authorization.
- A real release gate still requires compiled artifact identity, actual target
  fault evidence, bounded broker round-trip evidence and explicit authorization.

## Rejected alternatives

- **Keep prose in React:** rejected because it drifts from runtime state and has no
  machine-checkable contract.
- **Return decision values to the browser:** rejected because the dashboard needs
  state and route position, not owner or broker metadata.
- **Mark configured components ready:** rejected because configuration is not live
  evidence and cannot clear target gates.
- **Add manual pass booleans:** rejected because unproven assertions are not
  revision-bound evidence and could silently enable false readiness.
