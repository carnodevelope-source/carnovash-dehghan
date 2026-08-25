# Idempotency Inventory — 2026-08-25

All authenticated unsafe browser requests now receive `Idempotency-Key` from
the central Axios interceptor. The backend scopes records by tenant, user, and
key; exact retries replay completed JSON, competing work returns 409, changed
payload/key reuse returns 409, expired entries are reclaimed under row lock.
Non-browser/API clients must send the same header themselves for equivalent
protection; the header is intentionally not made mandatory yet to preserve the
published legacy API contract.

| Endpoint group | Methods | Mutation / duplicate impact | Financial or critical | Current protection |
| --- | --- | --- | --- | --- |
| `/api/vehicles/`, detail/status/job-adjust/release/block/unblock | POST/PATCH | request, task state, release, block state | Critical; release may be financial | Axios key + server replay/409; local submit guards. |
| `/api/inventory/`, `/purchase/`, `/expenses/` | POST/PUT/PATCH/DELETE | stock and expense mutations | Financial/critical | Axios key + server replay/409. |
| `/api/payments/wallet/*` | POST | wallet deposit, checkout, withdraw, feature option/installment | Financial/critical | Axios key + server replay/409. |
| `/api/reports/payouts/settle/`, `/workers/payouts/`, `/workers/adjustments/` | POST | payout and adjustment | Financial/critical | Axios key + server replay/409. |
| `/api/services/`, `/products/`, `/workers/` | POST/PUT/PATCH/DELETE | catalog, worker, settings changes | Critical configuration | Axios key + server replay/409. |
| `/api/notifications/*` | POST/PUT/PATCH/DELETE | import, groups/templates, campaign send | Critical/cost-bearing SMS | Axios key + server replay/409. |
| `/api/auth/support/*`, `/users/`, tenant/HQ ticket/team/carwash actions | POST/PATCH/DELETE | requests, approval/reject, account and wallet support actions | Critical; wallet actions financial | Axios key + server replay/409. |
| `/api/subscriptions/hq/*` actions/orders/bulk/alerts/seed | POST | approve/reject, order/task/bulk changes | Critical | Axios key + server replay/409. |
| Login, public attendance, CSRF | POST / public POST | authentication or attendance event | Different trust model | Middleware does not claim authenticated idempotency; endpoint-specific business safeguards remain required. |

## Concurrency and recovery tests

Local backend coverage includes same key/same body, changed body, pending key,
expired key reclamation, restart-style replay, and two real concurrent requests
with exactly one view execution. It does not invent success for an external
client that omits the header; staging must test representative payment and SMS
flows with browser and non-browser clients.
