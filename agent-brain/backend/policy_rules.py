"""The frozen policy numbers. Person 2 owns the live engine.

Person 1 calls POST /check_policy. These rules are the fallback when that
service is down, so the frontend still receives PASS, ESCALATE, or HALT.
"""

from __future__ import annotations

PER_TRANSACTION_CAP = 500
BULK_CEILING = 800
MONTHLY_CAP = 2000
TTL_SECONDS = 600

WHITELIST = ["Watsons", "HKTVmall", "PARKnSHOP", "Japan Home Centre"]
BLACKLIST = ["DarkWebMart"]
CATEGORY_BLACKLIST = ["Food", "Alcohol", "Electronics", "Health"]


def money(value: float) -> float:
    return round(float(value), 2)


def _in(value: str, options: list[str]) -> bool:
    return value.strip().casefold() in {option.casefold() for option in options}


def decide(
    merchant: str,
    category: str,
    amount: float,
    monthly_spent: float,
) -> dict:
    amount = money(amount)
    monthly_spent = money(monthly_spent)
    status = "PASS"
    reason = "Under HK$500 cap"
    if _in(merchant, BLACKLIST):
        status, reason = "HALT", "Merchant blacklisted"
    elif not _in(merchant, WHITELIST):
        status, reason = "HALT", "Merchant not whitelisted"
    elif _in(category, CATEGORY_BLACKLIST):
        status, reason = "HALT", "Category blacklisted"
    elif money(monthly_spent + amount) > MONTHLY_CAP:
        status, reason = "HALT", "Over HK$2000 monthly cap"
    elif amount > BULK_CEILING:
        status, reason = "HALT", "Over HK$800 bulk ceiling"
    elif amount > PER_TRANSACTION_CAP:
        status, reason = "ESCALATE", "Over HK$500 per-transaction cap"

    if status == "HALT":
        remaining = money(MONTHLY_CAP - monthly_spent)
    else:
        remaining = money(MONTHLY_CAP - monthly_spent - amount)
    return {
        "status": status,
        "reason": reason,
        "amount": amount,
        "currency": "HKD",
        "monthly_spent": monthly_spent,
        "monthly_remaining": remaining,
        "per_transaction_cap": PER_TRANSACTION_CAP,
        "monthly_cap": MONTHLY_CAP,
        "bulk_ceiling": BULK_CEILING,
    }
