# ADR-010 Internal Python delivery artifact

2026-09-17. Local implementation decision under SCN-008 AC-07; not a release
approval, hosted enablement or change to the target Compose architecture.

## Decision

Build one private `sochron1k` wheel containing the existing `sochron1k` and
`sochron_worker` packages. The worker already imports API-owned domain validators;
shipping both avoids source-relative PYTHONPATH, duplicate schemas or an unnecessary
shared-package extraction. Their source directories and runtime authorities remain
unchanged. No API startup is imported by the worker and no broker operation is added.

Use Hatchling 1.32.0, pinned in build-system and a dedicated locked build group.
Build using the locked environment with `--no-build-isolation`, not an unpinned
transitive build resolver. Explicit source inclusion ships Python module files
only. Verify the wheel's complete file set and bytes, then rebuild from the sdist.
Export existing production dependencies with hashes for isolated installation;
build/dev tools are not runtime dependencies. Keep `tool.uv.package=false` so
existing source-development and API-image dependency-only sync behavior is unchanged.

The `sochron-sync` console entry point and module invocation share signal setup
and the same CLI. Neither importing nor installing the package initializes state,
loads credentials, opens a destination or starts a service. Normal operator run
still requires an explicit private config and initialized journal.

## Consequences and alternatives

This is an internal artifact, not a PyPI publication. Version alone is insufficient
to identify a candidate while the project remains 0.1.0: retain source revision,
lockfile and artifact SHA-256 together. The wheel includes API dependencies because
it is one application artifact; a separate slim worker distribution is not needed
yet. A wheel does not include a Python interpreter or OS dependencies.

The current worker is POSIX-only (flock and Unix ownership). A generic wheel tag
does not certify Windows support. The MT5 Windows/Wine executor is a different
boundary. [ADR-011](ADR-011-worker-container.md) now supplies opt-in Linux container
packaging and local replacement evidence. Fixed-runtime admission, consistent
backup/restore and target-host gates remain required; local macOS installation
does not establish them. No automatic restart may bypass retry-budget review.

## References

- [Hatch file selection and path rewriting](https://hatch.pypa.io/latest/config/build/)
- [uv build workflow](https://docs.astral.sh/uv/guides/package/)
- [uv project packaging and entry points](https://docs.astral.sh/uv/concepts/projects/config/)
