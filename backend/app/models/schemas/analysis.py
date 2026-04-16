from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class AnalysisRequest(BaseModel):
    pair: str
    timeframe: str = "1h"
    consecutive_losses: int = 0
    daily_loss_pct: float = 0.0


class DiagnosticItem(BaseModel):
    check: str
    severity: str
    message: str
    recommendation: Optional[str] = None


class KillSwitchResult(BaseModel):
    kill_switch_active: bool
    triggers: List[Dict[str, str]]
    trigger_count: int
    message: str


class AnalysisResponse(BaseModel):
    pair: str
    timeframe: str
    direction: str
    confidence: float
    strength: str
    recommendation: str
    price: float
    suggested_entry: Optional[float] = None
    suggested_sl: Optional[float] = None
    suggested_tp: Optional[float] = None
    sl_pips: Optional[float] = None
    tp_pips: Optional[float] = None
    risk_reward: Optional[float] = None
    analysis_duration: float
    analyzed_at: str
    kill_switch: KillSwitchResult
    indicators_summary: Dict[str, Any]
    confidence_breakdown: Dict[str, float]
