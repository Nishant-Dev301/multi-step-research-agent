"""
Real x402 payment provider — advanced enhancement (see ENHANCEMENTS.md).

Implements the same `PaymentProvider` interface as `MockPaymentProvider`
(app/x402/payment.py), so it's a drop-in swap in ResearchOrchestrator:

    from app.future.real_payment_provider import RealX402PaymentProvider
    orchestrator.payment_provider = RealX402PaymentProvider(policy, wallet=my_wallet)

Status: NOT runnable yet — this is a scaffold. `_settle_on_chain` raises
NotImplementedError until wired to a real x402 facilitator SDK and a funded
wallet. Everything else (policy checks, ledger, summary) is identical to
the mock provider so behavior stays consistent when you swap it in.

Wiring checklist to make this real:
  1. `pip install` your chosen x402 facilitator SDK (e.g. an x402-compatible
     client library) and a wallet signing library.
  2. Replace `_settle_on_chain` with:
       a. issue the request to the resource, receive HTTP 402 + requirements
       b. build + sign the payment payload with the wallet
       c. retry the request with the X-PAYMENT header
       d. parse X-PAYMENT-RESPONSE for the settlement confirmation
  3. Set real merchant endpoints in app/agents/tools.py's TOOL_MERCHANT_MAP.
  4. Remove the `raise NotImplementedError` guard below.
"""

from __future__ import annotations

import time
import uuid
from typing import Optional

from app.x402.payment import (
    PaymentProvider,
    PaymentRecord,
    SpendPolicy,
    SpendPolicyError,
)


class RealX402PaymentProvider(PaymentProvider):
    """Same policy-guard behavior as MockPaymentProvider; the only
    difference is `_settle_on_chain` talks to a real facilitator instead
    of just recording a ledger entry."""

    def __init__(self, policy: SpendPolicy, wallet: Optional[object] = None):
        self.policy = policy
        self.wallet = wallet  # your signing wallet / key manager
        self.ledger: list[PaymentRecord] = []
        self._session_total = 0.0

    def _settle_on_chain(self, merchant: str, amount: float, task: str) -> str:
        """Placeholder for the real challenge -> sign -> settle handshake.
        Must return a settlement/transaction reference string on success,
        or raise an exception on failure."""
        raise NotImplementedError(
            "Wire this to a real x402 facilitator SDK + funded wallet before use. "
            "See module docstring for the wiring checklist."
        )

    def pay(self, merchant: str, amount: float, task: str) -> PaymentRecord:
        record_id = str(uuid.uuid4())[:8]

        if self.policy.allowed_merchants and merchant not in self.policy.allowed_merchants:
            rec = PaymentRecord(record_id, merchant, amount, task, time.time(),
                                 "rejected", f"merchant '{merchant}' not in allowlist")
            self.ledger.append(rec)
            raise SpendPolicyError(rec.reason)

        if amount > self.policy.max_per_call:
            rec = PaymentRecord(record_id, merchant, amount, task, time.time(),
                                 "rejected", f"${amount:.4f} exceeds per-call cap")
            self.ledger.append(rec)
            raise SpendPolicyError(rec.reason)

        if self._session_total + amount > self.policy.max_per_session:
            rec = PaymentRecord(record_id, merchant, amount, task, time.time(),
                                 "rejected", "session budget exhausted")
            self.ledger.append(rec)
            raise SpendPolicyError(rec.reason)

        settlement_ref = self._settle_on_chain(merchant, amount, task)  # raises until wired
        self._session_total += amount
        rec = PaymentRecord(record_id, merchant, amount, task, time.time(), "settled",
                             reason=f"tx:{settlement_ref}")
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
