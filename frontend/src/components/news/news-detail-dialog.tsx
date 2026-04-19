"use client";

import { ExternalLink, Clock, Flame, TrendingUp, TrendingDown, Minus, Target, BarChart3, Activity, AlertCircle } from "lucide-react";
import type { NewsItem } from "@/lib/api";
import {
  CATEGORY_META,
  SOURCE_META,
  CURRENCY_FLAGS,
  getImpactMeta,
  getActionMeta,
  getSentimentMeta,
  formatRelativeTime,
  formatThaiTime,
  TIME_HORIZON_LABEL,
} from "@/lib/news-utils";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogHeader, DialogBody } from "@/components/ui/dialog";
import { cn } from "@/lib/utils";
import { RiskMeterGauge } from "@/components/news/risk-meter-gauge";
import { TradeSetupBox } from "@/components/news/trade-setup-box";
import { ReasoningChain } from "@/components/news/reasoning-chain";
import { SimilarEvents } from "@/components/news/similar-events";

interface NewsDetailDialogProps {
  item: NewsItem | null;
  open: boolean;
  onClose: () => void;
}

export function NewsDetailDialog({ item, open, onClose }: NewsDetailDialogProps) {
  if (!item) return null;

  const impactScore = item.impact_score ?? (item.impact_level === "high" ? 4 : item.impact_level === "medium" ? 3 : 2);
  const impact = getImpactMeta(impactScore);
  const action = item.actionability ? getActionMeta(item.actionability) : null;
  const cat = item.category ? CATEGORY_META[item.category] : null;
  const src = SOURCE_META[item.source] || { label: item.source, color: "text-text-muted" };

  const currencies = (item.currency || "").split(",").filter(Boolean);
  const sentScore = item.sentiment_score ?? 0;
  const surprise = (item.surprise_factor ?? 0) * 100;

  return (
    <Dialog open={open} onClose={onClose} className="max-w-2xl">
      {/* Top impact stripe */}
      <div className={cn("h-1.5 w-full", impact.bg.replace("/15", "/80"))} />

      <DialogHeader>
        {/* Top meta row */}
        <div className="flex items-center gap-2 mb-2 flex-wrap">
          {currencies.map((c) => (
            <span key={c} className="text-2xl" title={c.trim()}>
              {CURRENCY_FLAGS[c.trim()] || "🏳️"}
            </span>
          ))}

          <div className={cn("flex items-center gap-1 px-2 py-1 rounded-lg border text-sm font-bold", impact.bg, impact.border, impact.color)}>
            <span>{impact.stars}</span>
            <span className="text-xs ml-1">{impact.label}</span>
          </div>

          {cat && (
            <Badge variant="neutral" className={cn("text-xs", cat.color)}>
              <span className="mr-1">{cat.icon}</span>
              {cat.label}
            </Badge>
          )}

          {item.is_urgent && (
            <Badge variant="danger" className="text-xs animate-pulse">
              <Flame className="w-3 h-3 mr-1" />
              ด่วนมาก
            </Badge>
          )}
        </div>

        {/* Title */}
        <h2 className="text-xl font-bold leading-snug pr-8">
          {item.title_th || item.title_original}
        </h2>
        {item.title_th && item.title_th !== item.title_original && (
          <p className="text-xs text-text-muted italic mt-1">
            🇺🇸 {item.title_original}
          </p>
        )}

        {/* Time + source */}
        <div className="flex items-center gap-3 mt-2 text-xs text-text-muted">
          <span className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {formatRelativeTime(item.scraped_at)}
          </span>
          <span>•</span>
          <span>{formatThaiTime(item.scraped_at)}</span>
          <span>•</span>
          <span className={cn("font-medium", src.color)}>{src.label}</span>
        </div>
      </DialogHeader>

      <DialogBody>
        {/* Key Takeaway (highlighted) */}
        {item.key_takeaway_th && (
          <div className="mb-4 p-3 rounded-xl bg-gradient-to-br from-primary-500/15 to-accent-500/10 border border-primary-500/30">
            <div className="flex items-start gap-2">
              <span className="text-xl">💡</span>
              <div>
                <div className="text-xs font-semibold text-primary-300 mb-1">ประเด็นสำหรับเทรดเดอร์</div>
                <p className="text-sm text-text-primary leading-snug">{item.key_takeaway_th}</p>
                {item.key_takeaway && item.key_takeaway !== item.key_takeaway_th && (
                  <p className="text-[11px] text-text-muted mt-1 italic">{item.key_takeaway}</p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* NEW: Risk Meter + Countdown (critical — always first) */}
        <RiskMeterGauge meter={item.risk_meter} />

        {/* NEW: Trade Setup (Entry/SL/TP) */}
        <TradeSetupBox setup={item.trade_setup} />

        {/* Summary */}
        {(item.summary_th || item.summary_original) && (
          <div className="mb-4">
            <div className="text-xs text-text-muted mb-1.5 font-medium">สรุปข่าว</div>
            <p className="text-sm text-text-secondary leading-relaxed">
              {item.summary_th || item.summary_original}
            </p>
            {item.summary_th && item.summary_original && item.summary_th !== item.summary_original && (
              <details className="mt-2">
                <summary className="text-[11px] text-text-muted cursor-pointer hover:text-text-primary">
                  ต้นฉบับภาษาอังกฤษ
                </summary>
                <p className="text-[11px] text-text-muted mt-1 italic">{item.summary_original}</p>
              </details>
            )}
          </div>
        )}

        {/* Rating stats grid */}
        <div className="grid grid-cols-2 gap-2 mb-4">
          {/* Expected volatility */}
          {item.expected_volatility_pips !== undefined && (
            <StatBox
              icon={<BarChart3 className="w-3.5 h-3.5" />}
              label="Volatility คาดการณ์"
              value={`${item.expected_volatility_pips} pips`}
              color={item.expected_volatility_pips >= 50 ? "text-red-400" : item.expected_volatility_pips >= 25 ? "text-amber-400" : "text-blue-400"}
            />
          )}

          {/* Time horizon */}
          {item.time_horizon && (
            <StatBox
              icon={<Clock className="w-3.5 h-3.5" />}
              label="กรอบเวลา"
              value={TIME_HORIZON_LABEL[item.time_horizon] || item.time_horizon}
              color="text-accent-400"
            />
          )}

          {/* Surprise factor */}
          {item.surprise_factor !== undefined && item.surprise_factor > 0 && (
            <StatBox
              icon={<AlertCircle className="w-3.5 h-3.5" />}
              label="Surprise Factor"
              value={`${surprise.toFixed(0)}%`}
              color={surprise >= 50 ? "text-red-400" : surprise >= 20 ? "text-amber-400" : "text-text-secondary"}
            />
          )}

          {/* Actionability */}
          {action && (
            <StatBox
              icon={<Target className="w-3.5 h-3.5" />}
              label="Actionability"
              value={action.label}
              color={action.color}
            />
          )}
        </div>

        {/* Key Numbers (if economic data) */}
        {item.key_numbers && (item.key_numbers.actual || item.key_numbers.forecast || item.key_numbers.previous) && (
          <div className="mb-4">
            <div className="text-xs text-text-muted mb-2 font-medium flex items-center gap-1">
              <BarChart3 className="w-3.5 h-3.5" />
              ตัวเลขเศรษฐกิจ
            </div>
            <div className="grid grid-cols-3 gap-2 text-center">
              {item.key_numbers.actual && (
                <div className="p-2.5 rounded-lg bg-bg-surface/70">
                  <div className="text-[10px] text-text-muted">Actual</div>
                  <div className="text-sm font-mono font-bold text-text-primary">{item.key_numbers.actual}</div>
                </div>
              )}
              {item.key_numbers.forecast && (
                <div className="p-2.5 rounded-lg bg-bg-surface/70">
                  <div className="text-[10px] text-text-muted">Forecast</div>
                  <div className="text-sm font-mono text-text-secondary">{item.key_numbers.forecast}</div>
                </div>
              )}
              {item.key_numbers.previous && (
                <div className="p-2.5 rounded-lg bg-bg-surface/70">
                  <div className="text-[10px] text-text-muted">Previous</div>
                  <div className="text-sm font-mono text-text-muted">{item.key_numbers.previous}</div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Sentiment per currency */}
        {item.sentiment && Object.keys(item.sentiment).length > 0 && (
          <div className="mb-4">
            <div className="text-xs text-text-muted mb-2 font-medium flex items-center gap-1">
              <Activity className="w-3.5 h-3.5" />
              ทิศทางแต่ละสกุลเงิน
            </div>
            <div className="grid grid-cols-5 gap-1.5">
              {["EUR", "USD", "JPY", "GBP", "AUD"].map((cur) => {
                const sent = item.sentiment?.[cur] || "neutral";
                const meta = getSentimentMeta(sent);
                return (
                  <div
                    key={cur}
                    className={cn(
                      "p-2 rounded-lg text-center border",
                      meta.bg,
                      sent === "bullish"
                        ? "border-buy/30"
                        : sent === "bearish"
                          ? "border-sell/30"
                          : "border-border"
                    )}
                  >
                    <div className="text-lg mb-0.5">{CURRENCY_FLAGS[cur]}</div>
                    <div className="text-[10px] text-text-muted font-medium">{cur}</div>
                    <div className={cn("text-xs font-semibold flex items-center justify-center gap-0.5", meta.color)}>
                      {sent === "bullish" ? <TrendingUp className="w-3 h-3" /> : sent === "bearish" ? <TrendingDown className="w-3 h-3" /> : <Minus className="w-3 h-3" />}
                      <span>{meta.label}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Overall sentiment score */}
        {Math.abs(sentScore) > 0.05 && (
          <div className="mb-4 p-3 rounded-xl bg-bg-surface/70">
            <div className="text-xs text-text-muted mb-1 font-medium">ทิศทางรวม</div>
            <div className="flex items-center gap-3">
              <div className="flex-1 h-2 rounded-full bg-bg-surface overflow-hidden relative">
                <div className="absolute inset-y-0 left-1/2 w-px bg-border" />
                <div
                  className={cn(
                    "absolute top-0 bottom-0 rounded-full",
                    sentScore > 0 ? "bg-buy left-1/2" : "bg-sell right-1/2"
                  )}
                  style={{ width: `${Math.abs(sentScore) * 50}%` }}
                />
              </div>
              <span className={cn("text-sm font-mono font-bold", sentScore > 0 ? "text-buy" : "text-sell")}>
                {sentScore > 0 ? "+" : ""}
                {sentScore.toFixed(2)}
              </span>
            </div>
          </div>
        )}

        {/* NEW: Similar past events */}
        <SimilarEvents events={item.similar_events} />

        {/* NEW: AI Reasoning Chain (collapsible) */}
        <ReasoningChain reasoning={item.reasoning} confidence={item.confidence} />

        {/* Link to original */}
        {item.url && (
          <a
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-center gap-2 w-full py-2.5 rounded-xl bg-primary-600/20 hover:bg-primary-600/30 border border-primary-500/30 text-primary-300 text-sm font-medium transition-colors"
          >
            <ExternalLink className="w-4 h-4" />
            อ่านต้นฉบับที่ {src.label}
          </a>
        )}
      </DialogBody>
    </Dialog>
  );
}

function StatBox({
  icon,
  label,
  value,
  color,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  color: string;
}) {
  return (
    <div className="p-2.5 rounded-lg bg-bg-surface/70">
      <div className="flex items-center gap-1 text-[10px] text-text-muted mb-1">
        {icon}
        <span>{label}</span>
      </div>
      <div className={cn("text-sm font-semibold", color)}>{value}</div>
    </div>
  );
}
