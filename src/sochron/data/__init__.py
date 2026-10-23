"""Market-data packages (docs/architecture.md section 8).

sochron.data.snapshot holds pure checks and builders for M1 snapshots. sochron.data.acquire (later,
acquisition host only) is never imported from here, so importing sochron.data runs no code.
"""
