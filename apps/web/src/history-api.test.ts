import { describe, expect, it } from "vitest";
import { historyPath, historyQuota, parseHistory, type HistoryRequest, type HistoryView } from "./history-api";
import { disabledHistory, historyFixture, historyIdentity, iso } from "./test/history-fixture";
const request: HistoryRequest = { timeframe: "M5", after: 0, identity: historyIdentity };
describe("SCN-007 owner history parser", () => {
  it.each(["M1", "M5", "M15", "H1"] as const)("accepts exact closed %s rows without live telemetry", timeframe => {
    const data = historyFixture(timeframe);
    expect(parseHistory(data, { timeframe, after: 0, identity: null })).toBe(data);
  });
  it("validates disabled and empty archives", () => {
    expect(parseHistory(disabledHistory(), request).state).toBe("disabled");
    const data = historyFixture(); data.bars = []; data.through_receipt = 0;
    expect(parseHistory(data, request).bars).toEqual([]);
  });
  const invalid: Array<[string, (v: HistoryView) => void]> = [
    ["wrong timeframe", v => { v.timeframe = "M1"; }],
    ["wrong identity", v => { v.identity = { ...historyIdentity, account_ref: "other" }; }],
    ["missing identity field", v => { delete (v.identity as Partial<typeof historyIdentity>).executor_id; }],
    ["bad archive ID", v => { v.archive_id = "not-an-archive"; }],
    ["wrong margin mode", v => { Object.assign(v.identity!, { margin_mode: "hedging" }); }],
    ["invalid currency", v => { v.identity!.currency = "not a currency"; }],
    ["oversized window", v => { v.bars.push(v.bars[0]); }],
    ["receipt beyond snapshot", v => { v.bars[0].first_receipt = 43; }],
    ["zero receipt", v => { v.bars[0].first_receipt = 0; }],
    ["forming bar", v => { Object.assign(v.bars[0], { closed: false }); }],
    ["time mapping", v => { v.bars[0].open_time_utc = iso(v.bars[0].time_server_s); }],
    ["invalid calendar", v => { v.bars[0].first_received_at = "2026-02-30T00:00:00Z"; }],
    ["non-UTC", v => { v.bars[0].first_received_at = "2026-09-17T00:00:00+07:00"; }],
    ["duplicate bar", v => { v.bars[1] = v.bars[0]; }],
    ["misaligned timestamp", v => { v.bars[0].time_server_s++; }],
    ["no later closure", v => { v.bars[0].confirmed_by_server_s = v.bars[0].time_server_s; }],
    ["future closure", v => { v.bars[0].confirmed_by_server_s += 86400; }],
    ["microsecond reversal", v => { v.bars[0].source_observed_at = "2026-09-18T00:00:00.000002Z"; v.bars[0].first_received_at = "2026-09-18T00:00:00.000001Z"; }],
    ["offset switch", v => { v.bars[1].broker_utc_offset_seconds = 0; v.bars[1].open_time_utc = iso(v.bars[1].time_server_s); }],
    ["invalid decimal", v => { v.bars[0].open = "NaN"; }],
    ["off tick grid", v => { v.bars[0].open = "2500.105"; }],
    ["OHLC range", v => { v.bars[0].low = "2600"; }],
    ["unsafe volume", v => { v.bars[0].tick_volume = Number.MAX_SAFE_INTEGER + 1; }],
    ["missing gaps", v => { v.bars.splice(2, 1); }],
    ["incorrect warning", v => { v.storage = "warning_85"; }],
    ["wrong quota", v => { v.quota_bytes = 1; }],
    ["too large storage", v => { v.database_bytes = historyQuota + 1; }],
    ["disabled leaks bars", v => { v.state = "disabled"; }],
    ["execution ready", v => { Object.assign(v, { execution_ready: true }); }],
  ];
  it.each(invalid)("rejects %s", (_, change) => {
    const data = historyFixture(); change(data);
    expect(() => parseHistory(data, request)).toThrow();
  });
  it("pins archive, watermark, identity and offset across pages", () => {
    const first = historyFixture(), last = first.bars.at(-1)!;
    const next: HistoryRequest = { ...request, after: last.time_server_s, previousUTC: last.open_time_utc,
      pin: { archive: first.archive_id!, receipt: 42, identity: historyIdentity, offset: 7200 } };
    const data = historyFixture("M5", last.time_server_s + 300);
    expect(parseHistory(data, next)).toBe(data);
    expect(historyPath(next)).toContain("through_receipt=42");
    expect(historyPath(next)).toContain(`archive_id=${first.archive_id}`);
    for (const change of [(v: HistoryView) => { v.through_receipt++; },
      (v: HistoryView) => { v.archive_id = "00000000-0000-4000-8000-000000000008"; }]) {
      const changed = structuredClone(data); change(changed);
      expect(() => parseHistory(changed, next)).toThrow();
    }
    expect(() => parseHistory(disabledHistory(), next)).toThrow();
    expect(() => parseHistory(data, { ...next, pin: { ...next.pin!, offset: 0 } })).toThrow();
    expect(() => parseHistory(data, { ...next, identity: null, pin: { ...next.pin!, identity: { ...historyIdentity, executor_id: "other" } } })).toThrow();
  });
  it("preserves page-boundary gaps and rejects unexplained or altered gaps", () => {
    const data = historyFixture(), first = data.bars[0];
    const cursor = { after: first.time_server_s - 600, previousUTC: iso(first.time_server_s - 7800) };
    data.gaps = [{ after_open_time_utc: cursor.previousUTC, before_open_time_utc: first.open_time_utc, missing_intervals: 1, classification: "unclassified" }];
    expect(parseHistory(data, { ...request, ...cursor }).gaps).toHaveLength(1);
    data.gaps[0].missing_intervals = 2;
    expect(() => parseHistory(data, { ...request, ...cursor })).toThrow();
  });
  it("keeps decimal values beyond canvas precision exact", () => {
    const data = historyFixture();
    for (const bar of data.bars) Object.assign(bar, { open: "9999999999999.1234567890", high: "9999999999999.1234567890",
      low: "9999999999999.1234567890", close: "9999999999999.1234567890", digits: 10, tick_size: "0.0000000001" });
    expect(parseHistory(data, request).bars[0].close).toBe("9999999999999.1234567890");
  });
  it("matches the API contract when tick size is finer than displayed digits", () => {
    const data = historyFixture(); for (const bar of data.bars) bar.tick_size = "0.001";
    expect(parseHistory(data, request).bars).toHaveLength(20);
    data.bars[0].open = "2500.101";
    expect(() => parseHistory(data, request)).toThrow("Invalid archived OHLC");
  });
  it.each([0.7, 0.85])("validates quota warning at %s", threshold => {
    const data = historyFixture(); data.database_bytes = Math.ceil(historyQuota * threshold);
    data.storage = threshold === 0.7 ? "warning_70" : "warning_85";
    expect(parseHistory(data, request).storage).toBe(data.storage);
  });
});
