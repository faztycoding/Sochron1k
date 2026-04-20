"""Twelve Data WebSocket price streaming — 0 REST credits."""
import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Set

from app.config import get_settings, TARGET_PAIRS

logger = logging.getLogger(__name__)


class PriceStream:
    """Singleton: connects to Twelve Data WebSocket, broadcasts to SSE listeners."""

    _instance: Optional["PriceStream"] = None
    _prices: Dict[str, Dict[str, Any]] = {}
    _listeners: Set[asyncio.Queue] = set()
    _running: bool = False
    _task: Optional[asyncio.Task] = None

    def __new__(cls) -> "PriceStream":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def prices(self) -> Dict[str, Dict[str, Any]]:
        return dict(self._prices)

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=50)
        self._listeners.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._listeners.discard(q)

    async def _broadcast(self, data: Dict[str, Any]) -> None:
        dead: list = []
        for q in self._listeners:
            try:
                q.put_nowait(data)
            except asyncio.QueueFull:
                dead.append(q)
        for q in dead:
            self._listeners.discard(q)

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("[ws_stream] Price stream started")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("[ws_stream] Price stream stopped")

    async def _run_loop(self) -> None:
        """Run WebSocket + REST poll IN PARALLEL.

        Free-tier Twelve Data only allows 1 symbol on WebSocket — other pairs
        fail to subscribe but WS stays open. Without parallel REST poll, those
        pairs would stuck at baseline forever. Parallel setup guarantees every
        pair gets updates within <=REST_POLL_INTERVAL seconds.
        """
        settings = get_settings()
        api_key = settings.TWELVE_DATA_API_KEY

        # Prime baseline once so percent_change works from first tick
        await self._prime_baseline()

        async def ws_task():
            while self._running:
                try:
                    await self._ws_connect(api_key)
                except Exception as e:
                    logger.warning(f"[ws_stream] WebSocket err, reconnect in 10s: {e}")
                    await asyncio.sleep(10)

        async def rest_task():
            while self._running:
                try:
                    await self._rest_poll()
                except Exception as e:
                    logger.error(f"[ws_stream] REST poll err, retry in 5s: {e}")
                    await asyncio.sleep(5)

        await asyncio.gather(ws_task(), rest_task(), return_exceptions=True)

    async def _ws_connect(self, api_key: str) -> None:
        import websockets

        url = f"wss://ws.twelvedata.com/v1/quotes/price?apikey={api_key}"
        symbols = ",".join(TARGET_PAIRS)

        async with websockets.connect(url, ping_interval=30) as ws:
            await ws.send(json.dumps({
                "action": "subscribe",
                "params": {"symbols": symbols},
            }))
            logger.info(f"[ws_stream] WebSocket connected: {symbols}")

            async for msg in ws:
                if not self._running:
                    break
                try:
                    data = json.loads(msg)
                    event = data.get("event")

                    if event == "price":
                        pair = data.get("symbol", "")
                        price = float(data.get("price", 0))
                        if pair and price > 0:
                            is_jpy = "JPY" in pair
                            spread_pips = 1.5 if is_jpy else 0.00015
                            price_data = {
                                "pair": pair,
                                "price": price,
                                "bid": round(price - spread_pips / 2, 3 if is_jpy else 5),
                                "ask": round(price + spread_pips / 2, 3 if is_jpy else 5),
                                "spread": round(spread_pips * (100 if is_jpy else 10000), 1),
                                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
                                "source": "websocket",
                            }
                            # Preserve change/percent_change from REST baseline if available,
                            # but recompute against stored previous_close for live updates
                            prev_cached = self._prices.get(pair, {})
                            ref_close = prev_cached.get("previous_close")
                            if ref_close and ref_close > 0:
                                change = price - ref_close
                                pct = (change / ref_close) * 100
                                price_data["previous_close"] = ref_close
                                price_data["change"] = round(change, 3 if is_jpy else 5)
                                price_data["percent_change"] = round(pct, 4)
                                if prev_cached.get("reference_type"):
                                    price_data["reference_type"] = prev_cached["reference_type"]
                                if prev_cached.get("day_high"):
                                    price_data["day_high"] = max(prev_cached["day_high"], price)
                                if prev_cached.get("day_low"):
                                    price_data["day_low"] = min(prev_cached["day_low"], price)
                                if prev_cached.get("day_open"):
                                    price_data["day_open"] = prev_cached["day_open"]

                            self._prices[pair] = price_data
                            await self._broadcast({"type": "price", "data": price_data})

                    elif event == "subscribe-status":
                        logger.info(f"[ws_stream] Subscribe: {data.get('status')}")
                    elif event == "heartbeat":
                        pass

                except Exception as e:
                    logger.debug(f"[ws_stream] Parse error: {e}")

    async def _prime_baseline(self) -> None:
        """Fetch baseline prices (with previous_close + 24h-rolling) once.

        Stores into self._prices so WebSocket messages can compute percent_change
        immediately on first tick.
        """
        try:
            from app.services.price.manager import PriceManager

            pm = PriceManager()
            try:
                prices = await pm.get_realtime_prices()
                for pair, pdata in prices.items():
                    pdata["source"] = "rest"
                    self._prices[pair] = pdata
                logger.info(
                    f"[ws_stream] Baseline primed for {len(prices)} pairs"
                )
            finally:
                await pm.close()
        except Exception as e:
            logger.warning(f"[ws_stream] Baseline prime failed: {e}")

    async def _rest_poll(self) -> None:
        """Poll TwelveData batch /quote every 8s for ALL pairs.

        Rate math (Crow-55 plan, 55 credits/min budget):
          - Batch /quote with 5 symbols = 5 credits per call
          - Poll every 8s = 7.5 polls/min = ~38 credits/min for realtime
          - Leaves ~17 credits/min for candle fetches (analysis page, prefetch)

        WebSocket gives sub-second EUR/USD updates for free; this poll
        keeps the other 4 pairs fresh within ~8 seconds.

        On rate-limit failure we DON'T call yfinance (broken on Yahoo's side)
        — just skip the cycle and keep last broadcast prices.
        """
        from app.services.price.manager import PriceManager

        pm = PriceManager()
        consecutive_empty = 0
        try:
            while self._running:
                try:
                    prices = await pm.get_realtime_prices(bypass_cache=True)
                    if not prices:
                        consecutive_empty += 1
                        if consecutive_empty == 1:
                            logger.warning(
                                "[ws_stream] REST poll returned empty (rate-limited?) — keeping last prices"
                            )
                        await asyncio.sleep(8)
                        continue
                    consecutive_empty = 0
                    for pair, pdata in prices.items():
                        pdata.setdefault("source", "rest")
                        existing = self._prices.get(pair, {})
                        if existing.get("source") == "websocket":
                            # WS has fresher price — only refresh perf metadata
                            existing["previous_close"] = pdata.get("previous_close", existing.get("previous_close"))
                            existing["day_open"] = pdata.get("day_open", existing.get("day_open"))
                            existing["day_high"] = max(pdata.get("day_high", 0), existing.get("day_high", 0))
                            existing["day_low"] = min(pdata.get("day_low", 1e9), existing.get("day_low", 1e9))
                            if pdata.get("reference_type"):
                                existing["reference_type"] = pdata["reference_type"]
                        else:
                            self._prices[pair] = pdata
                    await self._broadcast({
                        "type": "prices",
                        "data": self._prices,
                        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
                    })
                except Exception as e:
                    logger.warning(f"[ws_stream] Poll cycle error: {e}")
                await asyncio.sleep(8)
        finally:
            await pm.close()
