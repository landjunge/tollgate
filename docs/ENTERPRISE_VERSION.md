# Enterprise Version – Roadmap

**Date:** 2026-08-12  
**Status:** Agreed starting point for the Enterprise Edition  
**Principle:** Additive overlay on the existing L1–L7 architecture. The Protect · Route · Prove core, OpenAI drop-in proxy and MCP path stay untouched.

This document is the handoff point so future work or other AIs can continue cleanly.

## Existing Foundation (do not rewrite)

- L3 Virtual Identity + consumers.py (already per-consumer budgets & scopes)
- L4 Admission Control (gateway/admit.py, limits.py) – hard deny before any HTTP call
- L5 Router + Circuits (router.py, gateway/circuit.py)
- L7 Append-only Ledger (usage_ledger.py, audit_log.py)
- Control plane, Dashboard, Freeze, Chaos tests, Certificate scorecard
- Docker + FastAPI already present

## Phased Plan

### Phase 1 – Multi-Tenancy
- Extend the consumer model with `tenant_id` / `org_id`
- Hierarchy: Tenant → Workspace/Consumer → Agent
- Tenant-scoped budgets, scopes, freezes and ledger isolation
- Storage abstraction: SQLite remains the default for single users; optional Postgres for multi-instance / shared deployments

### Phase 2 – Auth & SSO
- FastAPI OIDC middleware (Azure AD, Okta, Google Workspace, …)
- Existing API keys continue to work as scoped Service Accounts mapped to a tenant
- Full backward compatibility with current open-mode labels

### Phase 3 – RBAC
- Roles built on top of existing scopes and policy.py: TenantAdmin, Operator, Viewer, ServiceAccount
- Enforcement inside admission control and control-plane endpoints
- Every role change is written to the audit ledger

### Phase 4 – Governance & Compliance
- Policy-as-Code (versioned policies, similar to current consumer-budget CLI)
- Long-retention audit export + SIEM / webhook support
- Chaos + Certificate as ready-made compliance evidence

### Phase 5 – Ops & Scale
- Helm chart built on the existing Docker image
- Multi-region support using the current health-aware routing and circuit breakers
- Multi-tenant views in the dashboard (extend dashboard_html.py)
- Usage / cost export suitable for internal billing

## What stays the same for normal users
- 10-minute cold-start experience
- Local-first single-user mode when Enterprise features are not activated
- Free-first behaviour defined in NORMAL_VERSION_UX.md

## Next concrete implementation steps
1. Introduce `tenant_id` into the consumer model and ledger schema
2. Make the ledger backend pluggable (SQLite | Postgres)
3. Prototype OIDC middleware without breaking existing key-based auth

This is the agreed handoff point for the Enterprise Edition.
