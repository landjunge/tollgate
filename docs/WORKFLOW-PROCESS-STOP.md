# Owned CLI process stops / Eigene CLI-Prozesse stoppen

## Deutsch

Die optionale `WorkflowControl(..., registered_process_actors={actor: consumer})`
Assembly ist ausschließlich vertrauenswürdige Betreiberkonfiguration. Standard:
keine Prozessadapter. `with control.process_start(identity) as receipt:` hält die
vorhandene auftragseigene Journal-/Dateisperre über den **tatsächlichen** Prozessstart
und dessen Eigentümerregistrierung. Bei async-Aufrufern muss sie auch während
`await spawn` offen bleiben. `start_allowed` ist kein exportierbarer Allow-Token.
Die bestehende `stop(scope, stop_id)`-Operation teilt dieselbe Sperre.

Vor einem zulässigen Start wird DISPATCH_ATTEMPTED dauerhaft gespeichert. Ein
Abbruch/Crash bleibt OUTCOME_UNKNOWN und wird bei Wiederholung nicht gestartet;
`spawn_observed` beschreibt nur den vom Adapter beobachteten Start, kein Ende.
Ein gesperrter Auftrag bleibt über Neustarts gesperrt. Bei noch belegter Sperre
meldet Stop PENDING; erst die gespeicherte Barriere meldet EFFECTIVE. Das beendet
keinen Prozess: gezielter Abbruch und beobachtetes Ende gehören zum eigenen
Prozessadapter. Bereits eingetretene oder externe Restwirkung bleibt unbekannt.

**Stop-only ist keine Budgetfreigabe.** CLI-Kosten sind unbekannt, es gibt keinen
belegten harten Dollarcap, keine erfundene Nullkostenquote und keine Geldreserve.
Budgetierte und stop-only-Scopes lassen sich gegenseitig nicht umstellen. Die
bestehenden kostenbegrenzten Quote-/Reservierungs-/Dispatchwege bleiben erhalten.
Das neue optionale Feld `dispatch_mode` und stop-only-Einträge liegen additiv im
vorhandenen Journal; keine neue Queue oder parallele Kontrollablage.

Gezielte synthetische Prüfung: `pytest -q tests/test_workflow_process_stop.py
 tests/test_workflow_control.py` (26 Fälle). Kein echter Provider/Bezahllauf.

## English

An explicitly trusted host may register actor/consumer pairs and keep the
`process_start(identity)` context open across actual spawn **and owned session
registration**, including an asynchronous await. The existing durable workflow
journal/lock orders this against `stop`; this is not an early allow token.
PENDING is not a committed barrier; EFFECTIVE does not establish process exit.
Crash/unknown attempts never replay. The attached process adapter must terminate
only its own registered process and report observed exit separately.

This optional CLI path is **stop-only**: cost unknown, hard_cost_cap=false, no
zero-dollar quote or financial reservation. Bounded-budget scopes cannot be
downgraded into it, or upgraded by silently changing mode. Old budget journals
remain readable. No queue, external transport, provider calls, installation or
runtime activation is added by this source change. Targeted tests use synthetic
identities and effects only; existing admission and bounded-cost dispatch remain
independent controls.
