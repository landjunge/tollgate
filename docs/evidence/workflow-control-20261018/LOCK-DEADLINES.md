# Begrenzte Sperrwartezeit / bounded lock deadline

Integrationsprüfung auf Basis c3a062d vom18.10.2026: NaN als explizites
lock_timeout_s konnte den Ablaufvergleich dauerhaft falsch halten. Die vorherige
FileLock-Frist verwendete außerdem die verstellbare Wanduhr; bei Timeout wurde der
in __enter__ geöffnete Deskriptor nicht geschlossen. Dies sind konkrete Codefehler,
kein nachgewiesener früherer Produktionsausfall und keine Ursache der separaten
KiraBridge-Programmlistenfehler.

WorkflowControl lehnt ungültige Typen, NaN/Inf und Wartezeiten außerhalb0–30s vor
Statezugriff ab (0 ebenfalls ungültig). FileLock validiert endliche nichtnegative
Zahlen, verwendet monotonic und schließt beim gescheiterten Eintritt den eigenen
Deskriptor. Bestehender Standard und G02-Dispatch-/Stoppvertrag bleiben erhalten.

16 gezielte Fälle bestanden: ungültige Werte einschließlich riesiger Integer,
monotone Frist ohne Wanduhrzugriff, Deskriptorfreigabe sowie bestehender echter
kontendierter Send-/Stoppfall mit PENDING statt falscher Beendigungsbehauptung.
Keine Providerkontakte, Budget-/Schlüsseländerung oder Runtimeumschaltung.
Die vorhandene PR-CI prüft den geänderten Stand regulär.

English: invalid/nonfinite lock waits are rejected before state access. Deadlines
use monotonic time and failed entry closes its descriptor. Sixteen focused checks
passed, including the existing contended send/stop case. This does not prove every
external adapter can be cancelled or that all production actions cross this gate.
