"""Pinned PA01 Supabase RPC transport; store ACK never replaces read-back."""

from __future__ import annotations

import asyncio

import httpx

from .native_source import _json
from .pa01_config import PA01ProducerConfig
from .pa01_driver import PA01DestinationConflict, PA01DestinationUnavailable
from .pa01_envelope import PA01DecisionEnvelope
from .sync_config import origin, read_service_key
from .sync_journal import canonical

MAX_HTTP_BYTES = 262_144
TOTAL_SECONDS = 10
CONFIRMED_REJECTIONS = {
    ("23505", "PA01_DECISION_CONFLICT"),
    ("23514", "PA01_EXECUTION_PARAMETERS_INVALID"),
    ("23514", "PA01_EXPERIMENT_DENIED"),
    ("23514", "PA01_FEATURES_INVALID"),
    ("23514", "PA01_POLICY_CONTEXT_INVALID"),
    ("23514", "PA01_POLICY_SIGNAL_INVALID"),
    ("23514", "PA01_SIGNAL_IMMUTABLE"),
    ("23514", "PA01_SIGNAL_INVALID"),
    ("23514", "PA01_SNAPSHOT_IMMUTABLE"),
    ("23514", "PA01_SNAPSHOT_INVALID"),
    ("23514", "PA01_STRATEGY_DENIED"),
    ("22023", "PA01_DECISION_INVALID"),
    ("22023", "PA01_READ_INVALID"),
}


class PA01SupabaseDestination:
    def __init__(
        self,
        config: PA01ProducerConfig,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._config = config
        self._origin = origin(config.origin)
        self._key, self._legacy = read_service_key(config.service_key_file)
        self._transport = transport

    @property
    def owner_id(self) -> str:
        return str(self._config.owner_id)

    @property
    def strategy_version_id(self) -> int:
        return self._config.strategy_version_id

    @property
    def experiment_id(self) -> int:
        return self._config.experiment_id

    @property
    def origin(self) -> str:
        return self._origin

    async def _request(self, rpc: str, arguments: dict) -> dict:
        body = canonical(arguments).encode("utf-8")
        if len(body) > MAX_HTTP_BYTES:
            raise PA01DestinationUnavailable()
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
                if response.status_code not in (200, 400, 409):
                    raise PA01DestinationUnavailable()
                if (
                    response.headers.get("content-encoding", "identity") != "identity"
                    or response.headers.get("content-type", "").split(";")[0].strip()
                    != "application/json"
                ):
                    raise PA01DestinationUnavailable()
                length = response.headers.get("content-length")
                if length is not None and (
                    len(length) > 10
                    or not length.isascii()
                    or not length.isdecimal()
                    or int(length) > MAX_HTTP_BYTES
                ):
                    raise PA01DestinationUnavailable()
                data = bytearray()
                async for chunk in response.aiter_raw():
                    if len(data) + len(chunk) > MAX_HTTP_BYTES:
                        raise PA01DestinationUnavailable()
                    data.extend(chunk)
                try:
                    result = _json(data.decode("utf-8"), MAX_HTTP_BYTES)
                except ValueError, RecursionError:
                    raise PA01DestinationUnavailable() from None
                if response.status_code != 200:
                    if (result.get("code"), result.get("message")) in CONFIRMED_REJECTIONS:
                        raise PA01DestinationConflict()
                    raise PA01DestinationUnavailable()
                return result
        except httpx.HTTPError, TimeoutError, OSError:
            raise PA01DestinationUnavailable() from None

    def store(self, envelope: PA01DecisionEnvelope) -> None:
        asyncio.run(
            self._request(
                "sochron_store_pa01_decision",
                {
                    "p_owner_id": self.owner_id,
                    "p_strategy_version_id": self.strategy_version_id,
                    "p_experiment_id": self.experiment_id,
                    "p_decision": envelope.model_dump(mode="json"),
                },
            )
        )

    def read(self, envelope: PA01DecisionEnvelope) -> object:
        return asyncio.run(
            self._request(
                "sochron_read_pa01_decision",
                {
                    "p_owner_id": self.owner_id,
                    "p_signal_id": envelope.signal.signal_id,
                },
            )
        )
