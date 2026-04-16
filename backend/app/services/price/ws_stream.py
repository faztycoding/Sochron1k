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
        """Try WebSocket first, fallback to REST polling."""
        settings = get_settings()
        api_key = settings.TWELVE_DATA_API_KEY

        while self._running:
            # Try WebSocket
            try:
                await self._ws_connect(api_key)
            except Exception as e:
                logger.warning(f"[ws_stream] WebSocket failed: {e}")

            if not self._running:
                break

            # Fallback: REST poll every 3s (uses cache, minimal credits)
            logger.info("[ws_stream] Falling back to REST polling")
            try:
                await self._rest_poll()
            except Exception as e:
                logger.error(f"[ws_stream] REST poll error: {e}")
                await asyncio.sleep(5)

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
                            prev = self._prices.get(pair, {}).get("price")
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
                            self._prices[pair] = price_data
                            await self._broadcast({"type": "price", "data": price_data})

                    elif event == "subscribe-status":
                        logger.info(f"[ws_stream] Subscribe: {data.get('status')}")
                    elif event == "heartbeat":
                        pass

                except Exception as e:
                    logger.debug(f"[ws_stream] Parse error: {e}")

    async def _rest_poll(self) -> None:
        from app.services.price.manager import PriceManager

        pm = PriceManager()
        try:
            while self._running:
                try:
                    prices = await pm.get_realtime_prices()
                    for pair, pdata in prices.items():
                        prev = self._prices.get(pair, {}).get("price")
                        pdata["source"] = "rest"
                        self._prices[pair] = pdata
                    # Broadcast all at once
                    await self._broadcast({
                        "type": "prices",
                        "data": prices,
                        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
                    })
                except Exception as e:
                    logger.debug(f"[ws_stream] Poll error: {e}")
                await asyncio.sleep(3)
        finally:
            await pm.close()
