from typing import Literal

from pydantic import BaseModel, Field

PlanStatus = Literal["READY", "COMPLETED", "HALTED", "ESCALATED", "ABORTED", "FAILED"]
PolicyStatus = Literal["PASS", "ESCALATE", "HALT", "SKIPPED"]
EscalationStatus = Literal["PENDING", "APPROVED", "REFUSED", "EXPIRED"]


class IntentIn(BaseModel):
    intent: str = Field(min_length=1)
    monthly_spent: float = 0
    escalation_id: str | None = None


class Goal(BaseModel):
    intent: str
    query: str
    qty: int
    sell_point: str = ""
    sku: str = ""
    thought: str = ""
    model: str = ""


class Product(BaseModel):
    id: str
    name: str
    price: float
    currency: str
    merchant: str
    category: str
    stock: int
    image_url: str = ""
    sell_point: str = ""


class CartLine(BaseModel):
    sku: str
    name: str
    merchant: str
    category: str
    unit_price: float
    qty: int
    line_total: float


class CartQuote(BaseModel):
    line_items: list[CartLine]
    subtotal: float
    shipping_fee: float
    tax: float
    total_landed_cost: float
    currency: str
    free_shipping_threshold: float


class PolicyResult(BaseModel):
    status: PolicyStatus
    reason: str
    amount: float
    currency: str
    monthly_spent: float
    monthly_remaining: float
    per_transaction_cap: int
    monthly_cap: int
    bulk_ceiling: int


class PayResult(BaseModel):
    success: bool
    order_id: str | None
    charged: float | None
    currency: str | None
    payment_route: str | None
    ts: str | None
    error: str | None


class Escalation(BaseModel):
    escalation_id: str
    status: EscalationStatus
    ttl_seconds: int
    expires_at: str
    remaining_seconds: int
    amount: float
    currency: str
    merchant: str
    sku: str
    reason: str


class AuditEntry(BaseModel):
    index: int
    ts: str
    event: str
    status: str
    reason: str
    thought: str
    prev_hash: str
    hash: str


class ActionPlan(BaseModel):
    intent: str
    status: PlanStatus
    goal: Goal | None = None
    product: Product | None = None
    quote: CartQuote | None = None
    policy: PolicyResult | None = None
    escalation: Escalation | None = None
    payment: PayResult | None = None
    audit_log: list[AuditEntry]
