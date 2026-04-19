"use client";

import { TrendingUp, TrendingDown, Pause, X, Target, ShieldAlert } from "lucide-react";
import type { TradeSetup } from "@/lib/api";
import { cn } from "@/lib/utils";

const DIRECTION_META: Record<string, { label: string; color: string; bg: string; Icon: typeof TrendingUp }> = {
  buy: { label: "BUY", color: "text-buy", bg: "bg-buy/20 border-buy/40", Icon: TrendingUp },
  sell: { label: "SELL", color: "text-sell", bg: "bg-sell/20 border-sell/40", Icon: TrendingDown },
  wait: { label: "WAIT", color: "text-amber-300", bg: "bg-amber-500/15 border-amber-500/30", Icon: Pause },
  avoid: { label: "AVOID", color: "text-red-400", bg: "bg-red-500/15 border-red-500/30", Icon: X },
};

const STYLE_LABEL: Record<string, string> = {
  scalp: "Scalp (นาที)",
  intraday: "Intraday (วัน)",
  swing: "Swing (หลายวัน)",
};

const ENTRY_TYPE_LABEL: Record<string, string> = {
  market: "Market",
  limit: "Limit",
  stop: "Stop",
};

interface TradeSetupBoxProps {
  setup?: TradeSetup;
}

export function TradeSetupBox({ setup }: TradeSetupBoxProps) {
  if (!setup || !setup.direction) return null;

  const dir = DIRECTION_META[setup.direction] || DIRECTION_META.wait;
  const DirIcon = dir.Icon;
  const isActive = setup.direction === "buy" || setup.direction === "sell";
  const rr = setup.risk_reward ?? 0;
  const rrGood = rr >= 1.5;

  return (
    <div className="mb-4 rounded-xl overflow-hidden border border-border">
      {/* Header */}
      <div className={cn("flex items-center justify-between px-3 py-2 border-b border-border", dir.bg)}>
        <div className="flex items-center gap-2">
          <div className={cn("flex items-center gap-1.5 px-2 py-1 rounded-lg font-bold", dir.color)}>
            <DirIcon className="w-4 h-4" />
            <span className="text-sm">{dir.label}</span>
          </div>
          {setup.pair && (
            <span className="text-sm font-mono font-bold text-text-primary">{setup.pair}</span>
          )}
          {setup.style && (
            <span className="text-[10px] text-text-muted px-1.5 py-0.5 rounded bg-bg-elevated">
              {STYLE_LABEL[setup.style] || setup.style}
            </span>
          )}
        </div>
        <div className="flex items-center gap-1 text-xs font-semibold">
          <Target className="w-3 h-3 text-text-muted" />
          <span className="text-text-muted">Trade Setup</span>
        </div>
      </div>

      {isActive ? (
        <>
          {/* Entry / SL / TP */}
          <div className="grid grid-cols-3 divide-x divide-border">
            <TradeStat
              label="Entry"
              value={setup.entry_zone || ENTRY_TYPE_LABEL[setup.entry_type || "market"]}
              sub={setup.entry_type ? ENTRY_TYPE_LABEL[setup.entry_type] : "Market"}
              color="text-text-primary"
            />
            <TradeStat
              label="Stop Loss"
              value={setup.sl_pips ? `${setup.sl_pips} pips` : "—"}
              sub="Invalidation"
              color="text-sell"
            />
            <TradeStat
              label="Take Profit"
              value={setup.tp_pips ? `${setup.tp_pips} pips` : "—"}
              sub={rr ? `R:R 1:${rr.toFixed(1)}` : ""}
              color="text-buy"
            />
          </div>

          {/* R:R bar + warning */}
          <div className="px-3 py-2 bg-bg-surface/30 border-t border-border">
            <div className="flex items-center justify-between gap-3">
              <div className="flex-1">
                <div className="text-[10px] text-text-muted mb-1">Risk:Reward</div>
                <div className="h-1.5 rounded-full bg-bg-elevated relative overflow-hidden">
                  <div
                    className={cn(
                      "h-full rounded-full transition-all",
                      rrGood ? "bg-gradient-to-r from-buy to-accent-500" : "bg-amber-500"
                    )}
                    style={{ width: `${Math.min(100, rr * 30)}%` }}
                  />
                </div>
              </div>
              <span className={cn("text-sm font-bold font-mono", rrGood ? "text-buy" : "text-amber-400")}>
                {rr.toFixed(1)}x
              </span>
            </div>
            {setup.warning_minutes && setup.warning_minutes > 0 && (
              <div className="mt-2 flex items-start gap-1.5 text-[11px] text-amber-300">
                <ShieldAlert className="w-3 h-3 flex-shrink-0 mt-0.5" />
                <span>เลี่ยงเทรด {setup.warning_minutes} นาที ก่อน/หลังข่าวออก</span>
              </div>
            )}
          </div>
        </>
      ) : (
        <div className="px-3 py-3 text-center">
          <p className="text-xs text-text-muted">
            {setup.direction === "avoid"
              ? "⚠️ AI ไม่แนะนำเทรดข่าวนี้ — เสี่ยงสูงเทียบกับผลตอบแทน"
              : "⏸ AI แนะนำรอ — ดูปฏิกิริยาตลาดก่อนเข้าเทรด"}
          </p>
        </div>
      )}
    </div>
  );
}

function TradeStat({
  label,
  value,
  sub,
  color,
}: {
  label: string;
  value: string;
  sub?: string;
  color: string;
}) {
  return (
    <div className="px-3 py-2.5 text-center">
      <div className="text-[10px] text-text-muted mb-0.5">{label}</div>
      <div className={cn("text-sm font-mono font-bold", color)}>{value}</div>
      {sub && <div className="text-[10px] text-text-muted mt-0.5">{sub}</div>}
    </div>
  );
}
