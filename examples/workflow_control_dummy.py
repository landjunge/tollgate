"""One disposable workflow; no keys, providers, network or persistent user data."""
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from tollgate.workflow_control import AttemptIdentity, Quote, WorkflowControl, WorkflowScope


def main():
    with TemporaryDirectory(prefix="tollgate-workflow-demo-") as directory:
        os.environ["TOLLGATE_HOME"] = directory
        scope = WorkflowScope("dummy-project", "dummy-workflow")
        quote = Quote("dummy-v1", "dummy", "quota-read", "local-dummy", 60, "fixed-dummy-v1")
        # Test-only admission: production must use existing admit(), not this lambda.
        control = WorkflowControl(root=Path(directory), admission=lambda *_: True,
                                  registered_quotes={quote.adapter_id: quote})
        control.configure_budget(scope, "codex", "codex-lane", 100)
        identity = AttemptIdentity(scope, "thread:task", "codex", "codex-lane", "attempt-1", "a" * 64)
        effects = []
        control.reserve(identity, quote)
        control.dispatch(identity, lambda: effects.append("synthetic-dispatch"))
        control.dispatch(identity, lambda: effects.append("would-be-duplicate"))
        # Synthetic test evidence only, not a provider bill or real cost claim.
        control.settle(identity, 40, "synthetic-settlement", "synthetic-evidence")
        stop = control.stop(scope, "stop-1")
        next_identity = AttemptIdentity(scope, "thread:task", "codex", "codex-lane", "attempt-2", "b" * 64)
        denied = control.reserve(next_identity, quote)
        result = {"synthetic_only": True, "effects": effects, "stop": stop,
                  "denied": denied, "status": control.status(scope)}
        assert effects == ["synthetic-dispatch"]
        assert denied["reason_code"] == "WORKFLOW_STOPPED"
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
