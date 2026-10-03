"""Shelf picks against fake_mall JSON. Person 2 is skipped and still logged."""

from __future__ import annotations

import hashlib

from fastapi.testclient import TestClient

from agent_graph import ShoppingAgent, parse_goal
from clients import PolicyClient
from fake_mall import FileMall
from openrouter import OpenRouterPlanner, PlannerError, parse_decision
from pick import resolve_pick
from policy_rules import decide
from server import create_app

GENESIS = "0" * 64


def scripted(intent: str, catalog: list[dict]) -> dict:
    text = intent.casefold()
    qty = 1
    if "2 " in text or text.startswith("2"):
        qty = 2
    if "toilet" in text:
        sell = "best_rating" if "best" in text else "highest_usage" if "everyday" in text else "cheap"
        sku = {"cheap": "SKU001", "highest_usage": "SKU002", "best_rating": "SKU003"}[sell]
        return {
            "query": "toilet paper",
            "qty": qty,
            "sell_point": sell,
            "sku": sku,
            "thought": f"Toilet paper, {sell}.",
            "model": "scripted",
        }
    if "earbud" in text:
        return {
            "query": "earbuds",
            "qty": 1,
            "sell_point": "best_rating",
            "sku": "SKU025",
            "thought": "They asked for the best rated earbuds.",
            "model": "scripted",
        }
    if "rice" in text:
        return {
            "query": "rice",
            "qty": 1,
            "sell_point": "highest usage",
            "sku": "SKU005",
            "thought": "Everyday rice is the highest-usage bag.",
            "model": "scripted",
        }
    return {
        "query": "spaceship",
        "qty": 1,
        "sell_point": "cheap",
        "sku": "",
        "thought": "Nothing on the shelf matches.",
        "model": "scripted",
    }


def client() -> tuple[TestClient, PolicyClient]:
    policy = PolicyClient(offline=True)
    app = create_app(ShoppingAgent(FileMall(), policy, scripted))
    return TestClient(app), policy


def assert_chain(entries: list[dict]) -> None:
    previous = GENESIS
    for entry in entries:
        material = "|".join(
            [
                str(entry["index"]),
                entry["ts"],
                entry["event"],
                entry["status"],
                entry["reason"],
                entry["prev_hash"],
            ]
        )
        digest = hashlib.sha256(material.encode("utf-8")).hexdigest()
        assert entry["prev_hash"] == previous
        assert entry["hash"] == digest
        previous = entry["hash"]


def events(body: dict) -> list[str]:
    return [entry["event"] for entry in body["audit_log"]]


def test_policy_rules() -> None:
    assert decide("Watsons", "Household", 119.9, 0)["status"] == "PASS"
    assert decide("Watsons", "Household", 119.9, 0)["monthly_remaining"] == 1880.1
    halted = decide("Watsons", "Household", 119.9, 1900)
    assert halted["status"] == "HALT"
    assert halted["reason"] == "Over HK$2000 monthly cap"
    assert decide("DarkWebMart", "Household", 10, 0)["reason"] == "Merchant blacklisted"


def test_goal_parser() -> None:
    assert parse_goal("Buy toilet paper") == {
        "intent": "Buy toilet paper",
        "query": "toilet",
        "qty": 1,
    }


def test_catalog_shape() -> None:
    products = FileMall().products
    categories = {item["category"] for item in products}
    assert len(products) == 30
    assert len(categories) == 10
    for category in categories:
        points = [item["sell_point"] for item in products if item["category"] == category]
        assert sorted(points) == ["best_rating", "cheap", "highest_usage"]


def test_sell_point_overrides_a_wrong_sku() -> None:
    catalog = FileMall().products
    cheap = resolve_pick(
        catalog,
        {"query": "toilet paper", "sell_point": "cheap", "sku": "SKU003"},
    )
    assert cheap["id"] == "SKU001"
    rated = resolve_pick(
        catalog,
        {"query": "earbuds", "sell_point": "best_rating", "sku": "SKU025"},
    )
    assert rated["id"] == "SKU027"
    assert resolve_pick(catalog, {"query": "spaceship", "sell_point": "cheap", "sku": ""}) is None


def test_cheap_toilet_paper_pays_and_skips_policy() -> None:
    api, _policy = client()
    response = api.post("/agent/intent", json={"intent": "cheap toilet paper", "monthly_spent": 1900})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "COMPLETED"
    assert body["goal"]["sell_point"] == "cheap"
    assert body["goal"]["model"] == "scripted"
    assert body["product"]["id"] == "SKU001"
    assert body["product"]["sell_point"] == "cheap"
    assert body["quote"]["shipping_fee"] == 30
    assert body["quote"]["total_landed_cost"] == 59.9
    assert body["policy"]["status"] == "SKIPPED"
    assert body["policy"]["reason"] == "Person 2 check skipped"
    assert body["policy"]["monthly_remaining"] == 100
    assert body["escalation"] is None
    assert body["payment"]["success"] is True
    assert body["payment"]["charged"] == 59.9
    assert "reward_points_earned" not in body["payment"]
    assert events(body) == [
        "INTENT_RECEIVED",
        "PLAN",
        "SEARCH",
        "CART_PRICED",
        "POLICY_CHECK",
        "PAYMENT",
    ]
    assert body["audit_log"][4]["status"] == "SKIPPED"
    assert body["audit_log"][-1]["status"] == "COMPLETED"
    assert_chain(body["audit_log"])


def test_best_rated_earbuds_and_everyday_rice() -> None:
    api, _policy = client()
    earbuds = api.post("/agent/intent", json={"intent": "best rated earbuds"}).json()
    assert earbuds["product"]["id"] == "SKU027"
    assert earbuds["product"]["sell_point"] == "best_rating"
    assert earbuds["quote"]["shipping_fee"] == 0
    assert earbuds["quote"]["total_landed_cost"] == 698.0
    assert earbuds["policy"]["status"] == "SKIPPED"
    assert_chain(earbuds["audit_log"])
    rice = api.post("/agent/intent", json={"intent": "everyday rice"}).json()
    assert rice["product"]["id"] == "SKU005"
    assert rice["goal"]["sell_point"] == "highest_usage"
    assert rice["quote"]["total_landed_cost"] == 98.0


def test_unknown_request_is_logged_and_does_not_pay() -> None:
    api, _policy = client()
    body = api.post("/agent/intent", json={"intent": "a spaceship"}).json()
    assert body["status"] == "FAILED"
    assert body["payment"] is None
    assert events(body) == ["INTENT_RECEIVED"]
    assert body["audit_log"][-1]["reason"] == "No product matched"
    assert_chain(body["audit_log"])


def test_missing_openrouter_key_is_logged() -> None:
    policy = PolicyClient(offline=True)
    agent = ShoppingAgent(FileMall(), policy, OpenRouterPlanner(api_key=""))
    body = agent.run("cheap toilet paper", 0, None)
    assert body["status"] == "FAILED"
    assert body["audit_log"][-1]["reason"] == "OPENROUTER_API_KEY is not set"
    assert_chain(body["audit_log"])


def test_openrouter_json_parse() -> None:
    decision = parse_decision('```json\n{"query":"rice","qty":1,"sell_point":"cheap","sku":"SKU004","thought":"Cheap rice."}\n```')
    assert decision["sku"] == "SKU004"
    try:
        OpenRouterPlanner(api_key="").__call__("rice", [])
    except PlannerError as exc:
        assert "OPENROUTER_API_KEY" in str(exc)
    else:
        raise AssertionError("missing key should fail")
    try:
        OpenRouterPlanner(api_key="test", model="deepseek/deepseek-v4.1-flash:batch").__call__("rice", [])
    except PlannerError as exc:
        assert "batch-only" in str(exc)
        assert "deepseek/deepseek-v4.1-flash" in str(exc)
    else:
        raise AssertionError("batch model should fail before the request")


def test_home_page_has_chat_and_ticket() -> None:
    api, _policy = client()
    page = api.get("/")
    assert page.status_code == 200
    text = page.text
    assert 'id="intent"' in text
    assert 'id="ticket"' in text
    assert "/agent/intent" in text


if __name__ == "__main__":
    test_policy_rules()
    test_goal_parser()
    test_catalog_shape()
    test_sell_point_overrides_a_wrong_sku()
    test_cheap_toilet_paper_pays_and_skips_policy()
    test_best_rated_earbuds_and_everyday_rice()
    test_unknown_request_is_logged_and_does_not_pay()
    test_missing_openrouter_key_is_logged()
    test_openrouter_json_parse()
    test_home_page_has_chat_and_ticket()
    print("ok")
