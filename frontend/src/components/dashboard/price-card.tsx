"use client";

import { ArrowDown, ArrowUp, Minus, TrendingUp, TrendingDown } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle, CardValue } from "@/components/ui/card";
import { AnimatedNumber } from "@/components/ui/animated-number";
import type { PriceData, AnalysisResult, PairPerformance } from "@/lib/api";

interface PriceCardProps {
  pair: string;
  price?: PriceData | null;
  analysis?: AnalysisResult | null;
  performance?: PairPerformance | null;
  flash?: "up" | "down" | null;
}

function PerfBadge({ label, pct, pips }: { label: string; pct: number; pips: number }) {
  const isUp = pct > 0;
  const isDown = pct < 0;
  return (
    <div className="flex flex-col items-center gap-0.5 min-w-[52px]">
      <span className="text-[10px] text-text-muted font-medium">{label}</span>
      <span
        className={`text-xs font-mono font-semibold ${
          isUp ? "text-emerald-400" : isDown ? "text-red-400" : "text-text-muted"
        }`}
      >
        {isUp ? "+" : ""}
        {pct.toFixed(2)}%
      </span>
      <span className="text-[10px] font-mono text-text-muted">
        {isUp ? "+" : ""}
        {pips.toFixed(1)}p
      </span>
    </div>
  );
}

export function PriceCard({ pair, price, analysis, performance, flash }: PriceCardProps) {
  const direction = analysis?.direction;
  const confidence = analysis?.confidence ?? 0;
  const regime = analysis?.regime?.regime ?? "—";
  const isJPY = pair.includes("JPY");
  const decimals = isJPY ? 3 : 5;

  const perf1d = performance?.["1D"];
  const dayChange = perf1d?.pct ?? 0;
  const isUp = dayChange > 0;
  const isDown = dayChange < 0;

  // Day range bar
  const dayOpen = performance?.day_open ?? 0;
  const dayHigh = performance?.day_high ?? 0;
  const dayLow = performance?.day_low ?? 0;
  const currentPrice = price?.price ?? performance?.price ?? 0;
  const rangeSpan = dayHigh - dayLow || 1;
  const positionPct = Math.max(0, Math.min(100, ((currentPrice - dayLow) / rangeSpan) * 100));

  return (
    <Card className={`card-hover hover:border-primary-500/50 group relative overflow-hidden ${flash === "up" ? "flash-up" : flash === "down" ? "flash-down" : ""}`}>
      {/* Subtle gradient background based on direction */}
      <div
        className="absolute inset-0 opacity-5 pointer-events-none transition-opacity duration-500 group-hover:opacity-10"
        style={{
          background: isUp
            ? "linear-gradient(135deg, #22c55e 0%, transparent 60%)"
            : isDown
              ? "linear-gradient(135deg, #ef4444 0%, transparent 60%)"
              : "none",
        }}
      />

      <CardHeader>
        <div className="flex items-center gap-2">
          <CardTitle className="group-hover:text-primary-300 transition-colors">{pair}</CardTitle>
          {/* Live dot */}
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute h-full w-full rounded-full bg-emerald-400 opacity-60" />
            <span className="relative rounded-full h-2 w-2 bg-emerald-500" />
          </span>
        </div>
        {direction && direction !== "NO_TRADE" ? (
          <Badge variant={direction === "BUY" ? "buy" : "sell"}>
            {direction === "BUY" ? (
              <TrendingUp className="w-3 h-3 mr-1" />
            ) : (
              <TrendingDown className="w-3 h-3 mr-1" />
            )}
            {direction}
          </Badge>
        ) : (
          <Badge variant="neutral">
            <Minus className="w-3 h-3 mr-1" />
            {direction === "NO_TRADE" ? "STOP" : "รอข้อมูล"}
          </Badge>
        )}
      </CardHeader>

      {/* Price + Daily change */}
      <div className="flex items-end justify-between mt-1">
        <CardValue
          className={`transition-colors duration-300 ${
            flash === "up"
              ? "text-emerald-400"
              : flash === "down"
                ? "text-red-400"
                : isUp
                  ? "text-buy"
                  : isDown
                    ? "text-sell"
                    : "text-accent-400"
          }`}
        >
          {currentPrice ? (
            <AnimatedNumber value={currentPrice} decimals={decimals} flashOnChange={false} duration={400} />
          ) : (
            "—"
          )}
        </CardValue>
        {perf1d && (
          <div className={`flex items-center gap-1 text-sm font-mono ${isUp ? "text-emerald-400" : isDown ? "text-red-400" : "text-text-muted"}`}>
            {isUp ? <ArrowUp className="w-3.5 h-3.5" /> : isDown ? <ArrowDown className="w-3.5 h-3.5" /> : null}
            <span>{isUp ? "+" : ""}{dayChange.toFixed(3)}%</span>
          </div>
        )}
      </div>

      {/* Bid / Ask / Spread */}
      {price?.bid && price?.ask && (
        <div className="flex items-center gap-2 mt-2 text-[11px] font-mono">
          <span className="text-emerald-400/80">B {price.bid.toFixed(decimals)}</span>
          <span className="text-text-muted">/</span>
          <span className="text-red-400/80">A {price.ask.toFixed(decimals)}</span>
          {price.spread !== undefined && (
            <span className="ml-auto text-text-muted px-1.5 py-0.5 rounded bg-bg-surface text-[10px]">
              {price.spread.toFixed(1)}p spread
            </span>
          )}
        </div>
      )}

      {/* Day Range Bar */}
      {dayHigh > 0 && (
        <div className="mt-3">
          <div className="flex justify-between text-[10px] text-text-muted mb-1">
            <span>L {dayLow.toFixed(decimals)}</span>
            <span>H {dayHigh.toFixed(decimals)}</span>
          </div>
          <div className="relative h-1.5 rounded-full bg-bg-surface overflow-hidden">
            <div
              className="absolute h-full rounded-full bg-gradient-to-r from-red-500/60 via-yellow-500/40 to-emerald-500/60"
              style={{ width: "100%" }}
            />
            <div
              className="absolute top-1/2 -translate-y-1/2 w-2.5 h-2.5 rounded-full bg-white border-2 border-accent-500 shadow-md transition-all duration-500"
              style={{ left: `calc(${positionPct}% - 5px)` }}
            />
          </div>
        </div>
      )}

      {/* Performance Grid: 1D / 3D / 1W / 1M */}
      <div className="mt-3 pt-3 border-t border-border/50">
        <div className="flex justify-between">
          {(["1D", "3D", "1W", "1M"] as const).map((period) => {
            const data = performance?.[period];
            return data ? (
              <PerfBadge key={period} label={period} pct={data.pct} pips={data.pips} />
            ) : (
              <div key={period} className="flex flex-col items-center gap-0.5 min-w-[52px]">
                <span className="text-[10px] text-text-muted">{period}</span>
                <span className="text-xs text-text-muted">—</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Confidence */}
      {confidence > 0 && (
        <div className="mt-3 pt-2 border-t border-border/50">
          <div className="flex justify-between text-xs mb-1">
            <span className="text-text-muted">ความมั่นใจ</span>
            <span className="text-text-secondary font-mono">{(confidence * 100).toFixed(0)}%</span>
          </div>
          <div className="h-1.5 rounded-full bg-bg-surface overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-700"
              style={{
                width: `${confidence * 100}%`,
                background:
                  confidence >= 0.75
                    ? "linear-gradient(90deg, #22c55e, #06b6d4)"
                    : confidence >= 0.5
                      ? "linear-gradient(90deg, #f59e0b, #eab308)"
                      : "linear-gradient(90deg, #ef4444, #dc2626)",
              }}
            />
          </div>
          <p className="text-[10px] text-text-muted mt-1 capitalize">{regime}</p>
        </div>
      )}
    </Card>
  );
}
