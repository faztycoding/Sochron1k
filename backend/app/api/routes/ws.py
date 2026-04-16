import asyncio
import json
import logging
from typing import Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)
router = APIRouter(tags=["websocket"])


class NewsConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"[ws] Client connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket) -> None:
        self.active_connections.discard(websocket)
        logger.info(f"[ws] Client disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict) -> None:
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.add(connection)

        for conn in disconnected:
            self.active_connections.discard(conn)

    async def send_breaking_news(self, news_item: dict) -> None:
        await self.broadcast({
            "type": "breaking_news",
            "data": news_item,
        })

    async def send_pipeline_update(self, status: dict) -> None:
        await self.broadcast({
            "type": "pipeline_update",
            "data": status,
        })


ws_manager = NewsConnectionManager()


@router.websocket("/ws/news")
async def news_websocket(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                msg_type = msg.get("type", "")

                if msg_type == "ping":
                    await websocket.send_json({"type": "pong"})
                elif msg_type == "subscribe":
                    pair = msg.get("pair", "all")
                    await websocket.send_json({
                        "type": "subscribed",
                        "pair": pair,
                        "message": f"ติดตามข่าว {pair} แล้ว",
                    })
                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"ไม่รู้จักคำสั่ง: {msg_type}",
                    })
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "รูปแบบข้อมูลไม่ถูกต้อง",
                })
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
