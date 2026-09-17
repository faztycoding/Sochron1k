import type { Telemetry } from "./owner-api";

export const periods = { M1: 60, M5: 300, M15: 900, H1: 3600 } as const;
export type Timeframe = keyof typeof periods;
export type AccountIdentity = NonNullable<Telemetry["observation"]>["frame"]["identity"];
export type ChartBar = {
  time_server_s: number; open_time_utc: string; closed: boolean;
  open: string; high: string; low: string; close: string;
  tick_volume: number; spread_points: number;
};
export type ChartGap = { after_open_time_utc: string; before_open_time_utc: string;
  missing_intervals: number; classification: "unclassified" };
export type ChartObservation = {
  source: "mt5-copyrates"; identity: AccountIdentity; timeframe: Timeframe;
  price_basis: "bid" | "last"; sequence: number; terminal_build: number;
  digits: number; tick_size: string; broker_utc_offset_seconds: number;
  observed_at: string; received_time_utc: string; bars: ChartBar[]; gaps: ChartGap[];
};
export type ChartView = {
  state: "disabled" | "awaiting_snapshot" | "ready" | "stale" | "rejected";
  snapshot_age_seconds: number | null; latest_bar_age_seconds: number | null;
  feed_status: Telemetry["status"]; observation: ChartObservation | null; execution_ready: false;
};
function record(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("Invalid chart");
  return value as Record<string, unknown>;
}
function integer(value: unknown, minimum: number, maximum = Number.MAX_SAFE_INTEGER): value is number {
  return typeof value === "number" && Number.isSafeInteger(value) && value >= minimum && value <= maximum;
}
function utc(value: unknown): number {
  if (typeof value !== "string" || value.length > 40 || !/(Z|\+00:00)$/.test(value)) throw new Error("Invalid UTC");
  const time = Date.parse(value) / 1000;
  if (!Number.isFinite(time) || time <= 0 || time > 4102444800) throw new Error("Invalid UTC");
  return time;
}
// Exact fixed-point validation, independent of binary floating-point rendering.
export function priceUnits(value: unknown): bigint {
  if (typeof value !== "string" || value.length > 40) throw new Error("Invalid price");
  const match = /^(\d{1,24})(?:\.(\d{1,24}))?(?:[Ee]([+-]?\d{1,2}))?$/.exec(value);
  if (!match) throw new Error("Invalid price");
  const fraction = match[2] ?? "";
  const shift = 10 + Number(match[3] ?? 0) - fraction.length;
  if (Math.abs(shift) > 34) throw new Error("Invalid price");
  let units = BigInt(match[1] + fraction);
  if (shift < 0) {
    const divisor = 10n ** BigInt(-shift);
    if (units % divisor) throw new Error("Invalid precision");
    units /= divisor;
  } else units *= 10n ** BigInt(shift);
  if (units <= 0n || units >= 10n ** 24n) throw new Error("Invalid price range");
  return units;
}
export function parseChart(value: unknown, timeframe: Timeframe, identity: AccountIdentity): ChartView {
  const data = record(value), feed = record(data.feed_status);
  if (!["disabled", "awaiting_snapshot", "ready", "stale", "rejected"].includes(String(data.state)) ||
      data.execution_ready !== false || feed.execution_ready !== false || feed.auto_trading_enabled !== false ||
      !["disabled", "awaiting_snapshot", "connected", "stale", "rejected"].includes(String(feed.state)) ||
      typeof feed.price_fresh !== "boolean" || typeof feed.heartbeat_fresh !== "boolean") throw new Error("Invalid chart state");
  for (const age of [data.snapshot_age_seconds, data.latest_bar_age_seconds, feed.price_age_seconds, feed.heartbeat_age_seconds]) {
    if (age !== null && (typeof age !== "number" || !Number.isFinite(age) || age < 0)) throw new Error("Invalid age");
  }
  if (data.observation === null) {
    if (["ready", "stale"].includes(String(data.state))) throw new Error("Missing chart");
    return data as unknown as ChartView;
  }
  if (["disabled", "awaiting_snapshot"].includes(String(data.state))) throw new Error("Unexpected chart");
  const o = record(data.observation), account = record(o.identity);
  if (o.source !== "mt5-copyrates" || o.timeframe !== timeframe || !["bid", "last"].includes(String(o.price_basis)) ||
      !Object.entries(identity).every(([key, item]) => account[key] === item) ||
      !integer(o.sequence, 1) || !integer(o.terminal_build, 1) || !integer(o.digits, 0, 10) ||
      !integer(o.broker_utc_offset_seconds, -50400, 50400)) throw new Error("Invalid chart identity");
  const tick = priceUnits(o.tick_size), observed = utc(o.observed_at), received = utc(o.received_time_utc);
  if (received < observed) throw new Error("Invalid receive time");
  if (!Array.isArray(o.bars) || o.bars.length < 2 || o.bars.length > 240 || !Array.isArray(o.gaps)) throw new Error("Invalid window");
  let previous = 0;
  const expectedGaps: Array<[number, number, number]> = [];
  for (const [index, raw] of o.bars.entries()) {
    const bar = record(raw), time = utc(bar.open_time_utc);
    if (!integer(bar.time_server_s, 1, 4102444800) || bar.time_server_s % periods[timeframe] ||
        time !== bar.time_server_s - o.broker_utc_offset_seconds || time <= previous || time > observed ||
        bar.closed !== (index < o.bars.length - 1) || !integer(bar.tick_volume, 1) ||
        !integer(bar.spread_points, 0, 2147483647)) throw new Error("Invalid bar metadata");
    const [open, high, low, close] = [bar.open, bar.high, bar.low, bar.close].map(priceUnits);
    if (low > open || low > close || high < open || high < close ||
        [open, high, low, close].some(p => p % tick || p % (10n ** BigInt(10 - (o.digits as number))))) throw new Error("Invalid OHLC");
    if (previous && time - previous > periods[timeframe]) expectedGaps.push([previous, time, (time - previous) / periods[timeframe] - 1]);
    previous = time;
  }
  if (o.gaps.length !== expectedGaps.length) throw new Error("Missing gaps");
  o.gaps.forEach((raw, index) => {
    const gap = record(raw), expected = expectedGaps[index];
    if (gap.classification !== "unclassified" || utc(gap.after_open_time_utc) !== expected[0] ||
        utc(gap.before_open_time_utc) !== expected[1] || gap.missing_intervals !== expected[2]) throw new Error("Invalid gap");
  });
  if (data.state === "ready" && (data.snapshot_age_seconds === null || data.latest_bar_age_seconds === null ||
      feed.state !== "connected" || !feed.price_fresh || !feed.heartbeat_fresh ||
      feed.price_age_seconds === null || feed.heartbeat_age_seconds === null)) throw new Error("Invalid ready state");
  return data as unknown as ChartView;
}
export function chartIsFresh(data: ChartView, elapsed: number): boolean {
  return data.state === "ready" && data.observation !== null && data.snapshot_age_seconds !== null &&
    data.latest_bar_age_seconds !== null && data.snapshot_age_seconds + elapsed <= 15 &&
    data.latest_bar_age_seconds + elapsed < periods[data.observation.timeframe] &&
    data.feed_status.state === "connected" && data.feed_status.price_fresh && data.feed_status.heartbeat_fresh &&
    data.feed_status.price_age_seconds !== null && data.feed_status.heartbeat_age_seconds !== null &&
    data.feed_status.price_age_seconds + elapsed <= 5 && data.feed_status.heartbeat_age_seconds + elapsed <= 5;
}
export function canvasCanPreservePrices(observation: ChartObservation): boolean {
  const tick = Number(observation.tick_size);
  try {
    return observation.bars.every(bar => [bar.open, bar.high, bar.low, bar.close].every(value => {
      const number = Number(value);
      return priceUnits(number.toFixed(observation.digits)) === priceUnits(value) && number + tick > number && number - tick < number;
    }));
  } catch { return false; }
}
