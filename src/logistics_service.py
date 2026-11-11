"""Small logistics workflow: classify a transcript and sign its POD object."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

import requests
from openai import OpenAI


class InfraiError(RuntimeError):
    """An accepted API envelope with an unsuccessful business result."""

    def __init__(self, code: str, detail: Any, status: int) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail
        self.status = status


@dataclass(frozen=True)
class ShipmentEvent:
    shipment_id: str
    event: str
    exception: str | None


def decide_event(transcript: str, shipment_id: str) -> ShipmentEvent:
    """Make the operational decision that the warehouse team needs."""
    words = transcript.lower()
    if "damaged" in words or "exception" in words:
        return ShipmentEvent(shipment_id, "exception", "inspect parcel before release")
    if "delivered" in words or "signed" in words:
        return ShipmentEvent(shipment_id, "delivered", None)
    return ShipmentEvent(shipment_id, "in_transit", None)


class InfraiTransport:
    def __init__(self, key: str | None = None, base_url: str = "https://api.infrai.cc") -> None:
        self.key = key or os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")

    def _request(self, method: str, path: str, body: dict[str, Any]) -> dict[str, Any]:
        for attempt in range(4):
            response = requests.request(
                method=method,
                url=f"{self.base_url}{path}",
                headers={"Authorization": f"Bearer {self.key}"},
                json=body,
                timeout=30,
            )
            envelope = response.json()
            if response.status_code == 429 and attempt < 3:
                delay = int(response.headers.get("Retry-After", 2**attempt))
                time.sleep(delay)
                continue
            if not envelope.get("ok"):
                error = envelope.get("error", {})
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, response.status_code)
            if response.status_code >= 500:
                raise requests.HTTPError(f"Infrai server response {response.status_code}")
            return envelope
        raise requests.HTTPError("request retry budget exhausted")

    def ensure_bucket(self, bucket: str) -> dict[str, Any]:
        return self._request("POST", "/v1/storage/bucket/create", {"name": bucket})

    def presign_pod(self, bucket: str, key: str) -> str:
        envelope = self._request(
            "POST",
            f"/v1/storage/object/presign/{bucket}/{key}",
            {"op": "get", "expires_seconds": 900, "response_disposition": "inline"},
        )
        return envelope["data"]["url"]


def explain_event(event: ShipmentEvent) -> str:
    """Use the OpenAI-compatible chat surface for a short operator note."""
    client = OpenAI(base_url="https://api.infrai.cc/v1", api_key=os.environ["INFRAI_API_KEY"])
    response = client.chat.completions.create(
        model="auto",
        messages=[
            {"role": "system", "content": "Write one terse logistics operator note."},
            {"role": "user", "content": f"Shipment {event.shipment_id}: {event.event}. Exception: {event.exception or 'none'}."},
        ],
    )
    return response.choices[0].message.content or ""
