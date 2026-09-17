"""Two pinned Supabase RPCs; ACK never substitutes for driver read-back."""

from __future__ import annotations

import asyncio
import json

import httpx

from .native_source import ExportBatch, _json
from .sync_config import SyncConfig, origin, read_service_key
from .sync_driver import DestinationConflict, DestinationUnavailable
from .sync_journal import canonical

MAX_HTTP_BYTES = 262144
TOTAL_SECONDS = 10


class SupabaseDestination:
    def __init__(self, config: SyncConfig, *, transport: httpx.AsyncBaseTransport | None = None):
        self._config = config
        self._origin = origin(config.origin)
        self._key, self._legacy = read_service_key(config.service_key_file)
        self._transport = transport

    @property
    def owner_id(self) -> str:
        return str(self._config.owner_id)

    @property
    def origin(self) -> str:
        return self._origin

    def _arguments(self, batch: ExportBatch) -> dict:
        binding = {
            "identity": self._config.identity.model_dump(mode="json"),
            "offset": self._config.offset_seconds,
            "chart": self._config.chart.model_dump(mode="json"),
        }
        if batch.archive_id != str(self._config.archive_id) or canonical(
            json.loads(batch.binding_json)
        ) != canonical(binding):
            raise DestinationConflict()
        return {"p_owner_id": self.owner_id, "p_archive_id": batch.archive_id}

    async def _request(self, rpc: str, arguments: dict, *, read: bool) -> dict:
        body = canonical(arguments).encode("utf-8")
        if len(body) > MAX_HTTP_BYTES:
            raise DestinationUnavailable()
        headers = {
            "apikey": self._key,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Accept-Encoding": "identity",
        }
        if self._legacy:
            headers["Authorization"] = "Bearer " + self._key
        try:
            async with (
                asyncio.timeout(TOTAL_SECONDS),
                httpx.AsyncClient(
                    timeout=2,
                    follow_redirects=False,
                    trust_env=False,
                    transport=self._transport,
                    limits=httpx.Limits(max_connections=1, max_keepalive_connections=0),
                ) as client,
                client.stream(
                    "POST", self.origin + "/rest/v1/rpc/" + rpc, headers=headers, content=body
                ) as response,
            ):
                if response.status_code not in (200, 409):
                    raise DestinationUnavailable()
                if (
                    response.headers.get("content-encoding", "identity") != "identity"
                    or response.headers.get("content-type", "").split(";")[0].strip()
                    != "application/json"
                ):
                    raise DestinationUnavailable()
                length = response.headers.get("content-length")
                if length is not None and (
                    len(length) > 10
                    or not length.isascii()
                    or not length.isdecimal()
                    or int(length) > MAX_HTTP_BYTES
                ):
                    raise DestinationUnavailable()
                data = bytearray()
                async for chunk in response.aiter_raw():
                    if len(data) + len(chunk) > MAX_HTTP_BYTES:
                        raise DestinationUnavailable()
                    data.extend(chunk)
                try:
                    result = _json(data.decode("utf-8"), MAX_HTTP_BYTES)
                except ValueError, RecursionError:
                    if read and response.status_code == 200:
                        raise DestinationConflict() from None
                    raise DestinationUnavailable() from None
                if response.status_code == 409:
                    if result.get("code") == "23505" and result.get("message") in {
                        "NATIVE_ARCHIVE_CONFLICT",
                        "NATIVE_BAR_CONFLICT",
                    }:
                        raise DestinationConflict()
                    raise DestinationUnavailable()
                return result
        except httpx.HTTPError, TimeoutError, OSError:
            raise DestinationUnavailable() from None

    def store(self, batch: ExportBatch) -> None:
        args = self._arguments(batch)
        args.update(p_binding=json.loads(batch.binding_json), p_rows=batch.wire_rows())
        asyncio.run(self._request("sochron_store_native_m1", args, read=False))

    def read(self, batch: ExportBatch) -> object:
        args = self._arguments(batch)
        args["p_times"] = [row.cursor.time_server_s for row in batch.rows]
        return asyncio.run(self._request("sochron_read_native_m1", args, read=True))
