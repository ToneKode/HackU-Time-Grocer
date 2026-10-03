pip install -r requirements.txt && cp .env.example .env && ./run.sh
pytest -q          # 21 tests, no Redis needed (fakeredis)

Swagger UI: http://localhost:8001/docs. Set REDIS_URL=redis://localhost:6379/0 for real Redis.

Contract for Person 1 (agent) and Person 3 (UI)
Endpoint	Purpose
POST /check_policy	Returns decision (AUTO_EXECUTE / ESCALATE / HALT / REJECT / NEEDS_CLARIFICATION / DUPLICATE_BLOCKED), execution_allowed, reason, tlc, rule_trace, violations, clarification... Only call execute_payment when execution_allowed is true. Logs a POLICY_CHECK itself.
POST /log_event	Append any event to the hash chain. After a successful payment log PAYMENT_EXECUTED with {user_id, order_id, amount, idempotency_key} — this is what updates the monthly budget and duplicate protection.
POST /create_escalation	Starts the 600s Redis TTL; returns id, signature, expires_at, remaining_seconds.
GET /escalation/{id}	Poll status: pending / approved / refused / expired.
POST /escalation/{id}/approve or /refuse	Body {signature} (UI gets it from the escalation payload). After TTL: escalation_expired + late_approval_ignored: true.
GET /ledger, GET /ledger/verify	Trust Ledger + tamper check (valid, broken_at).
GET/PUT /rules, GET /budget/{user_id}	FR1 rules, FR8 dashboard data.
POST /demo/tamper/{i}, POST /demo/reset	Demo only (DEMO_MODE=true).
Agent flow
/check_policy (phase pre) with items from the mock API + shipping_fee + rewards_discount.
ESCALATE -> /create_escalation -> poll -> on approved call /check_policy with phase=final, prior_check_id, escalation_id.
For AUTO_EXECUTE, run phase=final too (catches price drift and revoked mandates), then pay, then log PAYMENT_EXECUTED.
