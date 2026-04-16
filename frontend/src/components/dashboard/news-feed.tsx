"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { Newspaper, RefreshCw } from "lucide-react";
import type { NewsItem } from "@/lib/api";

interface NewsFeedProps {
  items: NewsItem[];
  onRefresh?: () => void;
  loading?: boolean;
}

const impactVariant = (level: string) => {
  if (level === "high") return "danger" as const;
  if (level === "medium") return "warning" as const;
  return "neutral" as const;
};

export function NewsFeed({ items, onRefresh, loading }: NewsFeedProps) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Newspaper className="w-4 h-4 text-primary-400" />
          <CardTitle>ข่าวล่าสุด</CardTitle>
        </div>
        {onRefresh && (
          <button
            onClick={onRefresh}
            disabled={loading}
            className="p-1.5 rounded-lg hover:bg-bg-surface transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 text-text-muted ${loading ? "animate-spin" : ""}`} />
          </button>
        )}
      </CardHeader>

      <div className="flex flex-col gap-2 max-h-80 overflow-y-auto">
        {items.length === 0 && (
          <p className="text-sm text-text-muted py-4 text-center">ยังไม่มีข่าว</p>
        )}
        {items.map((item) => (
          <div
            key={item.id}
            className="flex items-start gap-3 p-3 rounded-xl bg-bg-surface/50 hover:bg-bg-surface transition-colors"
          >
            <div
              className="w-1 self-stretch rounded-full flex-shrink-0"
              style={{
                backgroundColor:
                  item.impact_level === "high"
                    ? "var(--color-danger)"
                    : item.impact_level === "medium"
                      ? "var(--color-warning)"
                      : "var(--color-border)",
              }}
            />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium leading-snug line-clamp-2">
                {item.title_th || item.title_original}
              </p>
              <div className="flex items-center gap-2 mt-1.5">
                <Badge variant={impactVariant(item.impact_level)}>
                  {item.impact_level}
                </Badge>
                <span className="text-xs text-text-muted">{item.source}</span>
                {item.sentiment_score !== undefined && item.sentiment_score !== null && (
                  <span
                    className={`text-xs ${
                      item.sentiment_score > 0
                        ? "text-buy"
                        : item.sentiment_score < 0
                          ? "text-sell"
                          : "text-text-muted"
                    }`}
                  >
                    {item.sentiment_score > 0 ? "+" : ""}
                    {item.sentiment_score.toFixed(2)}
                  </span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
