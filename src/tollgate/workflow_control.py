"""Durable workflow control for explicitly connected, trusted local adapters.

No queue, credential store or network authorization server. Use this boundary at
actual bounded synchronous dispatch, never as an exported allow token. Existing
provider admission and audit still apply. Amounts are integer USD microdollars.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import tempfile
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator

from tollgate.audit_log import append_audit
from tollgate.consumers import consumer_id_is_valid
from tollgate.filelock import FileLock
from tollgate.paths import user_dir


def _unique_pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("duplicate key")
        out[key] = value
    return out


UNIT = "USD_MICRO"
MAX_AMOUNT = 10**15
_ID = re.compile(r"[A-Za-z0-9_.:-]{1,128}\Z")
_HASH = re.compile(r"[a-f0-9]{64}\Z")


class ControlError(RuntimeError):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _id(value: str, *, optional: bool = False) -> None:
    if not isinstance(value, str) or not ((optional and value == "") or _ID.fullmatch(value)):
        raise ControlError("INVALID_ID")


def _money(value: int) -> None:
    if type(value) is not int or not 0 <= value <= MAX_AMOUNT:
        raise ControlError("INVALID_AMOUNT")


@dataclass(frozen=True)
class WorkflowScope:
    project_id: str
    workflow_id: str

    def __post_init__(self):
        _id(self.project_id)
        _id(self.workflow_id)


@dataclass(frozen=True)
class AttemptIdentity:
    scope: WorkflowScope
    task_id: str
    actor_id: str
    consumer_id: str
    attempt_id: str
    request_hash: str
    parent_task_id: str = ""
    subtask_id: str = ""

    def __post_init__(self):
        if not isinstance(self.scope, WorkflowScope):
            raise ControlError("INVALID_SCOPE")
        for key in ("task_id", "actor_id", "consumer_id", "attempt_id"):
            _id(getattr(self, key))
        if not consumer_id_is_valid(self.consumer_id):
            raise ControlError("INVALID_CONSUMER")
        for key in ("parent_task_id", "subtask_id"):
            _id(getattr(self, key), optional=True)
        if not isinstance(self.request_hash, str) or not _HASH.fullmatch(self.request_hash):
            raise ControlError("INVALID_HASH")


@dataclass(frozen=True)
class Quote:
    """Trusted adapter's enforced upper bound, never a model/client estimate.

    Configuring this does not itself prove a provider supports such a cap. Only
    synthetic bounded adapters are accepted in the accompanying acceptance test.
    """
    adapter_id: str
    provider: str
    operation: str
    target_id: str
    max_cost_microusd: int
    price_basis: str

    def __post_init__(self):
        for key in ("adapter_id", "provider", "operation", "target_id", "price_basis"):
            _id(getattr(self, key))
        _money(self.max_cost_microusd)


def _provider_admit(identity: AttemptIdentity, quote: Quote) -> bool:
    from tollgate.gateway.admit import admit
    from tollgate.gateway.context import RequestContext

    return admit(
        quote.provider, op=quote.operation,
        ctx=RequestContext(agent_id=identity.actor_id, consumer=identity.consumer_id,
                           job_id=identity.scope.workflow_id),
    ).allowed


class WorkflowControl:
    """Local trusted coordinator; do not expose methods to unauthenticated clients.

    ``admission`` is injectable only for isolated tests. A real integration uses
    existing admit(). ``send`` must itself enforce the quoted target/cost/timeout
    and must perform its dispatch synchronously before returning. Do not pass a
    scheduler, redirecting client, auto-retrying transport or deferred callback.
    """
    def __init__(self, *, root: Path | None = None,
                 admission: Callable[[AttemptIdentity, Quote], bool] = _provider_admit,
                 lock_timeout_s: float = 1.0,
                 registered_quotes: dict[str, Quote] | None = None,
                 registered_process_actors: dict[str, str] | None = None):
        if (type(lock_timeout_s) not in (int, float)
                or not 0 < lock_timeout_s <= 30 or not math.isfinite(lock_timeout_s)):
            raise ControlError("INVALID_LOCK_TIMEOUT")
        self.root = root
        self.directory = user_dir(root) / "workflow_control"
        self.registered_quotes = dict(registered_quotes or {})
        # Trusted host configuration only. This mode grants no bounded-cost claim.
        self.registered_process_actors = dict(registered_process_actors or {})
        for actor, consumer in self.registered_process_actors.items():
            _id(actor)
            if not consumer_id_is_valid(consumer):
                raise ControlError("INVALID_CONSUMER")
        if any(key != quote.adapter_id for key, quote in self.registered_quotes.items()):
            raise ControlError("INVALID_ADAPTER_REGISTRY")
        self.admission = admission
        self.lock_timeout_s = lock_timeout_s

    def _path(self, scope: WorkflowScope) -> Path:
        digest = hashlib.sha256(json.dumps(asdict(scope), sort_keys=True).encode()).hexdigest()
        return self.directory / (digest + ".json")

    @contextmanager
    def _transaction(self, scope: WorkflowScope) -> Iterator[tuple[Path, dict[str, Any]]]:
        path = self._path(scope)
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with FileLock(path, timeout_s=self.lock_timeout_s):
            if path.exists():
                try:
                    if path.stat().st_size > 8_000_000:
                        raise ValueError("size")
                    data = json.loads(path.read_text(), object_pairs_hook=_unique_pairs)
                    self._validate(data, scope)
                except Exception as exc:
                    raise ControlError("JOURNAL_UNAVAILABLE") from exc
            else:
                data = {"schema": 1, "scope": asdict(scope), "seq": 0,
                        "stopped": False, "stop_id": "", "budgets": {}, "attempts": {}}
            yield path, data

    @staticmethod
    def _validate(data: dict[str, Any], scope: WorkflowScope) -> None:
        if (data["schema"] != 1 or data["scope"] != asdict(scope)
                or type(data["seq"]) is not int or type(data["stopped"]) is not bool
                or data.get("dispatch_mode") not in {None, "bounded", "stop_only"}):
            raise ValueError("schema")
        for actor, budget in data["budgets"].items():
            _id(actor)
            _id(budget["consumer_id"])
            _money(budget["limit"])
            if type(budget["spent"]) is not int or not 0 <= budget["spent"] <= MAX_AMOUNT * 10_000:
                raise ValueError("spent")
        for attempt_id, attempt in data["attempts"].items():
            _id(attempt_id)
            identity = dict(attempt["identity"])
            identity["scope"] = WorkflowScope(**identity["scope"])
            ident = AttemptIdentity(**identity)
            if ident.scope != scope or ident.attempt_id != attempt_id:
                raise ValueError("identity")
            if attempt.get("control_mode") == "stop_only":
                if (data.get("dispatch_mode") != "stop_only" or data["budgets"]
                        or "quote" in attempt or "held" in attempt
                        or attempt["state"] not in {"DISPATCH_ATTEMPTED", "OUTCOME_UNKNOWN", "DENIED"}
                        or type(attempt.get("spawn_observed")) is not bool):
                    raise ValueError("stop-only schema")
                continue
            if data.get("dispatch_mode") == "stop_only":
                raise ValueError("mixed control modes")
            quote = Quote(**attempt["quote"])
            if attempt["state"] not in {"RESERVED", "DISPATCH_ATTEMPTED", "OUTCOME_UNKNOWN",
                                        "SETTLED", "CANCELLED_NO_SEND", "DENIED"}:
                raise ValueError("state")
            _money(attempt["held"])
            if attempt["held"] > quote.max_cost_microusd:
                raise ValueError("held")

    @staticmethod
    def _commit(path: Path, data: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        data["seq"] += 1
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        fd, name = tempfile.mkstemp(dir=path.parent, prefix=".control-", suffix=".tmp")
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "w") as stream:
                json.dump(data, stream, sort_keys=True, separators=(",", ":"))
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, path)
            if os.name != "nt":
                dirfd = os.open(path.parent, os.O_RDONLY)
                try:
                    os.fsync(dirfd)
                finally:
                    os.close(dirfd)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def _audit(self, event: str, scope: WorkflowScope, *, code: str = "OK") -> None:
        # No prompt/content digest, payload, URL, secrets or raw identities exported.
        append_audit("workflow_" + event, op=event, ok=code == "OK", error=code,
                     extra={"scope_ref": self._path(scope).stem}, root=self.root)

    def _admitted(self, identity: AttemptIdentity, quote: Quote) -> bool:
        try:
            return self.admission(identity, quote) is True
        except Exception:
            # Dependency text may contain credentials; never expose or audit it.
            raise ControlError("DEPENDENCY_UNAVAILABLE") from None

    @staticmethod
    def _binding(identity: AttemptIdentity, quote: Quote) -> dict[str, Any]:
        return {"identity": asdict(identity), "quote": asdict(quote)}

    @staticmethod
    def _existing(data: dict[str, Any], identity: AttemptIdentity,
                  quote: Quote | None = None) -> dict[str, Any]:
        attempt = data["attempts"].get(identity.attempt_id)
        if attempt is None:
            raise ControlError("ATTEMPT_NOT_FOUND")
        if attempt["identity"] != asdict(identity) or (quote and attempt["quote"] != asdict(quote)):
            raise ControlError("IDEMPOTENCY_CONFLICT")
        return attempt

    @staticmethod
    def _summary(data: dict[str, Any], actor_id: str) -> dict[str, Any]:
        budget = data["budgets"][actor_id]
        held = sum(a["held"] for a in data["attempts"].values()
                   if a["identity"]["actor_id"] == actor_id)
        return {"actor_id": actor_id, "consumer_id": budget["consumer_id"],
                "unit": UNIT, "limit": budget["limit"], "spent": budget["spent"],
                "reserved": held, "available": max(0, budget["limit"] - budget["spent"] - held),
                "cost_kind": "evidenced_final" if any(
                    a["state"] == "SETTLED" and a["identity"]["actor_id"] == actor_id
                    for a in data["attempts"].values()) else "no_final_cost",
                "incident": budget.get("incident", False)}

    def configure_budget(self, scope: WorkflowScope, actor_id: str, consumer_id: str,
                         limit_microusd: int, *, authorize_increase: bool = False) -> None:
        """Trusted operator configuration, not an agent tool. Existing lane never migrates."""
        _id(actor_id)
        _id(consumer_id)
        if not consumer_id_is_valid(consumer_id):
            raise ControlError("INVALID_CONSUMER")
        _money(limit_microusd)
        with self._transaction(scope) as (path, data):
            if data.get("dispatch_mode") == "stop_only":
                raise ControlError("CONTROL_MODE_CONFLICT")
            data["dispatch_mode"] = "bounded"
            previous = data["budgets"].get(actor_id)
            if previous:
                if previous["consumer_id"] != consumer_id:
                    raise ControlError("BUDGET_LANE_CONFLICT")
                if limit_microusd > previous["limit"] and authorize_increase is not True:
                    raise ControlError("BUDGET_INCREASE_NOT_AUTHORIZED")
                previous["limit"] = limit_microusd
            else:
                data["budgets"][actor_id] = {"consumer_id": consumer_id,
                                             "limit": limit_microusd, "spent": 0}
            self._commit(path, data)
        self._audit("budget", scope)

    def reserve(self, identity: AttemptIdentity, quote: Quote) -> dict[str, Any]:
        with self._transaction(identity.scope) as (path, data):
            if data.get("dispatch_mode") == "stop_only":
                raise ControlError("CONTROL_MODE_CONFLICT")
            if identity.attempt_id in data["attempts"]:
                return self._project_attempt(self._existing(data, identity, quote))
            if len(data["attempts"]) >= 10_000:
                raise ControlError("JOURNAL_CAPACITY")
            budget = data["budgets"].get(identity.actor_id)
            if not budget or budget["consumer_id"] != identity.consumer_id:
                raise ControlError("BUDGET_LANE_CONFLICT")
            reason = "OK"
            if self.registered_quotes.get(quote.adapter_id) != quote:
                reason = "UNBOUNDED_COST"
            elif data["stopped"]:
                reason = "WORKFLOW_STOPPED"
            elif budget.get("incident"):
                reason = "ACCOUNTING_MISMATCH"
            elif quote.max_cost_microusd > self._summary(data, identity.actor_id)["available"]:
                reason = "BUDGET_EXCEEDED"
            elif not self._admitted(identity, quote):
                reason = "ADMISSION_DENIED"
            attempt = {**self._binding(identity, quote),
                       "state": "RESERVED" if reason == "OK" else "DENIED",
                       "held": quote.max_cost_microusd if reason == "OK" else 0,
                       "reason_code": reason}
            data["attempts"][identity.attempt_id] = attempt
            self._commit(path, data)
            result = self._project_attempt(attempt)
        self._audit("reserve", identity.scope, code=reason)
        return result

    def dispatch(self, identity: AttemptIdentity, send: Callable[[], Any]) -> dict[str, Any]:
        """Exactly one *local attempt*. No replay even after a crash before actual send.

        Lock spans the real bounded send. Stop can return PENDING while it is held;
        only a committed stop barrier confirms that further dispatch is blocked.
        Callback return value is deliberately not persisted or returned.
        """
        with self._transaction(identity.scope) as (path, data):
            attempt = self._existing(data, identity)
            if attempt.get("control_mode") == "stop_only":
                raise ControlError("CONTROL_MODE_CONFLICT")
            if attempt["state"] != "RESERVED":
                return self._project_attempt(attempt)
            quote = Quote(**attempt["quote"])
            budget = data["budgets"][identity.actor_id]
            summary = self._summary(data, identity.actor_id)
            deny = ""
            if data["stopped"]:
                deny = "WORKFLOW_STOPPED"
            elif budget.get("incident"):
                deny = "ACCOUNTING_MISMATCH"
            elif summary["spent"] + summary["reserved"] > summary["limit"]:
                deny = "BUDGET_EXCEEDED"
            elif self.registered_quotes.get(quote.adapter_id) != quote:
                deny = "UNBOUNDED_COST"
            elif not self._admitted(identity, quote):
                deny = "ADMISSION_DENIED"
            if deny:
                attempt.update(state="CANCELLED_NO_SEND", held=0, reason_code=deny)
                self._commit(path, data)
                self._audit("dispatch", identity.scope, code=deny)
                return self._project_attempt(attempt)
            from tollgate.usage_ledger import try_reserve_day_call

            try:
                day = try_reserve_day_call(quote.provider, consumer=identity.consumer_id,
                                           op=quote.operation, root=self.root)
            except Exception:
                raise ControlError("DEPENDENCY_UNAVAILABLE") from None
            if not day.get("ok"):
                attempt.update(state="CANCELLED_NO_SEND", held=0, reason_code="DAY_LIMIT_DENIED")
                self._commit(path, data)
                self._audit("dispatch", identity.scope, code="DAY_LIMIT_DENIED")
                return self._project_attempt(attempt)
            attempt["day_call_reserved"] = bool(day.get("reserved"))
            attempt.update(state="DISPATCH_ATTEMPTED", reason_code="AWAITING_FINAL_EVIDENCE")
            self._commit(path, data)  # must succeed before touching the outside world
            try:
                send()
            except BaseException:
                attempt.update(state="OUTCOME_UNKNOWN", reason_code="OUTCOME_UNKNOWN")
                self._commit(path, data)
                self._audit("dispatch", identity.scope, code="OUTCOME_UNKNOWN")
                return self._project_attempt(attempt)
            # HTTP success does not attest final billing or external acceptance.
            self._audit("dispatch", identity.scope)
            return self._project_attempt(attempt)

    def settle(self, identity: AttemptIdentity, actual_microusd: int,
               settlement_id: str, evidence_ref: str) -> dict[str, Any]:
        """Trusted final-cost evidence required; never call from model/HTTP200 alone."""
        _money(actual_microusd)
        _id(settlement_id)
        _id(evidence_ref)
        with self._transaction(identity.scope) as (path, data):
            attempt = self._existing(data, identity)
            if attempt.get("control_mode") == "stop_only":
                raise ControlError("CONTROL_MODE_CONFLICT")
            settlement = {"settlement_id": settlement_id, "evidence_ref": evidence_ref,
                          "actual_microusd": actual_microusd}
            if attempt["state"] == "SETTLED":
                if attempt["settlement"] != settlement:
                    raise ControlError("SETTLEMENT_CONFLICT")
                return self._project_attempt(attempt)
            if any(other is not attempt and other.get("settlement", {}).get("settlement_id") == settlement_id
                   for other in data["attempts"].values()):
                raise ControlError("SETTLEMENT_CONFLICT")
            if attempt["state"] not in {"DISPATCH_ATTEMPTED", "OUTCOME_UNKNOWN"}:
                raise ControlError("SETTLEMENT_NOT_ALLOWED")
            budget = data["budgets"][identity.actor_id]
            budget["spent"] += actual_microusd
            if actual_microusd > attempt["quote"]["max_cost_microusd"]:
                budget["incident"] = True
            attempt.update(state="SETTLED", held=0, settlement=settlement,
                           reason_code="ACCOUNTING_MISMATCH" if budget.get("incident") else "OK")
            self._commit(path, data)
            result = self._project_attempt(attempt)
        self._audit("settle", identity.scope, code=result["reason_code"])
        return result

    @contextmanager
    def process_start(self, identity: AttemptIdentity) -> Iterator[dict[str, Any]]:
        """Hold the existing scope barrier over actual owned spawn and registration.

        Stop-only is an explicit trusted-host mode for CLI processes with unknown
        cost. It cannot enter or replace a bounded-budget scope. The caller must
        keep this context open across the actual spawn (including an async await)
        and owned process registration. Never export ``start_allowed`` as a token.
        A durable attempt is never replayed, including after crash/unknown spawn.
        """
        if self.registered_process_actors.get(identity.actor_id) != identity.consumer_id:
            raise ControlError("PROCESS_ADAPTER_UNAVAILABLE")
        with self._transaction(identity.scope) as (path, data):
            if data.get("dispatch_mode") not in {None, "stop_only"} or data["budgets"] or any(
                a.get("control_mode") != "stop_only" for a in data["attempts"].values()
            ):
                raise ControlError("CONTROL_MODE_CONFLICT")
            if identity.attempt_id in data["attempts"]:
                attempt = self._existing(data, identity)
                yield {**self._project_attempt(attempt), "start_allowed": False}
                return
            if len(data["attempts"]) >= 10_000:
                raise ControlError("JOURNAL_CAPACITY")
            data["dispatch_mode"] = "stop_only"
            attempt = {
                "identity": asdict(identity), "control_mode": "stop_only",
                "state": "DENIED" if data["stopped"] else "DISPATCH_ATTEMPTED",
                "reason_code": "WORKFLOW_STOPPED" if data["stopped"] else "PROCESS_START_UNKNOWN",
                "spawn_observed": False,
            }
            data["attempts"][identity.attempt_id] = attempt
            self._commit(path, data)
            if data["stopped"]:
                yield {**self._project_attempt(attempt), "start_allowed": False}
                return
            try:
                yield {**self._project_attempt(attempt), "start_allowed": True}
            except BaseException:
                attempt.update(state="OUTCOME_UNKNOWN", reason_code="PROCESS_START_UNKNOWN")
                self._commit(path, data)
                raise
            else:
                attempt.update(spawn_observed=True, reason_code="PROCESS_SPAWN_OBSERVED")
                self._commit(path, data)
        self._audit("process_start", identity.scope)

    def stop(self, scope: WorkflowScope, stop_id: str) -> dict[str, Any]:
        _id(stop_id)
        try:
            with self._transaction(scope) as (path, data):
                if not data["stopped"]:
                    data.update(stopped=True, stop_id=stop_id, barrier_seq=data["seq"] + 1)
                    for attempt in data["attempts"].values():
                        if attempt["state"] == "RESERVED":
                            attempt.update(state="CANCELLED_NO_SEND", held=0,
                                           reason_code="WORKFLOW_STOPPED")
                    self._commit(path, data)
                result = {"status": "EFFECTIVE", "further_dispatch_blocked": True,
                          "stop_id": data["stop_id"], "barrier_seq": data["barrier_seq"],
                          "abort_confirmed": False,
                          "external_effect": "unknown" if any(a["state"] in {
                              "DISPATCH_ATTEMPTED", "OUTCOME_UNKNOWN"} for a in data["attempts"].values())
                              else "no_unresolved_dispatch"}
        except TimeoutError:
            return {"status": "PENDING", "further_dispatch_blocked": False,
                    "abort_confirmed": False, "external_effect": "unknown"}
        self._audit("stop", scope)
        return result

    @staticmethod
    def _project_attempt(attempt: dict[str, Any]) -> dict[str, Any]:
        # Private request hashes and arbitrary adapter output stay out of reports.
        if attempt.get("control_mode") == "stop_only":
            return {
                "attempt_id": attempt["identity"]["attempt_id"], "control_mode": "stop_only",
                "state": "OUTCOME_UNKNOWN" if attempt["state"] == "DISPATCH_ATTEMPTED" else attempt["state"],
                "dispatch_started": attempt["state"] != "DENIED",
                "spawn_observed": attempt["spawn_observed"], "reason_code": attempt["reason_code"],
                "cost_kind": "unknown", "hard_cost_cap": False,
                "project_completion_verified": False,
            }
        return {"attempt_id": attempt["identity"]["attempt_id"],
                "state": "OUTCOME_UNKNOWN" if attempt["state"] == "DISPATCH_ATTEMPTED" else attempt["state"],
                "dispatch_started": attempt["state"] in {"DISPATCH_ATTEMPTED", "OUTCOME_UNKNOWN", "SETTLED"},
                "reason_code": attempt["reason_code"], "reserved_microusd": attempt["held"],
                "unit": UNIT, "day_call_reserved": attempt.get("day_call_reserved", False),
                "project_completion_verified": False}

    def get_attempt(self, identity: AttemptIdentity) -> dict[str, Any]:
        with self._transaction(identity.scope) as (_, data):
            return self._project_attempt(self._existing(data, identity))

    def status(self, scope: WorkflowScope) -> dict[str, Any]:
        with self._transaction(scope) as (_, data):
            return {"scope": asdict(scope), "seq": data["seq"], "updated_at": data.get("updated_at"),
                    "stopped": data["stopped"],
                    "budgets": [self._summary(data, actor) for actor in sorted(data["budgets"])],
                    "attempts": [self._project_attempt(a) for a in data["attempts"].values()]}
