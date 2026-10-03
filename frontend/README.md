# Frontend — HacKU Time-Grocer (Person 3)

Vue 3 + Vite dashboard for the agent checkout. The spec is [`contract.json`](contract.json).

## Run

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173.

## Mock vs live

By default the app uses a **fake backend in the browser** (`src/lib/mock.js`), built from the
contract's examples, so every screen works before the agent and policy services exist.

To call the real services, create `frontend/.env.local`:

```
VITE_USE_MOCK=false
VITE_AGENT_URL=http://localhost:8002
VITE_POLICY_URL=http://localhost:8001
```

## Where things are

| File | What it does |
|------|--------------|
| `src/App.vue` | Page state: sends the intent, polls the escalation every second, handles Approve/Refuse |
| `src/lib/api.js` | The only four calls the frontend makes (`contract.json` → `calls`) |
| `src/lib/mock.js` | Fake agent + policy API for local work |
| `src/lib/hash.js` | Checks the audit log's sha256 hash chain in the browser |
| `src/components/` | One component per card on the screen |

## Demo scenarios

- **Normal order:** "Buy toilet paper" with HK$0 spent. Shows *Order placed* (HK$119.90).
- **Monthly cap hit:** the same intent with HK$1,900 spent. Shows *Halted*.
- **Bulk:** "Buy bulk toilet paper". Shows *Needs your approval* and a 10:00 timer. Approve completes the order; Refuse cancels it.
