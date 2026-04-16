"use client";

import { ArrowUpRight, Clock, Flame, TrendingUp, TrendingDown, Eye } from "lucide-react";
import type { NewsItem } from "@/lib/api";
import {
  CATEGORY_META,
  SOURCE_META,
  CURRENCY_FLAGS,
  getImpactMeta,
  getActionMeta,
  formatRelativeTime,
} from "@/lib/news-utils";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface NewsCardProps {
  item: NewsItem;
  onClick?: () => void;
  variant?: "default" | "compact" | "featured";
}

export function NewsCard({ item, onClick, variant = "default" }: NewsCardProps) {
  const impactScore = item.impact_score ?? (item.impact_level === "high" ? 4 : item.impact_level === "medium" ? 3 : 2);
  const impact = getImpactMeta(impactScore);
  const action = item.actionability ? getActionMeta(item.actionability) : null;
  const cat = item.category ? CATEGORY_META[item.category] : null;
  const src = SOURCE_META[item.source] || { label: item.source, color: "text-text-muted" };

  // Currency flags
  const currencies = (item.currency || "").split(",").filter(Boolean).slice(0, 3);
  const flags = currencies.map((c) => CURRENCY_FLAGS[c.trim()] || "🏳️").join(" ");

  // Sentiment score visual
  const sentScore = item.sentiment_score ?? 0;
  const isPositive = sentScore > 0.15;
  const isNegative = sentScore < -0.15;

  if (variant === "compact") {
    return (
      <button
        onClick={onClick}
        className="w-full text-left p-3 rounded-xl bg-bg-surface/50 hover:bg-bg-surface/80 border border-transparent hover:border-primary-500/30 transition-all group"
      >
        <div className="flex items-start gap-3">
          <div className={cn("w-1 self-stretch rounded-full flex-shrink-0", impact.bg.replace("/15", ""))} />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-sm">{flags}</span>
              <Badge variant="neutral" className={cn("text-[10px] px-1.5 py-0", impact.color)}>
                {impact.stars}
              </Badge>
              <span className="text-[10px] text-text-muted ml-auto">{formatRelativeTime(item.scraped_at)}</span>
            </div>
            <p className="text-sm font-medium leading-snug line-clamp-2">
              {item.title_th || item.title_original}
            </p>
            {item.key_takeaway_th && (
              <p className="text-[11px] text-text-muted mt-1 line-clamp-1 italic">
                💡 {item.key_takeaway_th}
              </p>
            )}
          </div>
        </div>
      </button>
    );
  }

  return (
    <button
      onClick={onClick}
      className={cn(
        "w-full text-left rounded-2xl bg-bg-card border border-border hover:border-primary-500/40 transition-all group overflow-hidden",
        variant === "featured" && "border-primary-500/30 bg-gradient-to-br from-bg-card to-primary-900/20"
      )}
    >
      {/* Impact stripe */}
      <div className={cn("h-1", impact.bg.replace("/15", "/80"))} />

      <div className="p-4">
        {/* Header row */}
        <div className="flex items-center gap-2 mb-2 flex-wrap">
          {/* Flags */}
          <span className="text-lg">{flags}</span>

          {/* Impact stars */}
          <span className={cn("font-bold text-sm", impact.color)}>{impact.stars}</span>

          {/* Category */}
          {cat && (
            <Badge variant="neutral" className={cn("text-[10px] px-2 py-0.5", cat.color)}>
              <span className="mr-1">{cat.icon}</span>
              {cat.label}
            </Badge>
          )}

          {/* Urgent flag */}
          {item.is_urgent && (
            <Badge variant="danger" className="text-[10px] px-2 py-0.5 animate-pulse">
              <Flame className="w-3 h-3 mr-1" />
              ด่วน
            </Badge>
          )}

          {/* Time ago */}
          <div className="ml-auto flex items-center gap-1 text-[11px] text-text-muted">
            <Clock className="w-3 h-3" />
            {formatRelativeTime(item.scraped_at)}
          </div>
        </div>

        {/* Title (TH) */}
        <h3 className="text-base font-semibold leading-snug mb-1.5 group-hover:text-primary-300 transition-colors line-clamp-2">
          {item.title_th || item.title_original}
        </h3>

        {/* Original title (EN) if has TH */}
        {item.title_th && item.title_th !== item.title_original && (
          <p className="text-[11px] text-text-muted line-clamp-1 mb-2 italic">
            {item.title_original}
          </p>
        )}

        {/* Summary */}
        {(item.summary_th || item.summary_original) && (
          <p className="text-xs text-text-secondary line-clamp-2 mb-3">
            {item.summary_th || item.summary_original}
          </p>
        )}

        {/* Key takeaway */}
        {item.key_takeaway_th && (
          <div className="mb-3 p-2.5 rounded-lg bg-primary-500/10 border border-primary-500/20">
            <p className="text-xs text-primary-200">
              <span className="font-semibold">💡 ประเด็นสำคัญ: </span>
              {item.key_takeaway_th}
            </p>
          </div>
        )}

        {/* Sentiment per currency */}
        {item.sentiment && Object.keys(item.sentiment).length > 0 && (
          <div className="flex items-center gap-1.5 mb-3 flex-wrap">
            {Object.entries(item.sentiment).map(([cur, sent]) => {
              if (sent === "neutral" || !CURRENCY_FLAGS[cur]) return null;
              return (
                <Badge
                  key={cur}
                  variant={sent === "bullish" ? "buy" : sent === "bearish" ? "sell" : "neutral"}
                  className="text-[10px] px-1.5 py-0.5"
                >
                  {CURRENCY_FLAGS[cur]}
                  <span className="mx-1">{cur}</span>
                  {sent === "bullish" ? <TrendingUp className="w-2.5 h-2.5" /> : <TrendingDown className="w-2.5 h-2.5" />}
                </Badge>
              );
            })}
          </div>
        )}

        {/* Footer: stats */}
        <div className="flex items-center gap-3 text-[11px] text-text-muted pt-2 border-t border-border/40">
          <span className={cn("font-medium", src.color)}>{src.label}</span>

          {item.expected_volatility_pips !== undefined && item.expected_volatility_pips > 0 && (
            <span className="flex items-center gap-1">
              📊 ~{item.expected_volatility_pips} pips
            </span>
          )}

          {action && (
            <span className={cn("font-medium", action.color)}>
              {action.label}
            </span>
          )}

          {(isPositive || isNegative) && (
            <span className={cn("font-mono font-semibold", isPositive ? "text-buy" : "text-sell")}>
              {isPositive ? "+" : ""}
              {sentScore.toFixed(2)}
            </span>
          )}

          <div className="ml-auto flex items-center gap-1 text-primary-400 group-hover:text-primary-300">
            <Eye className="w-3 h-3" />
            <span>ดูรายละเอียด</span>
            <ArrowUpRight className="w-3 h-3" />
          </div>
        </div>
      </div>
    </button>
  );
}
