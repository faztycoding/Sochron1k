import { periods, type Timeframe } from "../chart-api";
import { historyQuota, type HistoryView } from "../history-api";
import { identity } from "./chart-fixture";

export const historyIdentity = { ...identity, executor_id: "synthetic-executor", margin_mode: "retail_hedging" as const };
export const iso = (seconds: number) => new Date(seconds * 1000).toISOString();
export function historyFixture(timeframe: Timeframe = "M5", start = 1789516800, count = 20): HistoryView {
  const period = periods[timeframe];
  return { state: "available", archive_id: "00000000-0000-4000-8000-000000000007", identity: { ...historyIdentity },
    source: "mt5-copyrates", through_receipt: 42, timeframe, execution_ready: false,
    database_bytes: 32768, quota_bytes: historyQuota, storage: "normal", gaps: [],
    bars: Array.from({ length: count }, (_, index) => ({ time_server_s: start + index * period,
      open_time_utc: iso(start + index * period - 7200), closed: true,
      open: "2500.10", high: "2500.90", low: "2500.00", close: "2500.20", tick_volume: 50, spread_points: 20,
      confirmed_by_server_s: start + (index + 1) * period, first_receipt: 40,
      source_observed_at: iso(start + count * period - 7200), first_received_at: iso(start + count * period - 7200 + 1),
      terminal_build: 5430, price_basis: "bid", digits: 2, tick_size: "0.01", broker_utc_offset_seconds: 7200,
    })),
  };
}
export function disabledHistory(timeframe: Timeframe = "M5"): HistoryView {
  return { ...historyFixture(timeframe), state: "disabled", archive_id: null, identity: null,
    bars: [], through_receipt: 0, database_bytes: 0 };
}
