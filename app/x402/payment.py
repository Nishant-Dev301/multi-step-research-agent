"""
Lightweight x402-style payment middleware.

x402 (https://www.x402.org/) is an emerging standard that lets a client pay
for an HTTP resource by responding to a 402 Payment Required challenge with
a signed payment proof, which the server verifies before releasing the
resource.

For hackathon purposes this module implements the *shape* of that flow —
policy checks, a settlement call, and an auditable ledger — behind a small
interface (`PaymentProvider`). Swap `MockPaymentProvider` for a real x402
client/facilitator SDK later without touching the orchestrator.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Optional


class SpendPolicyError(Exception):
    """Raised when a payment would violate the configured spend policy."""


@dataclass
class SpendPolicy:
    max_per_call: float = 0.05          # USD, max per single API call
    max_per_session: float = 1.00       # USD, max total per research query
    allowed_merchants: Optional[set[str]] = None  # None = allow all


@dataclass
class PaymentRecord:
    id: str
    merchant: str
    amount: float
    task: str
    timestamp: float
    status: str  # "settled" | "rejected"
    reason: Optional[str] = None


class PaymentProvider:
    """Interface every payment backend (mock or real x402) must implement."""

    def pay(self, merchant: str, amount: float, task: str) -> PaymentRecord:
        raise NotImplementedError


class MockPaymentProvider(PaymentProvider):
    """
    Simulates the x402 challenge/settle handshake without touching a real
    network or wallet. Enforces a SpendPolicy and keeps a full audit ledger —
    this is what a judge/mentor can point to as the "policy guard" piece.
    """

    def __init__(self, policy: SpendPolicy):
        self.policy = policy
        self.ledger: list[PaymentRecord] = []
        self._session_total = 0.0

    def _spent(self) -> float:
        return self._session_total

    def pay(self, merchant: str, amount: float, task: str) -> PaymentRecord:
        record_id = str(uuid.uuid4())[:8]

        # Policy checks (mirrors what a real x402 policy-guard layer would do)
        if self.policy.allowed_merchants and merchant not in self.policy.allowed_merchants:
            rec = PaymentRecord(record_id, merchant, amount, task, time.time(),
                                 "rejected", f"merchant '{merchant}' not in allowlist")
            self.ledger.append(rec)
            raise SpendPolicyError(rec.reason)

        if amount > self.policy.max_per_call:
            rec = PaymentRecord(record_id, merchant, amount, task, time.time(),
                                 "rejected", f"${amount:.4f} exceeds per-call cap ${self.policy.max_per_call:.4f}")
            self.ledger.append(rec)
            raise SpendPolicyError(rec.reason)

        if self._spent() + amount > self.policy.max_per_session:
            rec = PaymentRecord(record_id, merchant, amount, task, time.time(),
                                 "rejected", "session budget exhausted")
            self.ledger.append(rec)
            raise SpendPolicyError(rec.reason)

        # --- Simulated 402 challenge -> signed proof -> settle ---
        # A real integration would:
        #   1. Call the resource, receive HTTP 402 + payment requirements
        #   2. Sign a payment payload with the agent's wallet
        #   3. Retry the request with the X-PAYMENT header
        #   4. Read the settlement confirmation from X-PAYMENT-RESPONSE
        self._session_total += amount
        rec = PaymentRecord(record_id, merchant, amount, task, time.time(), "settled")
        self.ledger.append(rec)
        return rec

    def summary(self) -> dict:
        return {
            "total_spent": round(self._session_total, 4),
            "budget": self.policy.max_per_session,
            "calls": len(self.ledger),
            "settled": len([r for r in self.ledger if r.status == "settled"]),
            "rejected": len([r for r in self.ledger if r.status == "rejected"]),
            "ledger": [r.__dict__ for r in self.ledger],
        }
