"use client";

import { Badge } from "@/components/ui/badge";
import { Clock } from "lucide-react";
import type { SessionInfo } from "@/lib/api";

interface SessionInfoBarProps {
  session: SessionInfo | null;
}

const sessionNames: Record<string, string> = {
  tokyo_fix: "Tokyo Fix",
  asian: "Asian Session",
  london_open: "London Open",
  london: "London Session",
  ny_overlap: "NY Overlap",
  ny: "New York",
  dead_zone: "Dead Zone ⚠️",
};

export function SessionInfoBar({ session }: SessionInfoBarProps) {
  if (!session) return null;

  const name = sessionNames[session.session] || session.session;
  const isDead = session.is_dead_zone;

  return (
    <div className="flex items-center gap-3 px-4 py-2 rounded-xl bg-bg-surface/50 text-sm">
      <Clock className="w-4 h-4 text-text-muted" />
      <span className="text-text-secondary">
        {String(session.thai_hour).padStart(2, "0")}:00 TH
      </span>
      <Badge variant={isDead ? "danger" : "default"}>{name}</Badge>
      {isDead && <span className="text-xs text-danger">ไม่แนะนำเทรด</span>}
      {!isDead && (
        <span className="flex items-center gap-1">
          <span className="live-dot bg-success" />
          <span className="text-xs text-success">ตลาดเปิด</span>
        </span>
      )}
    </div>
  );
}
