"use client";

import { Badge } from "@/components/ui/badge";
import { Clock } from "lucide-react";
import type { SessionInfo } from "@/lib/api";

interface SessionInfoBarProps {
  session: SessionInfo | null;
}

const sessionInfo: Record<string, { name: string; desc: string }> = {
  tokyo_fix: { name: "Tokyo Fix", desc: "JPY volatile — ระวังสภาพคล่อง" },
  asian: { name: "Asian Session", desc: "Volume ต่ำ — เหมาะ scalping JPY" },
  london_open: { name: "London Open", desc: "Volume สูงสุด — เหมาะเปิดสถานะ" },
  london: { name: "London Session", desc: "EUR/USD active — trend ชัดเจน" },
  ny_overlap: { name: "NY Overlap", desc: "Volume สูงสุดในวัน — โอกาสทอง" },
  ny: { name: "New York", desc: "USD active — ระวังข่าว Fed/CPI" },
  dead_zone: { name: "Dead Zone", desc: "ตลาดปิด 01:00-07:00 TH — ไม่แนะนำเทรด" },
};

export function SessionInfoBar({ session }: SessionInfoBarProps) {
  if (!session) return null;

  const info = sessionInfo[session.session] || { name: session.session, desc: "" };
  const isDead = session.is_dead_zone;

  return (
    <div className="flex items-center gap-3 px-4 py-2.5 rounded-xl bg-bg-surface/50 border border-border/30 text-sm">
      <Clock className="w-4 h-4 text-text-muted" />
      <span className="text-text-secondary font-mono">
        {String(session.thai_hour).padStart(2, "0")}:00 TH
      </span>
      <Badge variant={isDead ? "danger" : "default"}>{info.name}</Badge>
      <span className={`text-xs ${isDead ? "text-danger" : "text-text-muted"}`}>
        {info.desc}
      </span>
      {!isDead && (
        <span className="flex items-center gap-1 ml-auto">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute h-full w-full rounded-full bg-emerald-400 opacity-60" />
            <span className="relative rounded-full h-2 w-2 bg-emerald-500" />
          </span>
          <span className="text-xs text-success">LIVE</span>
        </span>
      )}
    </div>
  );
}
