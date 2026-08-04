# Security Policy

## Supported versions

This repository is a portfolio project. Treat the `main` / default branch as the supported line.

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security problems that could expose users or secrets.

Instead:

1. Email or message the repository owner privately with steps to reproduce.
2. Include impact (auth bypass, data leak, RCE, etc.) and whether a fix suggestion exists.
3. Allow reasonable time for a fix before public disclosure.

## Safe defaults for forks

- Rotate `SECRET_KEY`, database passwords, and any seeded admin credentials before deploying.
- Keep `SEED_DEMO_PASSWORD` and `SEED_ADMIN_PASSWORD` out of production.
- Do not enable Stripe or OpenAI keys in public CI logs.
- Prefer `BILLING_FORCE_LOCAL=true` for demos without real payment processing.
