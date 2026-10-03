"""Settle a sanitized shopping list, one mocked charge per merchant.

The list is the person 1 cart line passed down after dev1 (the policy
engine) has already accepted it: each row is an item, a price, and a
merchant. This step does not re-check policy.

For each merchant it picks the rail with the lowest cash paid, then the
highest reward value, charges that merchant with the chosen method, and
waits for the mock gateway to confirm. Logistics are returned only after
that confirmation.
"""

from __future__ import annotations

import asyncio
import uuid
from collections import OrderedDict
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from dev.payment.money import as_float, money
from dev.payment.rails import LABELS, choose_rail, explain

DEFAULT_DELAY_S = 0.5

CARRIERS = {
    "hktvmall": "HKTVmall Delivery",
    "parknshop": "PARKnSHOP Home Delivery",
    "taste": "Taste Home Delivery",
    "watsons": "Watsons Express",
    "japan home centre": "JHC Courier",
}

_settlements: dict[str, dict] = {}


@dataclass(frozen=True)
class ShoppingLine:
    merchant: str
    amount: Decimal
    qty: int
    sku: str | None = None
    name: str | None = None


def line_from_contract(raw: dict) -> ShoppingLine:
    """Accept a person 1 CartLine, or a short {merchant, price} row."""
    merchant = str(raw.get("merchant") or "").strip()
    if not merchant:
        raise ValueError("each item needs a merchant")
    qty = int(raw.get("qty") or 1)
    if qty <= 0:
        raise ValueError("qty must be positive")
    if raw.get("line_total") is not None:
        amount = money(raw["line_total"])
    else:
        unit = raw.get("unit_price", raw.get("price"))
        if unit is None:
            raise ValueError("each item needs line_total, unit_price, or price")
        amount = money(Decimal(str(unit)) * qty)
    if amount < 0:
        raise ValueError("item amount cannot be negative")
    sku = raw.get("sku")
    name = raw.get("name")
    return ShoppingLine(
        merchant=merchant,
        amount=amount,
        qty=qty,
        sku=None if sku is None else str(sku),
        name=None if name is None else str(name),
    )


def _carrier(merchant: str) -> str:
    return CARRIERS.get(merchant.casefold(), f"{merchant} Courier")


def _group(lines: list[ShoppingLine]) -> OrderedDict[str, list[ShoppingLine]]:
    groups: OrderedDict[str, list[ShoppingLine]] = OrderedDict()
    index: dict[str, str] = {}
    for line in lines:
        key = line.merchant.casefold()
        display = index.setdefault(key, line.merchant)
        groups.setdefault(display, []).append(line)
    return groups


async def _charge(
    *,
    merchant: str,
    method: str,
    cash_paid: Decimal,
    delay_s: float,
) -> dict:
    """Mock the merchant gateway. Returns only after the call finishes."""
    await asyncio.sleep(delay_s)
    now = datetime.now(timezone.utc)
    eta = (now + timedelta(days=2)).date().isoformat()
    return {
        "success": True,
        "order_id": "ORD-" + uuid.uuid4().hex[:8],
        "ts": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "logistics": {
            "carrier": _carrier(merchant),
            "tracking_id": "TRK-" + uuid.uuid4().hex[:10].upper(),
            "status": "confirmed",
            "eta": eta,
            "method": method,
            "cash_paid": as_float(cash_paid),
        },
    }


async def settle_payment(
    items: list[dict],
    *,
    idempotency_key: str | None = None,
    delay_s: float = DEFAULT_DELAY_S,
) -> dict:
    if idempotency_key and idempotency_key in _settlements:
        return deepcopy(_settlements[idempotency_key])

    lines = [line_from_contract(item) for item in items]
    if not lines:
        raise ValueError("shopping list is empty")

    settlements = []
    cash_total = money(0)
    reward_total = money(0)

    for merchant, group in _group(lines).items():
        subtotal = money(sum((line.amount for line in group), Decimal("0")))
        best, quotes = choose_rail(subtotal)
        receipt = await _charge(
            merchant=merchant,
            method=best.method,
            cash_paid=best.cash_paid,
            delay_s=delay_s,
        )
        if not receipt["success"]:
            body = {
                "success": False,
                "currency": "HKD",
                "error": receipt.get("error") or "merchant_declined",
                "cash_paid": as_float(cash_total),
                "reward_hkd": as_float(reward_total),
                "settlements": settlements,
            }
            return body

        cash_total = money(cash_total + best.cash_paid)
        reward_total = money(reward_total + best.reward_hkd)
        settlements.append(
            {
                "merchant": merchant,
                "items": [
                    {
                        "sku": line.sku,
                        "name": line.name,
                        "qty": line.qty,
                        "amount": as_float(line.amount),
                    }
                    for line in group
                ],
                "subtotal": as_float(subtotal),
                "method": best.method,
                "method_label": LABELS[best.method],
                "cash_paid": as_float(best.cash_paid),
                "reward_hkd": as_float(best.reward_hkd),
                "reason": explain(best, quotes),
                "considered": [quote.as_dict() for quote in quotes],
                "order_id": receipt["order_id"],
                "ts": receipt["ts"],
                "logistics": receipt["logistics"],
            }
        )

    body = {
        "success": True,
        "currency": "HKD",
        "selection_rule": "minimum cash paid, then maximum reward HKD value",
        "cash_paid": as_float(cash_total),
        "reward_hkd": as_float(reward_total),
        "settlements": settlements,
        "error": None,
    }
    if idempotency_key:
        _settlements[idempotency_key] = deepcopy(body)
    return body


def clear_settlements() -> None:
    _settlements.clear()
