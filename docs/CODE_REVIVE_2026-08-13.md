# Code revive — team mode (2026-08-13)

**Not a rewrite.** Hygiene after modular slices M8–M11, under architect rules.

## Intent

| Do | Don’t |
|----|--------|
| Fix regressions from extraction | Big Clean Architecture |
| soft_fail instead of silent `pass` | Touch admit core |
| Dead imports / NameError | New features |
| Keep public API | Microservice split |

## Fixes in this revive

1. **Bug:** dashboard still called `el_mod` after M9 registry extract → **NameError** if elevenlabs ready — fixed via `get_ops("elevenlabs")["budget"]`
2. **Observability:** `package_deny`, router health map, free_policy config load, inspect kwargs → `soft_fail`
3. **Lint dead weight:** unused imports (`catalog.field`, `control_plane.json`, `filelock.os`, `metrics.Any`, unused `RequestClass` in router, dead `audit_pass`)
4. **Docs:** KeysService docstring points at `provider_ops`

## Verify

```bash
pytest -q          # 188+
tollgate doctor    # PASS / production readiness
```

## Still out of scope (pain-driven later)

- Full ProviderAdapter classes per provider
- entry.py file split
- Bare `except` in distant modules (cli, dashboard HTML)

*Team rule: each module still answers one question. Revive does not invent new questions.*
