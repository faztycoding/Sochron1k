"use client";

import { ShieldAlert, Zap, Clock } from "lucide-react";
import type { RiskMeter } from "@/lib/api";
import { cn } from "@/lib/utils";

interface RiskMeterGaugeProps {
  meter?: RiskMeter;
}

export function RiskMeterGauge({ meter }: RiskMeterGaugeProps) {
  if (!meter) return null;

  const { risk_score, opportunity_score, warning_active, message_th, minutes_to_event } = meter;

  return (
    <div
      className={cn(
        "mb-4 rounded-xl border overflow-hidden",
        warning_active
          ? "border-red-500/40 bg-gradient-to-br from-red-500/15 to-red-500/5"
          : "border-border bg-bg-surface/30"
      )}
    >
      {/* Top message */}
      <div
        className={cn(
          "px-3 py-2 border-b",
          warning_active ? "border-red-500/30 bg-red-500/10" : "border-border"
        )}
      >
        <div className="flex items-center gap-2">
          {warning_active ? (
            <ShieldAlert className="w-4 h-4 text-red-400 animate-pulse flex-shrink-0" />
          ) : (
            <Clock className="w-4 h-4 text-accent-400 flex-shrink-0" />
          )}
          <span
            className={cn(
              "text-sm font-medium",
              warning_active ? "text-red-300" : "text-text-primary"
            )}
          >
            {message_th}
          </span>
        </div>
      </div>

      {/* Dual meter */}
      <div className="grid grid-cols-2 divide-x divide-border">
        <MeterBar
          label="ความเสี่ยง"
          score={risk_score}
          color="text-red-400"
          barClass="bg-gradient-to-r from-amber-500 to-red-500"
          icon={<ShieldAlert className="w-3 h-3" />}
        />
        <MeterBar
          label="โอกาสเทรด"
          score={opportunity_score}
          color="text-buy"
          barClass="bg-gradient-to-r from-accent-500 to-buy"
          icon={<Zap className="w-3 h-3" />}
        />
      </div>

      {/* Countdown (if event in future) */}
      {minutes_to_event !== undefined && minutes_to_event !== null && minutes_to_event > 0 && (
        <div className="px-3 py-2 bg-bg-surface/40 border-t border-border flex items-center justify-between text-[11px]">
          <span className="text-text-muted">นับถอยหลังข่าว</span>
          <span className="font-mono font-bold text-accent-300">
            {formatCountdown(minutes_to_event)}
          </span>
        </div>
      )}
    </div>
  );
}

function MeterBar({
  label,
  score,
  color,
  barClass,
  icon,
}: {
  label: string;
  score: number;
  color: string;
  barClass: string;
  icon: React.ReactNode;
}) {
  return (
    <div className="px-3 py-2.5">
      <div className="flex items-center justify-between mb-1.5">
        <div className={cn("flex items-center gap-1 text-[11px] font-medium", color)}>
          {icon}
          <span>{label}</span>
        </div>
        <span className={cn("text-sm font-bold font-mono", color)}>{score}</span>
      </div>
      <div className="h-1.5 rounded-full bg-bg-elevated overflow-hidden">
        <div
          className={cn("h-full rounded-full transition-all", barClass)}
          style={{ width: `${Math.min(100, Math.max(0, score))}%` }}
        />
      </div>
    </div>
  );
}

function formatCountdown(minutes: number): string {
  if (minutes < 60) return `${minutes} นาที`;
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  if (hours < 24) {
    return mins > 0 ? `${hours}ชม. ${mins}น.` : `${hours} ชั่วโมง`;
  }
  const days = Math.floor(hours / 24);
  const hrs = hours % 24;
  return hrs > 0 ? `${days}วัน ${hrs}ชม.` : `${days} วัน`;
}
