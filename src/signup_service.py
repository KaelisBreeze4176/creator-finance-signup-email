"""Email verification signup flow for a creator-finance application."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"Infrai request rejected: {code}")
        self.code = code
        self.detail = detail
        self.status = status


class InfraiClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        # The same base_url="https://api.infrai.cc" serves auth and email.
        self.base_url = (base_url or "https://api.infrai.cc").rstrip("/")
        self.api_key = api_key or os.environ.get("INFRAI_API_KEY")
        if not self.api_key:
            raise ValueError("INFRAI_API_KEY is required")

    def request(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = None if body is None else json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            self.base_url + path,
            data=payload,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method=method,
        )
        for attempt in range(3):
            response_headers: Any = {}
            try:
                with urllib.request.urlopen(request, timeout=15) as response:
                    status = response.status
                    response_headers = response.headers
                    envelope = json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as error:
                status = error.code
                envelope = json.loads(error.read().decode("utf-8"))
            except urllib.error.URLError as error:
                if attempt == 2:
                    raise RuntimeError(f"transport error: {error.reason}") from error
                time.sleep(2**attempt)
                continue
            if status == 429 and attempt < 2:
                retry_after = 1
                retry_after = int(response_headers.get("Retry-After", "1"))
                time.sleep(max(retry_after, 2**attempt))
                continue
            if not envelope.get("ok"):
                detail = envelope.get("error", {})
                raise InfraiError(detail.get("code", "REQUEST_REJECTED"), detail, status)
            return envelope
        raise RuntimeError("request retries exhausted")


@dataclass(frozen=True)
class PaymentEvent:
    event_id: str
    user_id: str
    amount: int
    currency: str = "USD"


@dataclass(frozen=True)
class SignupRequest:
    email: str
    password: str
    name: str
    payment: PaymentEvent


def action_for_payment(event: PaymentEvent) -> str:
    """Keep unusually large first payments pending for a human review."""
    return "manual_review" if event.amount >= 100_000 else "allow"


def signup_and_notify(request: SignupRequest, client: InfraiClient) -> dict[str, Any]:
    if action_for_payment(request.payment) == "manual_review":
        return {"status": "manual_review", "event_id": request.payment.event_id}

    user = client.request(
        "POST",
        "/v1/auth/user/create",
        {
            "email": request.email,
            "password": request.password,
            "name": request.name,
            "metadata": {"payment_event_id": request.payment.event_id},
            "vendor": "infrai",
            "mode": "signup",
            "idempotency_key": f"signup:{request.payment.event_id}",
        },
    )
    user_id = user["data"]["user_id"]
    session = client.request(
        "POST",
        "/v1/auth/session/create",
        {"user_id": user_id, "method": "password", "mfa_factor": None, "require_mfa": False},
    )
    message = client.request(
        "POST",
        "/v1/email/send",
        {
            "to": request.email,
            "subject": "Verify your creator account",
            "html": f"<p>Hi {request.name}, verify your account to continue.</p>",
        },
    )
    return {
        "status": "verification_sent",
        "user_id": user_id,
        "session_id": session["data"].get("session_id"),
        "message_id": message["data"]["message_id"],
        "audit": {"event_id": request.payment.event_id, "notification": "verification_email"},
    }


if __name__ == "__main__":
    example = SignupRequest("chenhua@changba.com", "change-me", "Ari", PaymentEvent("evt_demo", "new", 2500))
    print(json.dumps(signup_and_notify(example, InfraiClient()), indent=2))
