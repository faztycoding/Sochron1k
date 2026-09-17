import { periods, priceUnits, type AccountIdentity, type ChartBar, type ChartGap, type Timeframe } from "./chart-api";

export const historyPageSize = 20;
export const historyQuota = 128 * 1024 * 1024;
export type HistoryIdentity = AccountIdentity & { executor_id: string; margin_mode: "retail_netting" | "retail_hedging" | "exchange" };
export type ArchivedBar = ChartBar & {
  closed: true; confirmed_by_server_s: number; first_receipt: number;
  first_received_at: string; source_observed_at: string; terminal_build: number;
  price_basis: "bid" | "last"; digits: number; tick_size: string; broker_utc_offset_seconds: number;
};
export type HistoryView = {
  state: "disabled" | "available"; archive_id: string | null; identity: HistoryIdentity | null;
  source: "mt5-copyrates"; through_receipt: number; timeframe: Timeframe;
  bars: ArchivedBar[]; gaps: ChartGap[]; database_bytes: number; quota_bytes: number;
  storage: "normal" | "warning_70" | "warning_85"; execution_ready: false;
};
export type HistoryCursor = { after: number; previousUTC?: string };
export type HistoryPin = { archive: string; receipt: number; identity: HistoryIdentity; offset?: number };
export type HistoryRequest = HistoryCursor & { timeframe: Timeframe; pin?: HistoryPin; identity: AccountIdentity | null };
function record(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("Invalid history");
  return value as Record<string, unknown>;
}
function integer(value: unknown, min: number, max = Number.MAX_SAFE_INTEGER): value is number {
  return typeof value === "number" && Number.isSafeInteger(value) && value >= min && value <= max;
}
// Preserve microseconds when checking provenance; Date alone silently truncates them.
function utc(value: unknown): bigint {
  if (typeof value !== "string") throw new Error("Invalid history UTC");
  const match = /^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d{1,6}))?(?:Z|\+00:00)$/.exec(value);
  if (!match) throw new Error("Invalid history UTC");
  const ms = Date.parse(`${match[1]}Z`);
  if (!Number.isFinite(ms) || ms <= 0 || ms > 4102444800000 ||
      new Date(ms).toISOString().slice(0, 19) !== match[1]) throw new Error("Invalid history UTC");
  return BigInt(ms) * 1000n + BigInt((match[2] ?? "").padEnd(6, "0"));
}
export function historyPath(request: HistoryRequest): string {
  const query = new URLSearchParams({ limit: String(historyPageSize), after_server_s: String(request.after) });
  if (request.pin) {
    query.set("archive_id", request.pin.archive);
    query.set("through_receipt", String(request.pin.receipt));
  }
  return `/api/owner/history/${request.timeframe}?${query}`;
}
export function parseHistory(value: unknown, request: HistoryRequest): HistoryView {
  const data = record(value), period = periods[request.timeframe];
  if (!["disabled", "available"].includes(String(data.state)) || data.timeframe !== request.timeframe ||
      data.source !== "mt5-copyrates" || data.execution_ready !== false || !integer(data.through_receipt, 0) ||
      !integer(data.database_bytes, 0, historyQuota) || data.quota_bytes !== historyQuota ||
      !Array.isArray(data.bars) || data.bars.length > historyPageSize || !Array.isArray(data.gaps)) throw new Error("Invalid history state");
  const expectedStorage = data.database_bytes >= historyQuota * 0.85 ? "warning_85" :
    data.database_bytes >= historyQuota * 0.70 ? "warning_70" : "normal";
  if (data.storage !== expectedStorage) throw new Error("Invalid history storage");
  if (data.state === "disabled") {
    if (request.pin || data.archive_id !== null || data.identity !== null || data.through_receipt !== 0 ||
        data.bars.length || data.gaps.length || data.database_bytes !== 0) throw new Error("Invalid disabled history");
    return data as unknown as HistoryView;
  }
  const identity = record(data.identity);
  if (typeof data.archive_id !== "string" || !/^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/.test(data.archive_id) ||
      !["executor_id", "account_ref", "server", "currency", "symbol"].every(key =>
        typeof identity[key] === "string" && identity[key].length > 0 && identity[key].length <= 128 && !/[\u0000-\u001f\u007f]/.test(identity[key])) ||
      !/^[A-Z]{3,8}$/.test(String(identity.currency)) || !/^\S{1,32}$/.test(String(identity.symbol)) ||
      !["retail_netting", "retail_hedging", "exchange"].includes(String(identity.margin_mode))) throw new Error("Invalid history identity");
  for (const expected of [request.identity, request.pin?.identity]) {
    if (expected && !Object.entries(expected).every(([key, item]) => identity[key] === item)) throw new Error("History identity changed");
  }
  if (request.pin && (data.archive_id !== request.pin.archive || data.through_receipt !== request.pin.receipt)) throw new Error("History snapshot changed");
  let previousServer = request.after;
  let previousUTC = request.previousUTC ? utc(request.previousUTC) : null;
  let offset = request.pin?.offset;
  const gaps: Array<[bigint, bigint, number]> = [];
  for (const raw of data.bars) {
    const bar = record(raw), time = utc(bar.open_time_utc), observed = utc(bar.source_observed_at), received = utc(bar.first_received_at);
    if (!integer(bar.time_server_s, 1, 4102444800) || bar.time_server_s % period || bar.time_server_s <= previousServer ||
        !integer(bar.broker_utc_offset_seconds, -50400, 50400) || bar.broker_utc_offset_seconds % 60 ||
        time !== BigInt(bar.time_server_s - bar.broker_utc_offset_seconds) * 1000000n || bar.closed !== true ||
        !integer(bar.confirmed_by_server_s, bar.time_server_s + period, 4102444800) || bar.confirmed_by_server_s % period ||
        BigInt(bar.confirmed_by_server_s - bar.broker_utc_offset_seconds) * 1000000n > observed || received < observed ||
        !integer(bar.first_receipt, 1, data.through_receipt) || !integer(bar.terminal_build, 1) ||
        !integer(bar.tick_volume, 1) || !integer(bar.spread_points, 0, 2147483647) ||
        !integer(bar.digits, 0, 10) || !["bid", "last"].includes(String(bar.price_basis))) throw new Error("Invalid archived bar");
    offset ??= bar.broker_utc_offset_seconds;
    if (offset !== bar.broker_utc_offset_seconds || (previousUTC !== null &&
        previousUTC !== BigInt(previousServer - offset) * 1000000n)) throw new Error("History offset changed");
    const tick = priceUnits(bar.tick_size), quantum = 10n ** BigInt(10 - bar.digits);
    const [open, high, low, close] = [bar.open, bar.high, bar.low, bar.close].map(priceUnits);
    if (low > open || low > close || high < open || high < close ||
        [open, high, low, close].some(p => p % tick || p % quantum)) throw new Error("Invalid archived OHLC");
    if (previousUTC !== null && bar.time_server_s - previousServer > period)
      gaps.push([previousUTC, time, (bar.time_server_s - previousServer) / period - 1]);
    previousServer = bar.time_server_s; previousUTC = time;
  }
  if (data.gaps.length !== gaps.length) throw new Error("Missing history gaps");
  data.gaps.forEach((raw, index) => {
    const gap = record(raw), expected = gaps[index];
    if (gap.classification !== "unclassified" || utc(gap.after_open_time_utc) !== expected[0] ||
        utc(gap.before_open_time_utc) !== expected[1] || gap.missing_intervals !== expected[2]) throw new Error("Invalid history gap");
  });
  return data as unknown as HistoryView;
}
