# Normal Version – UX & Intelligence Priorities

**Date:** 2026-08-12  
**Status:** Agreed starting point for the community / normal version  
**Core principles:** Absolutely user-friendly + always cost-saving (Free-first)

This document captures the priorities for improving the normal (non-Enterprise) version of Tollgate so that future work or other AIs can continue cleanly.

## Prioritized Improvements

1. **Free-first as default**
   - `tollgate init` / first-run starts in Free-only mode
   - Only free models (e.g. OpenRouter free variants)
   - Clear remaining free quota visible in dashboard and responses
   - No silent spillover to paid providers

2. **Guided simple entry**
   - One command that creates a safe Free-consumer
   - Opens the dashboard
   - Explains next steps in plain language

3. **Automatic agent registration (auto free-mode)**
   - Unknown agents / consumers arriving via the proxy are automatically created in Free-mode
   - Short notification to the user
   - User keeps full control; no manual setup required for basic use

4. **Clear block feedback**
   - Structured reason + remaining free budget + suggested next action
   - Visible both in API responses and in the dashboard

5. **Light free-model preference**
   - Quietly prefer free models that have worked reliably for this user

## Implementation Notes

- Build on existing free request-class, soft budgets, OpenRouter support, consumers, dashboard and L4 admission control
- Keep the Protect · Route · Prove core completely untouched
- All changes must remain additive and preserve the 10-minute cold-start experience

## Next concrete steps

- Implement Free-first defaults in init flow
- Auto-create unknown consumers in free mode with notification
- Improve block response format and dashboard visibility of remaining quota

This is the agreed handoff point for the normal version.
