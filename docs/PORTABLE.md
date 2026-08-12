# Portable / USB

Tollgate must run from a **stick or external volume** without any `/Users/…` or host-only paths.

**No Docker.** Primary path is **venv + `scripts/run.sh`** on the volume. Containers are optional and not part of the USB story.

## Layout (recommended)

```
/Volumes/STICK/                 # or /media/… /mnt/…
  tollgate/                     # git clone + optional .venv
    scripts/run.sh
    src/tollgate/
  WS-tollgate/                  # data sibling (secrets stay out of git tree)
    User/
      Key.txt
      keys_app.json             # auto-created
      keys_usage.json           # ledger
```

Colocated alternative (single folder)::

```
/Volumes/STICK/tollgate/
  User/Key.txt
  .venv/
  src/
```

## Env (priority)

| Variable | Role |
|----------|------|
| `TOLLGATE_HOME` | Explicit data root (best for USB) |
| `GNOM_WS` | Compat if Gnom workspace is the data root |
| `TOLLGATE_PORTABLE=1` | Force portable resolution even off USB mounts |
| *(auto)* | Code under `/Volumes`, `/media`, `/run/media`, `/mnt` → portable |
| *(fallback desk)* | `~/.tollgate` |

Resolution code: `src/tollgate/paths.py`.

## Setup once on the stick

```bash
cd /path/to/tollgate
./scripts/portable-setup.sh
# Gnom-style data dir name (optional):
#   WS_NAME=WS-gnom-hub-v1 ./scripts/portable-setup.sh
# edit WS-*/User/Key.txt
./scripts/run.sh
./scripts/portable-smoke.sh   # offline path check, no network
```

### Stick + Gnom-Hub (same volume, no Docker)

```text
/Volumes/STICK/
  tollgate/           # this repo + .venv
  gnom-hub-v1/        # optional desk UI
  WS-gnom-hub-v1/     # shared data (Key.txt, ledger, gnom user.db)
    User/Key.txt
```

```bash
export TOLLGATE_HOME=/Volumes/STICK/WS-gnom-hub-v1
export GNOM_WS=$TOLLGATE_HOME
export TOLLGATE_URL=http://127.0.0.1:8787
export GNOM_TOLLGATE_LLM=1
# Terminal A
/Volumes/STICK/tollgate/scripts/run.sh
# Terminal B — start gnom-hub as usual with same env
```

## Snapshot migrate (v0.3.3+)

Move **ops state** between hosts / sticks without re-typing envelopes:

```bash
# on source desk (Key.txt NOT included by default)
tollgate snapshot export -o desk.tgz
tollgate snapshot info desk.tgz

# on target (set TOLLGATE_HOME first)
tollgate snapshot import desk.tgz --dry-run
tollgate snapshot import desk.tgz
# optional full overwrite:
# tollgate snapshot import desk.tgz --replace

# only if you deliberately want secrets in the archive:
tollgate snapshot export -o desk-secrets.tgz --include-secrets
```

Includes: `keys_app.json`, `consumers.json` (hashes), ledger, circuits, chaos, audit.  
Excludes: `Key.txt` / `.env` unless `--include-secrets`.

Health shows where data landed::

```bash
curl -s http://127.0.0.1:8787/v1/health | jq .portable
```

Example::

```json
{
  "project_root": "/Volumes/STICK/tollgate",
  "data_home": "/Volumes/STICK/WS-tollgate",
  "user_dir": "/Volumes/STICK/WS-tollgate/User",
  "portable": true,
  "usb": true
}
```

## MCP on portable hosts

```json
{
  "mcpServers": {
    "tollgate": {
      "command": "python",
      "args": ["-m", "tollgate"],
      "env": {
        "TOLLGATE_PORTABLE": "1"
      }
    }
  }
}
```

Or set `TOLLGATE_HOME` to the **absolute path of WS-tollgate on that machine** (volume name may differ per OS — that is expected; do not hardcode another user’s home).

## Consumer auth (optional, multi-host stick)

Open mode (default): no `User/consumers.json` → any local client works.

Lock the gate (n8n / other machines)::

```bash
tollgate consumer-add n8n
tollgate consumer-add desk --admin
# → prints secret once; stored as hash only
export TOLLGATE_REQUIRE_AUTH=1   # optional if consumers file non-empty
```

Header: `X-Consumer-Key: n8n:<secret>`

`/v1/config` needs an **admin** consumer when auth is on. `/v1/health` and `/v1/auth` stay public.

## Rules

| Do | Don't |
|----|--------|
| Keep `User/` + ledger on the stick | Commit `Key.txt` / `.env` / `consumers.json` |
| Use relative scripts under `scripts/` | Absolute paths like `/Users/name/…` in docs or mcp.json |
| Prefer sibling `WS-tollgate` | Assume `~` exists or is the same host |
| Bind HTTP to `127.0.0.1` | Expose `/v1/config` on `0.0.0.0` without auth + admin consumer |

## Gnom + USB

If Gnom already uses `GNOM_WS` on the stick, Tollgate honors it. Gnom remains a **client**; install Tollgate into the same portable venv (`pip install -e ./tollgate`).
