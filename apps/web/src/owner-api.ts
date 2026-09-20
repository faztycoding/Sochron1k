export type AuthConfig = { enabled: false } | {
  enabled: true; supabase_url: string; public_key: string;
};
export type Telemetry = {
  status: {
    state: "disabled" | "awaiting_snapshot" | "connected" | "stale" | "rejected";
    heartbeat_fresh: boolean; price_fresh: boolean;
    heartbeat_age_seconds: number | null; price_age_seconds: number | null;
    auto_trading_enabled: false; execution_ready: false;
  };
  observation: null | {
    event_time_utc: string; received_time_utc: string;
    frame: {
      trade_mode: "demo"; equity: string; balance: string; free_margin: string;
      bid: string; ask: string;
      identity: { account_ref: string; server: string; currency: string; symbol: string };
    };
  };
};

function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("Invalid data");
  return value as Record<string, unknown>;
}
function text(value: unknown): value is string {
  return typeof value === "string" && value.length > 0 && value.length <= 256;
}
function decimal(value: unknown): value is string {
  return text(value) && /^-?\d+(\.\d+)?$/.test(value) && Number.isFinite(Number(value));
}

export function parseConfig(value: unknown): AuthConfig {
  const config = object(value);
  if (config.enabled === false) return { enabled: false };
  if (config.enabled !== true || !text(config.supabase_url) || typeof config.public_key !== "string") {
    throw new Error("Invalid Auth configuration");
  }
  const url = new URL(config.supabase_url);
  if ((url.protocol !== "https:" && !(url.protocol === "http:" &&
      ["127.0.0.1", "localhost", "[::1]"].includes(url.hostname))) ||
      url.username || url.password || url.search || url.hash || url.pathname !== "/") {
    throw new Error("Invalid Auth origin");
  }
  let permitted = /^sb_publishable_[A-Za-z0-9_-]{16,256}$/.test(config.public_key);
  if (!permitted && config.public_key.length <= 8192) {
    try {
      const payload = config.public_key.split(".")[1];
      permitted = object(JSON.parse(atob(payload.replace(/-/g, "+").replace(/_/g, "/")))).role === "anon";
    } catch { permitted = false; }
  }
  if (!permitted) throw new Error("Invalid public key");
  return { enabled: true, supabase_url: url.origin, public_key: config.public_key };
}

export function parseTelemetry(value: unknown): Telemetry {
  const data = object(value);
  const status = object(data.status);
  if (!["disabled", "awaiting_snapshot", "connected", "stale", "rejected"].includes(String(status.state)) ||
      typeof status.heartbeat_fresh !== "boolean" || typeof status.price_fresh !== "boolean" ||
      status.auto_trading_enabled !== false || status.execution_ready !== false) throw new Error("Invalid status");
  for (const field of ["price_age_seconds", "heartbeat_age_seconds"]) {
    const age = status[field];
    if (age !== null && (typeof age !== "number" || !Number.isFinite(age) || age < 0)) throw new Error("Invalid age");
  }
  if (data.observation !== null) {
    if (status.state === "disabled" || status.state === "awaiting_snapshot") throw new Error("Unexpected observation");
    const observation = object(data.observation);
    for (const key of ["event_time_utc", "received_time_utc"]) {
      if (!text(observation[key]) || !/(Z|\+00:00)$/.test(observation[key]) ||
          !Number.isFinite(Date.parse(observation[key]))) throw new Error("Invalid UTC time");
    }
    const frame = object(observation.frame);
    const identity = object(frame.identity);
    if (frame.trade_mode !== "demo" || !["account_ref", "server", "currency", "symbol"].every(k => text(identity[k]))) {
      throw new Error("Invalid Demo identity");
    }
    if (!["equity", "balance", "free_margin", "bid", "ask"].every(k => decimal(frame[k])) ||
        Number(frame.bid) <= 0 || Number(frame.ask) < Number(frame.bid)) throw new Error("Invalid values");
  } else if (status.state === "connected") throw new Error("Missing observation");
  return data as unknown as Telemetry;
}

export class ApiError extends Error {
  constructor(readonly status: number) { super("API request failed"); }
}
async function responseJSON(response: Response, maxBytes: number): Promise<unknown> {
  if (!response.ok) throw new ApiError(response.status);
  const reader = response.body?.getReader();
  if (!reader) throw new Error("Missing response");
  let bytes = 0;
  let body = "";
  const decoder = new TextDecoder();
  try {
    while (true) {
      const chunk = await reader.read();
      if (chunk.done) break;
      bytes += chunk.value.byteLength;
      if (bytes > maxBytes) throw new Error("Response too large");
      body += decoder.decode(chunk.value, { stream: true });
    }
    return JSON.parse(body + decoder.decode());
  } finally { await reader.cancel(); }
}

export async function readJSON(path: string, signal: AbortSignal, token?: string, maxBytes = 65536): Promise<unknown> {
  return responseJSON(await fetch(path, {
    signal: AbortSignal.any([signal, AbortSignal.timeout(6000)]), cache: "no-store",
    credentials: "omit", redirect: "error",
    headers: { Accept: "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
  }), maxBytes);
}

export async function postJSON(
  path: string, signal: AbortSignal, token: string, idempotencyKey: string, maxBytes = 65536,
): Promise<unknown> {
  return responseJSON(await fetch(path, {
    method: "POST", signal: AbortSignal.any([signal, AbortSignal.timeout(6000)]), cache: "no-store",
    credentials: "omit", redirect: "error",
    headers: { Accept: "application/json", Authorization: `Bearer ${token}`, "Idempotency-Key": idempotencyKey },
  }), maxBytes);
}

export function quoteIsFresh(data: Telemetry, elapsedSeconds: number): boolean {
  return data.status.state === "connected" && data.status.price_fresh && data.status.heartbeat_fresh &&
    data.status.price_age_seconds !== null && data.status.heartbeat_age_seconds !== null &&
    data.status.price_age_seconds + elapsedSeconds <= 5 &&
    data.status.heartbeat_age_seconds + elapsedSeconds <= 5;
}
