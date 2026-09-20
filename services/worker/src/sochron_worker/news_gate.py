"""Bounded attested-calendar client and deterministic News Gate publisher."""

from __future__ import annotations

import asyncio
import hashlib
import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Annotated, Literal, Self

import httpx
from pydantic import AwareDatetime, Field, field_validator, model_validator
from sochron1k.models import StrictModel
from sochron1k.policy_evidence import (
    NewsGateFrame,
    _canonical,
    _directory_identity,
    _publish_atomic,
)

from .native_source import _json
from .news_gate_config import NewsGateConfig, read_calendar_token

MAX_HTTP_BYTES = 262_144
MAX_EVENTS = 512
MAX_PUBLICATION_AGE_SECONDS = 300
TOTAL_SECONDS = 10
ENDPOINT = "/v1/calendar-window"
SafeText = Annotated[
    str,
    Field(min_length=1, max_length=128, pattern=r"^[^\x00-\x1f\x7f]+$"),
]
RevisionText = Annotated[
    str,
    Field(min_length=1, max_length=48, pattern=r"^[A-Za-z0-9._~-]+$"),
]
Currency = Annotated[str, Field(pattern=r"^[A-Z]{3}$")]


class NewsGateUnavailable(RuntimeError):
    def __init__(self) -> None:
        super().__init__("NEWS_GATE_UNAVAILABLE")


class CalendarEvent(StrictModel):
    event_id: SafeText
    scheduled_at_utc: AwareDatetime
    currency: Currency
    impact: Literal["low", "medium", "high"]
    status: Literal["scheduled", "cancelled"]

    @field_validator("scheduled_at_utc")
    @classmethod
    def normalize_time(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)


class CalendarWindow(StrictModel):
    protocol: Literal["sochron.calendar-window.v1"]
    source_id: SafeText
    revision: RevisionText
    published_at_utc: AwareDatetime
    coverage_from_utc: AwareDatetime
    coverage_until_utc: AwareDatetime
    complete: Literal[True]
    events: tuple[CalendarEvent, ...] = Field(max_length=MAX_EVENTS)

    @field_validator("published_at_utc", "coverage_from_utc", "coverage_until_utc")
    @classmethod
    def normalize_time(cls, value: datetime) -> datetime:
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def coherent_window(self) -> Self:
        identities = tuple(event.event_id for event in self.events)
        order = tuple((event.scheduled_at_utc, event.event_id) for event in self.events)
        if (
            self.coverage_from_utc >= self.coverage_until_utc
            or len(set(identities)) != len(identities)
            or order != tuple(sorted(order))
            or any(
                not self.coverage_from_utc
                <= event.scheduled_at_utc
                < self.coverage_until_utc
                for event in self.events
            )
        ):
            raise ValueError("invalid calendar window")
        return self


def _utc_text(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _canonical_window(window: CalendarWindow) -> bytes:
    return json.dumps(
        window.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


class CalendarGateway:
    def __init__(
        self,
        config: NewsGateConfig,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._config = config
        self._token = read_calendar_token(config.credential_file)
        self._transport = transport

    async def fetch(
        self,
        requested_from: datetime,
        requested_until: datetime,
    ) -> CalendarWindow:
        headers = {
            "Authorization": "Bearer " + self._token,
            "Accept": "application/json",
            "Accept-Encoding": "identity",
        }
        params = {
            "from": _utc_text(requested_from),
            "until": _utc_text(requested_until),
            "currencies": ",".join(self._config.currencies),
            "impacts": ",".join(self._config.impacts),
        }
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
                    "GET",
                    self._config.origin + ENDPOINT,
                    headers=headers,
                    params=params,
                ) as response,
            ):
                if response.status_code != 200:
                    raise NewsGateUnavailable()
                if (
                    response.headers.get("content-encoding", "identity") != "identity"
                    or response.headers.get("content-type", "").split(";")[0].strip()
                    != "application/json"
                ):
                    raise NewsGateUnavailable()
                length = response.headers.get("content-length")
                if length is not None and (
                    len(length) > 10
                    or not length.isascii()
                    or not length.isdecimal()
                    or int(length) > MAX_HTTP_BYTES
                ):
                    raise NewsGateUnavailable()
                body = bytearray()
                async for chunk in response.aiter_raw():
                    if len(body) + len(chunk) > MAX_HTTP_BYTES:
                        raise NewsGateUnavailable()
                    body.extend(chunk)
            window = CalendarWindow.model_validate(
                _json(body.decode("utf-8"), MAX_HTTP_BYTES)
            )
            if (
                any(event.currency not in self._config.currencies for event in window.events)
                or any(event.impact not in self._config.impacts for event in window.events)
            ):
                raise NewsGateUnavailable()
            return window
        except (
            httpx.HTTPError,
            TimeoutError,
            OSError,
            UnicodeError,
            ValueError,
            TypeError,
            RecursionError,
        ):
            raise NewsGateUnavailable() from None


class NewsGateCollector:
    def __init__(
        self,
        config: NewsGateConfig,
        gateway: CalendarGateway,
        *,
        utc_now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._config = config
        self._gateway = gateway
        self._utc_now = utc_now
        self._output_parent = _directory_identity(config.output_file.parent)

    def _now(self) -> datetime:
        value = self._utc_now()
        if value.tzinfo is None or value.utcoffset() is None:
            raise NewsGateUnavailable()
        return value.astimezone(UTC)

    def refresh(self) -> NewsGateFrame:
        requested_at = self._now()
        requested_from = requested_at - timedelta(
            seconds=self._config.blackout_after_seconds
        )
        requested_until = requested_at + timedelta(
            seconds=self._config.blackout_before_seconds, microseconds=1
        )
        try:
            window = asyncio.run(self._gateway.fetch(requested_from, requested_until))
            received_at = self._now()
            required_from = received_at - timedelta(
                seconds=self._config.blackout_after_seconds
            )
            required_until = received_at + timedelta(
                seconds=self._config.blackout_before_seconds, microseconds=1
            )
            publication_age = (received_at - window.published_at_utc).total_seconds()
            if (
                publication_age < 0
                or publication_age > MAX_PUBLICATION_AGE_SECONDS
                or window.coverage_from_utc > required_from
                or window.coverage_until_utc < required_until
            ):
                raise NewsGateUnavailable()
            blocking = tuple(
                event.event_id
                for event in window.events
                if event.status == "scheduled"
                and event.scheduled_at_utc
                - timedelta(seconds=self._config.blackout_before_seconds)
                <= received_at
                < event.scheduled_at_utc
                + timedelta(seconds=self._config.blackout_after_seconds)
            )
            digest = hashlib.sha256(_canonical_window(window)).hexdigest()
            gate = NewsGateFrame(
                protocol="sochron.news-gate.v1",
                source_id=window.source_id,
                revision=f"{window.revision}.sha256-{digest}",
                observed_at_utc=received_at,
                coverage_from_utc=window.coverage_from_utc,
                coverage_until_utc=window.coverage_until_utc,
                complete=True,
                blocked=bool(blocking),
                blocking_event_ids=blocking,
            )
            _publish_atomic(
                self._config.output_file,
                _canonical(gate),
                self._output_parent,
            )
            return gate
        except NewsGateUnavailable:
            raise
        except (OSError, ValueError, TypeError, RuntimeError, RecursionError):
            raise NewsGateUnavailable() from None
