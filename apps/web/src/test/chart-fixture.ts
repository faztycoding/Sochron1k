import { periods, type ChartView, type Timeframe } from "../chart-api";
export const identity = { account_ref: "synthetic-account", server: "Synthetic-Demo", symbol: "XAUUSD.fixture", currency: "USD" };
export function chartFixture(timeframe: Timeframe = "M5", gap = false): ChartView {
  const period = periods[timeframe], last = 1789603200;
  const iso = (value: number) => new Date(value * 1000).toISOString();
  const starts = [last - period * (gap ? 2 : 1), last];
  return {
    state: "ready", snapshot_age_seconds: 0, latest_bar_age_seconds: 1, execution_ready: false,
    feed_status: { state: "connected", price_fresh: true, heartbeat_fresh: true, price_age_seconds: 0,
      heartbeat_age_seconds: 0, execution_ready: false, auto_trading_enabled: false },
    observation: { source: "mt5-copyrates", identity, timeframe, price_basis: "bid", sequence: 1, terminal_build: 5430,
      digits: 2, tick_size: "0.01", broker_utc_offset_seconds: 7200, observed_at: iso(last - 7200 + 1), received_time_utc: iso(last - 7200 + 1),
      bars: starts.map((start, index) => ({ time_server_s: start, open_time_utc: iso(start - 7200), closed: index === 0,
        open: "2500.10", high: "2500.90", low: "2500.00", close: "2500.20", tick_volume: 10, spread_points: 20 })),
      gaps: gap ? [{ after_open_time_utc: iso(starts[0] - 7200), before_open_time_utc: iso(last - 7200), missing_intervals: 1, classification: "unclassified" }] : [],
    },
  };
}
