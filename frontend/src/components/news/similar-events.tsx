"use client";

import { History, TrendingUp, TrendingDown } from "lucide-react";
import type { SimilarEvent } from "@/lib/api";
import { cn } from "@/lib/utils";

interface SimilarEventsProps {
  events?: SimilarEvent[];
}

export function SimilarEvents({ events }: SimilarEventsProps) {
  if (!events || events.length === 0) return null;

  return (
    <div className="mb-4">
      <div className="flex items-center gap-1.5 mb-2">
        <History className="w-3.5 h-3.5 text-accent-400" />
        <span className="text-xs font-semibold text-text-primary">ครั้งก่อนที่ใกล้เคียง</span>
        <span className="text-[10px] text-text-muted">({events.length})</span>
      </div>

      <div className="space-y-1.5">
        {events.slice(0, 3).map((ev, idx) => {
          const pips = ev.pips_moved ?? 0;
          const isBullish = pips > 0;
          const absPips = Math.abs(pips);

          return (
            <div
              key={idx}
              className="flex items-center gap-2 p-2 rounded-lg bg-bg-surface/50 border border-border/50 hover:border-accent-500/30 transition-colors"
            >
              {/* Direction icon */}
              <div
                className={cn(
                  "flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center",
                  absPips === 0
                    ? "bg-bg-elevated text-text-muted"
                    : isBullish
                      ? "bg-buy/15 text-buy"
                      : "bg-sell/15 text-sell"
                )}
              >
                {absPips === 0 ? (
                  <History className="w-3.5 h-3.5" />
                ) : isBullish ? (
                  <TrendingUp className="w-3.5 h-3.5" />
                ) : (
                  <TrendingDown className="w-3.5 h-3.5" />
                )}
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="text-xs text-text-primary truncate font-medium">{ev.event}</div>
                <div className="text-[10px] text-text-muted flex items-center gap-2 mt-0.5">
                  {ev.date_approx && <span>{ev.date_approx}</span>}
                  {ev.pair_impact && (
                    <>
                      <span className="text-border">•</span>
                      <span className="font-mono">{ev.pair_impact}</span>
                    </>
                  )}
                  {ev.time_to_peak && (
                    <>
                      <span className="text-border">•</span>
                      <span>ยอดใน {ev.time_to_peak}</span>
                    </>
                  )}
                </div>
              </div>

              {/* Pips */}
              {absPips > 0 && (
                <div className="flex-shrink-0 text-right">
                  <div className={cn("text-sm font-mono font-bold", isBullish ? "text-buy" : "text-sell")}>
                    {isBullish ? "+" : "-"}
                    {absPips}
                  </div>
                  <div className="text-[9px] text-text-muted">pips</div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
