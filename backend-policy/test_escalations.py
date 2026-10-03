import time

from conftest import escalate


def events(c):
    return [e["event"] for e in c.get("/audit_log").json()]


def test_create_matches_contract_shape(c):
    e = escalate(c)
    assert e["escalation_id"].startswith("esc_") and e["status"] == "PENDING"
    assert e["ttl_seconds"] == 2 and e["remaining_seconds"] in (1, 2)
    assert (e["amount"], e["currency"], e["merchant"], e["sku"]) == (799.0, "HKD", "PARKnSHOP", "SKU003")
    assert e["reason"] == "Over HK$500 per-transaction cap" and e["expires_at"].endswith("Z")
    assert c.get(f"/escalations/{e['escalation_id']}").json()["status"] == "PENDING"


def test_approve(c):
    e = escalate(c)
    r = c.post(f"/escalations/{e['escalation_id']}/decision", json={"decision": "APPROVE"}).json()
    assert r["status"] == "APPROVED" and r["decision_applied"] is True and r["remaining_seconds"] == 0
    assert "ESCALATION_APPROVED" in events(c)


def test_refuse_then_cannot_approve(c):
    e = escalate(c)
    url = f"/escalations/{e['escalation_id']}/decision"
    assert c.post(url, json={"decision": "REFUSE"}).json()["status"] == "REFUSED"
    again = c.post(url, json={"decision": "APPROVE"}).json()
    assert again["status"] == "REFUSED" and again["decision_applied"] is False


def test_expiry_and_late_approval_ignored(c):
    e = escalate(c)
    time.sleep(2.3)
    r = c.post(f"/escalations/{e['escalation_id']}/decision", json={"decision": "APPROVE"}).json()
    assert r["status"] == "EXPIRED" and r["decision_applied"] is False and r["late_decision_ignored"] is True
    assert r["remaining_seconds"] == 0 and "decision_attempt_at" in r
    ev = events(c)
    assert ev.count("ESCALATION_EXPIRED") == 1 and "LATE_DECISION_IGNORED" in ev
    assert "ESCALATION_APPROVED" not in ev


def test_sweeper_logs_unattended_expiry(c):
    escalate(c)
    time.sleep(3.3)                       # background sweeper runs every second
    assert events(c).count("ESCALATION_EXPIRED") == 1


def test_duplicate_create_returns_same_pending_then_new_after_decision(c):
    a, b = escalate(c), escalate(c)
    assert a["escalation_id"] == b["escalation_id"]
    c.post(f"/escalations/{a['escalation_id']}/decision", json={"decision": "REFUSE"})
    assert escalate(c)["escalation_id"] != a["escalation_id"]


def test_create_guards(c):
    r = c.post("/create_escalation", json={"amount": 300, "merchant": "Watsons", "sku": "S", "reason": "x"})
    assert r.status_code == 422
    r = c.post("/create_escalation", json={"amount": 900, "merchant": "Watsons", "sku": "S", "reason": "x"})
    assert r.status_code == 422
    r = c.post("/create_escalation", json={"amount": 700, "merchant": "DarkWebMart", "sku": "S", "reason": "x"})
    assert r.status_code == 422


def test_unknown_escalation_404(c):
    assert c.get("/escalations/nope").status_code == 404
    assert c.post("/escalations/nope/decision", json={"decision": "APPROVE"}).status_code == 404


def test_bad_decision_value_422(c):
    e = escalate(c)
    assert c.post(f"/escalations/{e['escalation_id']}/decision", json={"decision": "MAYBE"}).status_code == 422


def test_signature_checked_when_supplied(c):
    e = escalate(c)
    url = f"/escalations/{e['escalation_id']}/decision"
    assert c.post(url, json={"decision": "APPROVE", "signature": "forged"}).status_code == 403
    assert c.get(f"/escalations/{e['escalation_id']}").json()["status"] == "PENDING"
    assert c.post(url, json={"decision": "APPROVE", "signature": e["signature"]}).json()["status"] == "APPROVED"
