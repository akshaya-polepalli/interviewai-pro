# Billing & subscriptions (Module 15)

Stripe-shaped SaaS plans with a **local activate** path for demos (no Stripe key required).

## Plans

| Code | Price | Highlights |
|------|-------|------------|
| `free` | $0 | 3 interviews/month, coding, ATS, roadmaps, reports |
| `pro` | $29 | Unlimited interviews, **voice**, **AI coach** |
| `team` | $99 | Pro + priority support / cohort-ready |

## Entitlements gating

| Feature | Free | Pro/Team |
|---------|------|----------|
| Text interviews | 3 / month | Unlimited |
| Voice interviews | ✗ | ✓ |
| AI Coach generate/ask | ✗ | ✓ |

Enforced in `InterviewService.create` and `CoachService.generate_plan` / `ask`.

## Modes

1. **Local** (default) — `BILLING_FORCE_LOCAL=true` or empty `STRIPE_SECRET_KEY`  
   `POST /billing/checkout` activates the plan immediately.
2. **Stripe** — set `STRIPE_SECRET_KEY` + price IDs, set `BILLING_FORCE_LOCAL=false`  
   Checkout returns a Stripe Checkout Session URL.

## API

| Method | Path | Auth |
|--------|------|------|
| GET | `/api/v1/billing/plans` | Public |
| GET | `/api/v1/billing/me` | `billing:read` |
| POST | `/api/v1/billing/checkout` | `billing:write` |
| POST | `/api/v1/billing/activate` | `billing:write` (local only) |
| POST | `/api/v1/billing/cancel` | `billing:write` |
| POST | `/api/v1/billing/webhook/stripe` | Verifies `stripe-signature` when `STRIPE_WEBHOOK_SECRET` is set; syncs plan from checkout / subscription events |

## Config

```env
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
STRIPE_PRICE_PRO=
STRIPE_PRICE_TEAM=
BILLING_FORCE_LOCAL=true
```

## Frontend

Route: `/billing`

## Migration

```bash
docker compose exec api alembic upgrade head
docker compose exec api python -m app.db.seed
docker compose exec api python -m app.db.demo_seed   # demo user is Pro
```

Revision: `c3e2d9f73322`.
