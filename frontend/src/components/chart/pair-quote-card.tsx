"use client";

import { useEffect, useRef, useState } from "react";
import { Wifi, WifiOff, Circle } from "lucide-react";
import type { PriceData, PairPerformance } from "@/lib/api";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

// Currency metadata: flag + Thai name
const PAIR_META: Record<string, { flagLeft: string; flagRight: string; thai: string }> = {
  "EUR/USD": { flagLeft: "🇪🇺", flagRight: "🇺🇸", thai: "ยูโร / ดอลลาร์สหรัฐฯ" },
  "USD/JPY": { flagLeft: "🇺🇸", flagRight: "🇯🇵", thai: "ดอลลาร์สหรัฐฯ / เยนญี่ปุ่น" },
  "EUR/JPY": { flagLeft: "🇪🇺", flagRight: "🇯🇵", thai: "ยูโร / เยนญี่ปุ่น" },
  "GBP/USD": { flagLeft: "🇬🇧", flagRight: "🇺🇸", thai: "ปอนด์ / ดอลลาร์สหรัฐฯ" },
  "AUD/USD": { flagLeft: "🇦🇺", flagRight: "🇺🇸", thai: "ดอลลาร์ออสเตรเลีย / ดอลลาร์สหรัฐฯ" },
};

interface PairQuoteCardProps {
  pair: string;
  onPriceUpdate?: (price: number) => void;
}

type MarketStatus = "open" | "dead_zone" | "closed";

export function PairQuoteCard({ pair, onPriceUpdate }: PairQuoteCardProps) {
  const [price, setPrice] = useState<PriceData | null>(null);
  const [prevPrice, setPrevPrice] = useState<number | null>(null);
  const [flash, setFlash] = useState<"up" | "down" | null>(null);
  const [connected, setConnected] = useState(false);
  const [performance, setPerformance] = useState<PairPerformance | null>(null);
  const [marketStatus, setMarketStatus] = useState<MarketStatus>("open");

  const priceRef = useRef<PriceData | null>(null);
  const sseRef = useRef<EventSource | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const meta = PAIR_META[pair] || { flagLeft: "🏳️", flagRight: "🏳️", thai: pair };
  const isJPY = pair.includes("JPY");
  const decimals = isJPY ? 3 : 5;

  // Fetch performance + session status (once per pair change)
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [perfRes, sessionRes] = await Promise.all([
          api.prices.performance().catch(() => null),
          api.analysis.session().catch(() => null),
        ]);
        if (cancelled) return;
        if (perfRes) setPerformance(perfRes.performance[pair] ?? null);
        if (sessionRes) {
          if (sessionRes.is_dead_zone) setMarketStatus("dead_zone");
          else setMarketStatus("open");
        }
      } catch {
        // silent
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [pair]);

  // Real-time SSE price stream with exponential-backoff reconnect
  useEffect(() => {
    let cancelled = false;

    const connect = () => {
      if (cancelled) return;
      const sse = new EventSource(`${API_BASE}/price/stream`);
      sseRef.current = sse;

      sse.onopen = () => {
        if (cancelled) return;
        setConnected(true);
        reconnectAttemptsRef.current = 0;
      };

      sse.onmessage = (event) => {
        if (cancelled) return;
        try {
          const data = JSON.parse(event.data);
          if (data.prices && data.prices[pair]) {
            const newData = data.prices[pair] as PriceData;
            const old = priceRef.current;

            if (old && newData.price !== old.price) {
              setPrevPrice(old.price);
              setFlash(newData.price > old.price ? "up" : "down");
              setTimeout(() => setFlash(null), 500);
            }

            priceRef.current = newData;
            setPrice(newData);
            onPriceUpdate?.(newData.price);
          }
        } catch {
          // parse error
        }
      };

      sse.onerror = () => {
        if (cancelled) return;
        setConnected(false);
        sse.close();
        sseRef.current = null;

        // Exponential backoff: 1s, 2s, 4s, 8s, 16s, max 30s
        const attempt = reconnectAttemptsRef.current;
        const delay = Math.min(30_000, 1000 * 2 ** attempt);
        reconnectAttemptsRef.current = attempt + 1;

        if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = setTimeout(connect, delay);
      };
    };

    connect();

    return () => {
      cancelled = true;
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      if (sseRef.current) {
        sseRef.current.close();
        sseRef.current = null;
      }
    };
  }, [pair]); // eslint-disable-line react-hooks/exhaustive-deps

  const currentPrice = price?.price ?? 0;
  const change = price?.change ?? 0;
  const pct = price?.percent_change ?? 0;
  const isUp = pct > 0;
  const isDown = pct < 0;

  // Split price into main part + last digit (TradingView-style superscript)
  const priceStr = currentPrice > 0 ? currentPrice.toFixed(decimals) : "—";
  const priceMain = priceStr === "—" ? "—" : priceStr.slice(0, -1);
  const priceLast = priceStr === "—" ? "" : priceStr.slice(-1);

  const statusMeta = {
    open: { label: "ตลาดเปิด", color: "text-buy" },
    dead_zone: { label: "Dead Zone", color: "text-amber-400" },
    closed: { label: "ตลาดปิด", color: "text-text-muted" },
  }[marketStatus];

  return (
    <div className="rounded-2xl bg-gradient-to-br from-bg-surface/90 to-bg-surface/40 backdrop-blur border border-border overflow-hidden">
      {/* Top row: pair + live status */}
      <div className="flex items-start justify-between gap-4 p-4 pb-3">
        <div className="flex-1 min-w-0">
          {/* Pair name with flags */}
          <div className="flex items-center gap-2 mb-1">
            <span className="text-2xl leading-none" aria-label={pair}>
              {meta.flagLeft}
              {meta.flagRight}
            </span>
            <h2 className="text-xl font-bold tracking-tight text-text-primary">
              {pair.replace("/", "")}
            </h2>
          </div>
          {/* Thai description + market */}
          <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[11px] text-text-muted">
            <span>{meta.thai}</span>
            <span>•</span>
            <span className="font-medium">Sochron1k · Real-time</span>
            <span>•</span>
            <span>ฟอเร็กซ์</span>
          </div>
        </div>

        {/* Right: connection + source */}
        <div className="flex flex-col items-end gap-1.5 flex-shrink-0">
          <div className="flex items-center gap-1.5">
            <span className="relative flex h-2 w-2">
              <span
                className={cn(
                  "animate-ping absolute inline-flex h-full w-full rounded-full opacity-75",
                  connected ? "bg-buy" : "bg-amber-400"
                )}
              />
              <span
                className={cn(
                  "relative inline-flex rounded-full h-2 w-2",
                  connected ? "bg-buy" : "bg-amber-500"
                )}
              />
            </span>
            <span className="text-[10px] font-semibold tracking-wider uppercase text-text-secondary">
              LIVE
            </span>
          </div>
          <div className="flex items-center gap-1 text-[10px] text-text-muted">
            {connected ? (
              <Wifi className="w-3 h-3 text-buy" />
            ) : (
              <WifiOff className="w-3 h-3 text-amber-400" />
            )}
            <span>{price?.source === "websocket" ? "WebSocket" : "SSE"}</span>
          </div>
        </div>
      </div>

      {/* Main price row */}
      <div className="px-4 pb-3">
        <div className="flex items-baseline gap-3 flex-wrap">
          <div className="flex items-baseline">
            <span
              className={cn(
                "text-4xl sm:text-5xl font-bold font-mono tabular-nums tracking-tight transition-colors duration-300",
                flash === "up"
                  ? "text-buy"
                  : flash === "down"
                    ? "text-sell"
                    : "text-text-primary"
              )}
            >
              {priceMain}
            </span>
            <span
              className={cn(
                "text-2xl sm:text-3xl font-bold font-mono align-super transition-colors duration-300",
                flash === "up"
                  ? "text-buy"
                  : flash === "down"
                    ? "text-sell"
                    : "text-text-secondary"
              )}
            >
              {priceLast}
            </span>
          </div>
          <span className="text-sm text-text-muted font-medium">
            {pair.split("/")[1]}
          </span>
        </div>

        {/* Change + percent */}
        <div className="flex items-center gap-2 mt-1">
          <span
            className={cn(
              "text-sm font-mono font-semibold",
              isUp ? "text-buy" : isDown ? "text-sell" : "text-text-muted"
            )}
          >
            {currentPrice > 0 && change !== 0
              ? `${change > 0 ? "+" : ""}${change.toFixed(isJPY ? 3 : 5)}`
              : "—"}
          </span>
          <span
            className={cn(
              "text-sm font-mono font-semibold",
              isUp ? "text-buy" : isDown ? "text-sell" : "text-text-muted"
            )}
          >
            {currentPrice > 0 && pct !== 0
              ? `${pct > 0 ? "+" : ""}${pct.toFixed(2)}%`
              : ""}
          </span>
        </div>

        {/* Market status dot */}
        <div className={cn("flex items-center gap-1.5 mt-2 text-xs", statusMeta.color)}>
          <Circle
            className={cn("w-2 h-2 fill-current", marketStatus === "open" && "animate-pulse")}
          />
          <span className="font-medium">{statusMeta.label}</span>
          {price?.reference_type && (
            <span className="text-text-muted ml-1 text-[10px]">· vs 24h ago</span>
          )}
        </div>
      </div>

      {/* Bid / Ask / Spread strip */}
      {price?.bid && price?.ask && (
        <div className="grid grid-cols-3 gap-0 border-t border-border/60 bg-bg-surface/40">
          <QuoteStat label="Bid" value={price.bid.toFixed(decimals)} color="text-sell" />
          <QuoteStat label="Ask" value={price.ask.toFixed(decimals)} color="text-buy" />
          <QuoteStat
            label="Spread"
            value={price.spread ? `${price.spread.toFixed(1)}p` : "—"}
            color="text-accent-400"
          />
        </div>
      )}

      {/* Performance grid (1D / 3D / 1W / 1M) */}
      {performance && (
        <div className="px-4 py-3 border-t border-border/60 bg-bg-surface/20">
          <div className="text-[10px] font-semibold uppercase tracking-wider text-text-muted mb-2">
            ประสิทธิภาพ
          </div>
          <div className="grid grid-cols-4 gap-2">
            <PerfBox label="1D" change={performance["1D"]} />
            <PerfBox label="3D" change={performance["3D"]} />
            <PerfBox label="1W" change={performance["1W"]} />
            <PerfBox label="1M" change={performance["1M"]} />
          </div>
        </div>
      )}
    </div>
  );
}

function QuoteStat({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color: string;
}) {
  return (
    <div className="px-3 py-2 text-center border-r border-border/60 last:border-r-0">
      <div className="text-[10px] text-text-muted">{label}</div>
      <div className={cn("text-sm font-mono font-semibold", color)}>{value}</div>
    </div>
  );
}

function PerfBox({
  label,
  change,
}: {
  label: string;
  change: { pct: number; pips: number; from_price: number } | null;
}) {
  if (!change) {
    return (
      <div className="rounded-lg p-2 bg-bg-elevated/40 border border-border/40 text-center">
        <div className="text-[10px] text-text-muted mb-0.5">{label}</div>
        <div className="text-sm font-mono text-text-muted">—</div>
      </div>
    );
  }

  const isUp = change.pct > 0;
  const isDown = change.pct < 0;
  const color = isUp ? "text-buy" : isDown ? "text-sell" : "text-text-muted";
  const bg = isUp ? "bg-buy/10 border-buy/30" : isDown ? "bg-sell/10 border-sell/30" : "bg-bg-elevated/40 border-border/40";

  return (
    <div className={cn("rounded-lg p-2 border text-center transition-colors", bg)}>
      <div className="text-[10px] text-text-muted mb-0.5">{label}</div>
      <div className={cn("text-sm font-mono font-bold", color)}>
        {isUp ? "+" : ""}
        {change.pct.toFixed(2)}%
      </div>
      <div className={cn("text-[10px] font-mono", color, "opacity-70")}>
        {isUp ? "+" : ""}
        {change.pips.toFixed(1)}p
      </div>
    </div>
  );
}
