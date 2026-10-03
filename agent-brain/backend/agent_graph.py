"""Live LangGraph for POST /agent/intent.

Same spine as graph/shopping_graph.py: reason, a fixed plan, tool calls,
then a policy branch. Each step is hashed into audit_log before the next
edge runs. Tool calls hit the mall and the policy service.
"""

from __future__ import annotations

import hashlib
import operator
import re
from datetime import datetime, timezone
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph

from clients import PolicyClient, public_escalation
from models import ActionPlan
from openrouter import OpenRouterPlanner
from pick import goal_from, resolve_pick
from policy_rules import money

GENESIS = "0" * 64

THOUGHTS = {
    "INTENT_RECEIVED": "Read the sentence. Set query and qty.",
    "PLAN": "The tool order is fixed: search, price, check policy, then pay.",
    "SEARCH": "Search the sandbox and keep the first product.",
    "CART_PRICED": "Price the cart. Shipping can change the amount.",
    "POLICY_CHECK": "Ask the policy engine. This node does not decide.",
    "PAYMENT": "Charge the landed total.",
    "ESCALATION_CREATED": "Open the 10-minute approval and return now.",
    "HALTED": "Policy said HALT. Do not pay.",
    "ESCALATION_REFUSED": "Mother refused. Do not pay.",
    "ESCALATION_EXPIRED": "The 10 minutes ran out. Do not pay.",
}


class AgentState(TypedDict, total=False):
    intent: str
    monthly_spent: float
    escalation_id: str
    escalation_status: str
    policy_status: str
    goal: dict
    product: dict
    quote: dict
    policy: dict
    escalation: dict
    payment: dict
    plan_status: str
    stop: bool
    pending_event: dict
    path: Annotated[list, operator.add]
    audit_log: Annotated[list, operator.add]


def parse_goal(intent: str) -> dict:
    text = intent.casefold()
    qty = 1
    match = re.search(r"\b(\d+)\b", text)
    if match:
        qty = max(1, int(match.group(1)))
    if "bulk" in text:
        query = "bulk"
    elif "toilet" in text:
        query = "toilet"
    else:
        skip = {"buy", "please", "a", "the", "some"}
        query = " ".join(word for word in text.split() if word not in skip) or intent
    return {"intent": intent, "query": query, "qty": qty}


def _pending(event: str, status: str, reason: str, thought: str | None = None) -> dict:
    return {
        "event": event,
        "status": status,
        "reason": reason,
        "thought": thought or THOUGHTS[event],
    }


def _stamp(log: list[dict], pending: dict) -> dict:
    index = len(log)
    prev = log[-1]["hash"] if log else GENESIS
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    material = "|".join([str(index), ts, pending["event"], pending["status"], pending["reason"], prev])
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()
    return {
        "index": index,
        "ts": ts,
        "event": pending["event"],
        "status": pending["status"],
        "reason": pending["reason"],
        "thought": pending["thought"],
        "prev_hash": prev,
        "hash": digest,
    }


def _product(raw: dict) -> dict:
    return {
        "id": raw["id"],
        "name": raw["name"],
        "price": round(float(raw["price"]), 2),
        "currency": raw.get("currency", "HKD"),
        "merchant": raw["merchant"],
        "category": raw["category"],
        "stock": int(raw.get("stock", 0)),
        "image_url": raw.get("image_url") or "",
        "sell_point": raw.get("sell_point") or "",
    }


def _quote(raw: dict) -> dict:
    lines = []
    for item in raw["line_items"]:
        lines.append(
            {
                "sku": item["sku"],
                "name": item["name"],
                "merchant": item["merchant"],
                "category": item["category"],
                "unit_price": round(float(item["unit_price"]), 2),
                "qty": int(item["qty"]),
                "line_total": round(float(item["line_total"]), 2),
            }
        )
    return {
        "line_items": lines,
        "subtotal": round(float(raw["subtotal"]), 2),
        "shipping_fee": round(float(raw["shipping_fee"]), 2),
        "tax": round(float(raw.get("tax", 0)), 2),
        "total_landed_cost": round(float(raw["total_landed_cost"]), 2),
        "currency": raw.get("currency", "HKD"),
        "free_shipping_threshold": round(float(raw.get("free_shipping_threshold", 400)), 2),
    }


def _failure(name: str, event: str, reason: str) -> dict:
    return {
        "path": [name],
        "plan_status": "FAILED",
        "stop": True,
        "pending_event": _pending(event, "FAILED", reason),
    }


class ShoppingAgent:
    def __init__(self, mall, policy: PolicyClient, planner=None):
        self.mall = mall
        self.policy = policy
        self.planner = planner or OpenRouterPlanner()
        self.graph = self._build()

    def _catalog(self) -> list[dict]:
        products = getattr(self.mall, "products", None)
        if isinstance(products, list) and products:
            return products
        return self.mall.search("")

    def run(self, intent: str, monthly_spent: float, escalation_id: str | None) -> dict:
        result = self.graph.invoke(
            {
                "intent": intent,
                "monthly_spent": monthly_spent,
                "escalation_id": escalation_id or "",
                "path": [],
                "audit_log": [],
            }
        )
        plan = {
            "intent": result.get("intent", intent),
            "status": result.get("plan_status", "FAILED"),
            "goal": result.get("goal"),
            "product": result.get("product"),
            "quote": result.get("quote"),
            "policy": result.get("policy"),
            "escalation": public_escalation(result["escalation"]) if result.get("escalation") else None,
            "payment": result.get("payment"),
            "audit_log": result.get("audit_log", []),
        }
        return ActionPlan.model_validate(plan).model_dump()

    def _audit(self, name: str):
        def audit(state: AgentState) -> dict:
            pending = state["pending_event"]
            entry = _stamp(state.get("audit_log", []), pending)
            self.policy.log_event(entry["event"], entry["status"], entry["reason"])
            return {"path": [name], "audit_log": [entry]}

        audit.__name__ = name
        return audit

    def _route_entry(self, state: AgentState) -> dict:
        escalation_id = state.get("escalation_id") or ""
        if not escalation_id:
            return {"path": ["route_entry"]}
        record = self.policy.get_escalation(escalation_id)
        if record is None:
            return {
                "path": ["route_entry"],
                "escalation_status": "UNKNOWN",
            }
        update: dict = {
            "path": ["route_entry"],
            "escalation_status": record.get("status"),
            "escalation": record,
        }
        if record.get("product"):
            update["product"] = record["product"]
        if record.get("quote"):
            update["quote"] = record["quote"]
        if record.get("goal"):
            update["goal"] = record["goal"]
        if record.get("policy"):
            update["policy"] = record["policy"]
        return update

    def _choose_entry(self, state: AgentState) -> str:
        status = state.get("escalation_status")
        if status == "APPROVED":
            return "execute_payment"
        if status in {"REFUSED", "EXPIRED", "UNKNOWN"}:
            return "abort"
        if status == "PENDING":
            return "hold"
        return "reason"

    def _reason(self, state: AgentState) -> dict:
        try:
            decision = self.planner(state["intent"], self._catalog())
            chosen = resolve_pick(self._catalog(), decision)
        except Exception as exc:
            return {
                "path": ["reason"],
                "plan_status": "FAILED",
                "stop": True,
                "pending_event": _pending(
                    "INTENT_RECEIVED",
                    "FAILED",
                    str(exc),
                    "The model step did not return a pick.",
                ),
            }
        if chosen is None:
            return {
                "path": ["reason"],
                "goal": goal_from(state["intent"], decision),
                "plan_status": "FAILED",
                "stop": True,
                "pending_event": _pending(
                    "INTENT_RECEIVED",
                    "FAILED",
                    "No product matched",
                    str(decision.get("thought") or "Nothing on the shelf fit the sentence."),
                ),
            }
        goal = goal_from(state["intent"], decision, chosen)
        return {
            "path": ["reason"],
            "goal": goal,
            "product": _product(chosen),
            "pending_event": _pending(
                "INTENT_RECEIVED",
                "PARSED",
                "Model may decide query, qty, and sell point",
                goal["thought"],
            ),
        }

    def _after_intent(self, state: AgentState) -> str:
        return "end" if state.get("stop") else "plan"

    def _plan(self, state: AgentState) -> dict:
        return {
            "path": ["plan"],
            "pending_event": _pending(
                "PLAN",
                "FIXED_ORDER",
                "search_products, price_cart, check_budget, then pay",
            ),
        }

    def _search(self, state: AgentState) -> dict:
        chosen = state.get("product") or {}
        sku = chosen.get("id") or (state.get("goal") or {}).get("sku")
        try:
            fresh = self.mall.product(sku)
        except Exception:
            return _failure("search_products", "SEARCH", "Mall search failed")
        sell = (state.get("goal") or {}).get("sell_point") or fresh.get("sell_point") or ""
        thought = (state.get("goal") or {}).get("thought") or "Catalog data only. The sell point picks the shelf."
        return {
            "path": ["search_products"],
            "product": _product(fresh),
            "pending_event": _pending(
                "SEARCH",
                "RECORDED",
                f"Picked {fresh['id']} for sell point {sell}.",
                thought,
            ),
        }

    def _after_search(self, state: AgentState) -> str:
        return "end" if state.get("stop") else "price_cart"

    def _cart(self, state: AgentState) -> dict:
        product = state["product"]
        qty = int(state["goal"]["qty"])
        try:
            quoted = self.mall.cart(product["id"], qty)
        except Exception:
            return _failure("price_cart", "CART_PRICED", "Mall cart failed")
        return {
            "path": ["price_cart"],
            "quote": _quote(quoted),
            "pending_event": _pending(
                "CART_PRICED",
                "RECORDED",
                "Later nodes use total_landed_cost, not the shelf price.",
            ),
        }

    def _after_cart(self, state: AgentState) -> str:
        return "end" if state.get("stop") else "check_budget"

    def _budget(self, state: AgentState) -> dict:
        product = state["product"]
        amount = state["quote"]["total_landed_cost"]
        spent = money(state.get("monthly_spent", 0))
        result = self.policy.check(product["merchant"], product["category"], amount, spent)
        status = result["status"]
        return {
            "path": ["check_budget"],
            "policy": result,
            "policy_status": status,
            "pending_event": _pending("POLICY_CHECK", status, result["reason"]),
        }

    def _after_policy(self, state: AgentState) -> str:
        if state.get("stop"):
            return "end"
        # Anything that is not an explicit PASS or ESCALATE halts. Unknown statuses never pay.
        return {
            "PASS": "execute_payment",
            "ESCALATE": "create_escalation",
        }.get(state["policy_status"], "halt")

    def _pay(self, state: AgentState) -> dict:
        approved = state.get("escalation_status") == "APPROVED"
        passed = state.get("policy_status") == "PASS" or (
            isinstance(state.get("policy"), dict) and state["policy"].get("status") == "PASS"
        )
        if not approved and not passed:
            return {
                "path": ["execute_payment"],
                "plan_status": "FAILED",
                "stop": True,
                "pending_event": _pending(
                    "PAYMENT",
                    "FAILED",
                    "Pay allowed only after PASS or APPROVED",
                ),
            }
        quote = state.get("quote") or {}
        product = state.get("product") or {}
        goal = state.get("goal") or {}
        total = quote.get("total_landed_cost")
        if total is None and state.get("escalation"):
            total = state["escalation"].get("amount")
        sku = product.get("id") or (state.get("escalation") or {}).get("sku")
        qty = goal.get("qty") or 1
        tag = "PASS" if passed and not approved else "ESCALATE"
        escalation_id = state.get("escalation_id") or "none"
        if tag == "PASS":
            escalation_id = "none"
        try:
            payment = self.mall.pay(float(total), f"{sku}:{qty}:{tag}:{escalation_id}")
        except Exception:
            return _failure("execute_payment", "PAYMENT", "Mall payment failed")
        plan_status = "COMPLETED" if payment["success"] else "FAILED"
        reason = "Payment success" if payment["success"] else (payment.get("error") or "Payment failed")
        log_status = "COMPLETED" if payment["success"] else "FAILED"
        return {
            "path": ["execute_payment"],
            "payment": payment,
            "plan_status": plan_status,
            "pending_event": _pending("PAYMENT", log_status, reason),
        }

    def _escalate(self, state: AgentState) -> dict:
        product = state["product"]
        policy = state["policy"]
        record = self.policy.create_escalation(
            {
                "amount": state["quote"]["total_landed_cost"],
                "currency": "HKD",
                "merchant": product["merchant"],
                "sku": product["id"],
                "qty": state["goal"]["qty"],
                "reason": policy["reason"],
                "product": product,
                "quote": state["quote"],
                "goal": state["goal"],
                "policy": policy,
                "intent": state["intent"],
                "monthly_spent": state.get("monthly_spent", 0),
            }
        )
        stored = self.policy.memory[record["escalation_id"]]
        return {
            "path": ["create_escalation"],
            "plan_status": "ESCALATED",
            "escalation": stored,
            "escalation_id": record["escalation_id"],
            "pending_event": _pending("ESCALATION_CREATED", "PENDING", policy["reason"]),
        }

    def _halt(self, state: AgentState) -> dict:
        reason = state["policy"]["reason"]
        return {
            "path": ["halt"],
            "plan_status": "HALTED",
            "payment": None,
            "pending_event": _pending("HALTED", "HALTED", reason),
        }

    def _abort(self, state: AgentState) -> dict:
        status = state.get("escalation_status")
        if status == "EXPIRED":
            event = "ESCALATION_EXPIRED"
            reason = "TTL reached 0"
        elif status == "REFUSED":
            event = "ESCALATION_REFUSED"
            reason = "Mother refused"
        else:
            event = "HALTED"
            reason = "Unknown escalation"
        return {
            "path": ["abort"],
            "plan_status": "ABORTED",
            "pending_event": _pending(event, "ABORTED", reason),
        }

    def _hold(self, state: AgentState) -> dict:
        reason = (state.get("escalation") or {}).get("reason") or "Waiting for approval"
        return {
            "path": ["hold"],
            "plan_status": "ESCALATED",
            "pending_event": _pending("ESCALATION_CREATED", "PENDING", reason),
        }

    def _build(self):
        graph = StateGraph(AgentState)
        graph.add_node("route_entry", self._route_entry)
        graph.add_node("reason", self._reason)
        graph.add_node("plan", self._plan)
        graph.add_node("search_products", self._search)
        graph.add_node("price_cart", self._cart)
        graph.add_node("check_budget", self._budget)
        graph.add_node("execute_payment", self._pay)
        graph.add_node("create_escalation", self._escalate)
        graph.add_node("halt", self._halt)
        graph.add_node("abort", self._abort)
        graph.add_node("hold", self._hold)
        for name in (
            "audit_intent",
            "audit_plan",
            "audit_search",
            "audit_cart",
            "audit_policy",
            "audit_payment",
            "audit_escalation",
            "audit_halt",
            "audit_abort",
            "audit_hold",
        ):
            graph.add_node(name, self._audit(name))

        graph.add_edge(START, "route_entry")
        graph.add_conditional_edges(
            "route_entry",
            self._choose_entry,
            {
                "reason": "reason",
                "execute_payment": "execute_payment",
                "abort": "abort",
                "hold": "hold",
            },
        )
        graph.add_edge("reason", "audit_intent")
        graph.add_conditional_edges(
            "audit_intent",
            self._after_intent,
            {"plan": "plan", "end": END},
        )
        graph.add_edge("plan", "audit_plan")
        graph.add_edge("audit_plan", "search_products")
        graph.add_edge("search_products", "audit_search")
        graph.add_conditional_edges(
            "audit_search",
            self._after_search,
            {"price_cart": "price_cart", "end": END},
        )
        graph.add_edge("price_cart", "audit_cart")
        graph.add_conditional_edges(
            "audit_cart",
            self._after_cart,
            {"check_budget": "check_budget", "end": END},
        )
        graph.add_edge("check_budget", "audit_policy")
        graph.add_conditional_edges(
            "audit_policy",
            self._after_policy,
            {
                "execute_payment": "execute_payment",
                "create_escalation": "create_escalation",
                "halt": "halt",
                "end": END,
            },
        )
        graph.add_edge("execute_payment", "audit_payment")
        graph.add_edge("audit_payment", END)
        graph.add_edge("create_escalation", "audit_escalation")
        graph.add_edge("audit_escalation", END)
        graph.add_edge("halt", "audit_halt")
        graph.add_edge("audit_halt", END)
        graph.add_edge("abort", "audit_abort")
        graph.add_edge("audit_abort", END)
        graph.add_edge("hold", "audit_hold")
        graph.add_edge("audit_hold", END)
        return graph.compile()
