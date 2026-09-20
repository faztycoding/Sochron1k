"""Pinned Supabase RPC transport for research-evaluation insert and read-back."""

from __future__ import annotations

import asyncio

import httpx

from .native_source import _json
from .research_evaluation import ResearchEvaluationEnvelope
from .research_evaluation_config import ResearchEvaluationConfig
from .research_evaluation_driver import (
    ResearchEvaluationDestinationConflict,
    ResearchEvaluationDestinationUnavailable,
)
from .sync_config import origin, read_service_key
from .sync_journal import canonical

MAX_HTTP_BYTES = 262_144
TOTAL_SECONDS = 10
CONFIRMED_REJECTIONS = {
    ("22023", "RESEARCH_EVALUATION_INVALID"),
    ("22023", "RESEARCH_EVALUATION_READ_INVALID"),
    ("23505", "RESEARCH_EVALUATION_CONFLICT"),
    ("23514", "RESEARCH_EVALUATION_EXPERIMENT_DENIED"),
    ("23514", "RESEARCH_EVALUATION_STRATEGY_DENIED"),
}


class ResearchEvaluationSupabaseDestination:
    def __init__(
        self,
        config: ResearchEvaluationConfig,
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
    def experiment_id(self) -> int | None:
        return self._config.experiment_id

    @property
    def origin(self) -> str:
        return self._origin

    async def _request(self, rpc: str, arguments: dict) -> dict:
        body = canonical(arguments).encode("utf-8")
        if len(body) > MAX_HTTP_BYTES:
            raise ResearchEvaluationDestinationUnavailable()
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
                    raise ResearchEvaluationDestinationUnavailable()
                if (
                    response.headers.get("content-encoding", "identity") != "identity"
                    or response.headers.get("content-type", "").split(";")[0].strip()
                    != "application/json"
                ):
                    raise ResearchEvaluationDestinationUnavailable()
                length = response.headers.get("content-length")
                if length is not None and (
                    len(length) > 10
                    or not length.isascii()
                    or not length.isdecimal()
                    or int(length) > MAX_HTTP_BYTES
                ):
                    raise ResearchEvaluationDestinationUnavailable()
                data = bytearray()
                async for chunk in response.aiter_raw():
                    if len(data) + len(chunk) > MAX_HTTP_BYTES:
                        raise ResearchEvaluationDestinationUnavailable()
                    data.extend(chunk)
                try:
                    result = _json(data.decode("utf-8"), MAX_HTTP_BYTES)
                except ValueError, RecursionError:
                    raise ResearchEvaluationDestinationUnavailable() from None
                if response.status_code != 200:
                    if (result.get("code"), result.get("message")) in CONFIRMED_REJECTIONS:
                        raise ResearchEvaluationDestinationConflict()
                    raise ResearchEvaluationDestinationUnavailable()
                return result
        except httpx.HTTPError, TimeoutError, OSError:
            raise ResearchEvaluationDestinationUnavailable() from None

    def store(self, envelope: ResearchEvaluationEnvelope) -> None:
        asyncio.run(
            self._request(
                "sochron_store_research_evaluation",
                {
                    "p_owner_id": self.owner_id,
                    "p_strategy_version_id": self.strategy_version_id,
                    "p_experiment_id": self.experiment_id,
                    "p_evaluation": envelope.model_dump(mode="json"),
                },
            )
        )

    def read(self, envelope: ResearchEvaluationEnvelope) -> object:
        return asyncio.run(
            self._request(
                "sochron_read_research_evaluation",
                {
                    "p_owner_id": self.owner_id,
                    "p_evaluation_fingerprint": envelope.evaluation_fingerprint,
                },
            )
        )
