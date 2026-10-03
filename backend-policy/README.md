# backend-policy — Person 2 (Trust, Policy & Audit) · port 8001

Deterministic policy engine, SHA-256 hash-chained audit log, and a Redis-TTL human escalation.
Contract: `agent-brain/cross_team_config.json` and `frontend/contract.json`.

## Run
```bash
cd backend-policy && pip install -r requirements.txt
uvicorn main:app --port 8001 --reload       # uses fakeredis by default; no Redis needed
pytest -q                                   # 24 tests
```
Real Redis: `REDIS_URL=redis://localhost:6379/0 uvicorn main:app --port 8001`.

## Endpoints
| Method | Path | Who calls it | Notes |
|---|---|---|---|
| POST | `/check_policy` | Person 1 (`check_budget`) | `{merchant, category, amount, currency, sku, qty, monthly_spent}` -> PolicyResult (+ extra `rule`) |
| POST | `/log_event` | Person 1 | `{event, status, reason, thought?}` -> LogEntry. `thought` is shown in the UI but not hashed |
| GET | `/audit_log` | Person 3 | AuditEntry[] ascending by index |
| GET | `/audit_log/verify` | Person 3 | `{valid, broken_at, reason}`; re-reads the file, so edits are detected |
| POST | `/create_escalation` | Person 1 | Starts the 600 s Redis timer. 422 unless the amount is in (500, 800] and the merchant is allowed |
| GET | `/escalations/{id}` | Person 1, Person 3 (poll 1 s) | PENDING / APPROVED / REFUSED / EXPIRED, `remaining_seconds` |
| POST | `/escalations/{id}/decision` | Person 3 | `{decision: APPROVE\|REFUSE}`. Always 200 with the Escalation; extra `decision_applied`, and `late_decision_ignored` after expiry |
| GET | `/rules` | Person 3 | Active caps and lists for the dashboard |
| POST | `/demo/tamper/{i}`, `/demo/reset` | demo only | need `DEMO_MODE=true` |

## Rules (first hit wins)
merchant_blacklisted -> merchant_not_whitelisted -> category_blacklisted -> monthly_cap (`spent + amount > 2000`)
-> over_bulk_ceiling (`> 800`) -> over_per_transaction_cap (`> 500` = ESCALATE) -> pass.

## Who logs what (avoid duplicate audit rows)
- Person 1 logs: INTENT_RECEIVED, PLAN, SEARCH, CART_PRICED, POLICY_CHECK, ESCALATION_CREATED, PAYMENT, HALTED.
- This service logs by itself: ESCALATION_APPROVED, ESCALATION_REFUSED, ESCALATION_EXPIRED (also when nobody is watching), LATE_DECISION_IGNORED.
  Person 1 should not log those three again on resume.

## Open items
- `category_blacklist` in `cross_team_config.json` was `[]`; changed to `["Food","Alcohol","Electronics","Health"]` so the snack-pack, condom and electronics cases are blocked.
- `monthly_spent` is supplied by the caller (as in the contract); this service does not track spend itself.
- Approval signature: `Escalation.signature` is returned; send it back as `signature` in the decision body to have it verified. Set `REQUIRE_SIGNATURE=true` to make it mandatory (Person 3 must then send it).
