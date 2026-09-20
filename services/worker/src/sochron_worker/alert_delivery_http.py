"""Bounded HTTP source and receipt-capable relay clients for alert delivery."""

from __future__ import annotations

import httpx
from pydantic import ValidationError
from sochron1k.alert_delivery_source import AlertDeliverySourceSnapshot

from .alert_delivery_driver import (
    AlertDestinationConflict,
    AlertDestinationUnavailable,
    AlertSourceUnavailable,
)
from .alert_delivery_journal import AlertDeliveryReceipt, DeliveryIntent
from .native_source import _json
from .sync_journal import canonical

MAX_HTTP_BYTES = 65_536


def _json_body(headers: httpx.Headers, data: bytes, *, unavailable: type[RuntimeError]) -> bytes:
    if (
        headers.get("content-encoding", "identity") != "identity"
        or headers.get("content-type", "").split(";", 1)[0].strip() != "application/json"
    ):
        raise unavailable()
    length = headers.get("content-length")
    if length is not None and (
        len(length) > 10
        or not length.isascii()
        or not length.isdecimal()
        or int(length) > MAX_HTTP_BYTES
    ):
        raise unavailable()
    if len(data) > MAX_HTTP_BYTES or (length is not None and int(length) != len(data)):
        raise unavailable()
    return data


def _bounded_request(
    client: httpx.Client,
    method: str,
    url: str,
    *,
    headers: dict[str, str],
    content: bytes | None = None,
) -> tuple[int, httpx.Headers, bytes]:
    with client.stream(method, url, headers=headers, content=content) as response:
        data = bytearray()
        for chunk in response.iter_bytes():
            if len(data) + len(chunk) > MAX_HTTP_BYTES:
                raise httpx.DecodingError("bounded alert response exceeded")
            data.extend(chunk)
        return response.status_code, response.headers, bytes(data)


class HttpAlertSource:
    def __init__(
        self,
        origin: str,
        token: str,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.origin = origin
        self._token = token
        self._transport = transport

    def read(self) -> AlertDeliverySourceSnapshot:
        try:
            with httpx.Client(
                timeout=2,
                follow_redirects=False,
                trust_env=False,
                transport=self._transport,
                limits=httpx.Limits(max_connections=1, max_keepalive_connections=0),
            ) as client:
                status, headers, body = _bounded_request(
                    client,
                    "GET",
                    self.origin + "/internal/v1/alerts",
                    headers={
                        "Authorization": "Bearer " + self._token,
                        "Accept": "application/json",
                        "Accept-Encoding": "identity",
                    },
                )
            if status != 200:
                raise AlertSourceUnavailable()
            data = _json(
                _json_body(headers, body, unavailable=AlertSourceUnavailable).decode(),
                MAX_HTTP_BYTES,
            )
            return AlertDeliverySourceSnapshot.model_validate(data)
        except (
            httpx.HTTPError,
            OSError,
            UnicodeError,
            ValueError,
            ValidationError,
            RecursionError,
        ):
            raise AlertSourceUnavailable() from None


class HttpAlertDestination:
    def __init__(
        self,
        origin: str,
        destination_ref: str,
        token: str,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.origin = origin
        self.destination_ref = destination_ref
        self._token = token
        self._transport = transport

    def _request(
        self, method: str, intent: DeliveryIntent, *, content: bytes | None = None
    ) -> tuple[int, httpx.Headers, bytes]:
        headers = {
            "Authorization": "Bearer " + self._token,
            "Accept": "application/json",
            "Accept-Encoding": "identity",
            "Idempotency-Key": intent.delivery_id,
        }
        if content is not None:
            headers["Content-Type"] = "application/json"
        try:
            with httpx.Client(
                timeout=2,
                follow_redirects=False,
                trust_env=False,
                transport=self._transport,
                limits=httpx.Limits(max_connections=1, max_keepalive_connections=0),
            ) as client:
                return _bounded_request(
                    client,
                    method,
                    self.origin + "/v1/sochron/notifications/" + intent.delivery_id,
                    headers=headers,
                    content=content,
                )
        except httpx.HTTPError, OSError:
            raise AlertDestinationUnavailable() from None

    def store(self, intent: DeliveryIntent) -> None:
        payload = canonical(intent.payload.model_dump(mode="json")).encode()
        if len(payload) > MAX_HTTP_BYTES:
            raise AlertDestinationConflict()
        status, _, _ = self._request("PUT", intent, content=payload)
        if status == 409:
            raise AlertDestinationConflict()
        if status not in {200, 201, 204}:
            raise AlertDestinationUnavailable()

    def read(self, intent: DeliveryIntent) -> AlertDeliveryReceipt | None:
        status, headers, body = self._request("GET", intent)
        if status == 404:
            return None
        if status == 409:
            raise AlertDestinationConflict()
        if status != 200:
            raise AlertDestinationUnavailable()
        try:
            data = _json(
                _json_body(headers, body, unavailable=AlertDestinationUnavailable).decode(),
                MAX_HTTP_BYTES,
            )
            return AlertDeliveryReceipt.model_validate(data)
        except (
            UnicodeError,
            ValueError,
            ValidationError,
            RecursionError,
        ):
            raise AlertDestinationUnavailable() from None
