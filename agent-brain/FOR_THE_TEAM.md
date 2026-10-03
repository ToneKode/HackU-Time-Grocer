# What the other people need to do

Person 1 (this PR) is the shopping agent on port **8002**.

`POST /agent/intent` takes `{ "intent": "...", "monthly_spent": 0 }` and returns one ActionPlan JSON. An OpenRouter model may choose only the query, the quantity, and a sell point (`cheap`, `highest_usage`, `best_rating`). Code picks the product. The hash-chained `audit_log` is on every response.

Two things are stand-ins on purpose:

- The mall is the JSON in `agent-brain/backend/fake_mall/` until person 4's server is up.
- Person 2's cap check is skipped. The log still records `POLICY_CHECK` / `SKIPPED`. The agent then pays the fake mall.

`frontend/index.html` is a **test counter** served at `GET /` on port 8002. Person 3 already has their own frontend. Do not replace it with this page. Someone else can wire the real UI to this JSON later.

Do not commit `agent-brain/backend/.env`. Each machine keeps its own `OPENROUTER_API_KEY`. A model id ending in `:batch` will not work on this chat endpoint. Use `deepseek/deepseek-v4.1-flash` or `openrouter/free`.

Run from `agent-brain/backend` with Python 3.13:

```powershell
py -3.13 -m pip install -r requirements.txt
py -3.13 test_agent.py
py -3.13 server.py
```

Open `http://127.0.0.1:8002` to try the test counter.

## Person 2 — policy, ledger, escalation (port 8001)

The agent does not call you yet. `_budget` in `agent-brain/backend/agent_graph.py` always returns status `SKIPPED` and still allows payment. `policy_rules.py` still has the frozen numbers for when you are ready.

Build:

- `POST /check_policy` with `merchant`, `category`, `amount`, `currency` (`HKD`), `monthly_spent`. Return `status` `PASS`, `ESCALATE`, or `HALT`, plus `reason`, the caps, and `monthly_remaining`.
- `POST /log_event` with `event`, `status`, `reason`. The agent already posts each audit line here. If you are down, it stops retrying after the first failure and still returns its own chain.
- `POST /create_escalation`, `GET /escalations/{id}`, `POST /escalations/{id}/decision`.
- `GET /audit_log` for person 3's ledger view.

Rules to implement, first match wins: merchant blacklist, merchant not on the whitelist, category blacklist, monthly total over HK$2000, amount over HK$800, amount over HK$500 (escalate, 600 second TTL), otherwise pass. Whitelist: Watsons, HKTVmall, PARKnSHOP, Japan Home Centre. Blacklist: DarkWebMart. Category blacklist is empty.

Do not let the model decide pass, halt, or pay. You do.

## Person 3 — real frontend

Keep your own app. Use `frontend/index.html` only as a sample of the request and the JSON.

Your app should call only:

- `POST http://127.0.0.1:8002/agent/intent`
- person 2's escalation routes and `GET /audit_log`, once those exist

Do not call `/products`, `/cart`, `/pay`, `/check_policy`, `/log_event`, or `/create_escalation` from the browser.

Request body: `intent` (required), `monthly_spent` (optional, default 0), `escalation_id` (optional).

Response fields: `intent`, `status`, `goal`, `product`, `quote`, `policy`, `escalation`, `payment`, `audit_log`.

New fields since `frontend/contract.json`: `product.sell_point`, and on `goal` also `sell_point`, `sku`, `thought`, `model`. `policy.status` is `SKIPPED` until person 2 is connected. `payment` has no reward-points field.

## Person 4 — mock mall (port 8000)

Your API on `dev` is the right shape. The agent is not pointed at it yet. While `MOCK_API_BASE_URL` is unset, person 1 reads `agent-brain/backend/fake_mall/*.json`.

Please:

1. Add `sell_point` to the product model in `mockup-mall/mock-api/data_loader.py` and return it from `GET /products` and `GET /products/{sku}`. Extra JSON keys are dropped today, so copying the file alone is not enough.
2. Replace `mockup-mall/mock-api/data/products.json` with the 30 products in `agent-brain/backend/fake_mall/products.json` (10 categories, 3 products each: `cheap`, `highest_usage`, `best_rating`), or add the same field to your own catalog.
3. Keep `POST /cart` as `{ "items": [{ "sku", "qty" }] }` and return `total_landed_cost`. Shipping stays HK$30 under HK$400, free at HK$400 and above, tax 0.
4. Keep `POST /pay`. You may still return `reward_points_earned`. Person 1 ignores it. `cart_total == 666` still declines with `card_declined`.

Search should match name, merchant, category, and sell point. The agent picks one sku and then calls `GET /products/{sku}`, `POST /cart`, and `POST /pay`.

## Whoever integrates

1. Start person 4 on port 8000. Set `MOCK_API_BASE_URL=http://127.0.0.1:8000` for person 1 and restart. Leave it unset to keep the fake JSON.
2. Start person 2 on port 8001. Replace the skip in `_budget` with `PolicyClient.check`, and branch on `PASS` / `ESCALATE` / `HALT` again. Pay only after `PASS` or an approved escalation.
3. Point person 3's app at `POST /agent/intent`. Leave `frontend/index.html` as the test counter.
4. Put an OpenRouter key in `agent-brain/backend/.env`. Do not use a `:batch` model id.
