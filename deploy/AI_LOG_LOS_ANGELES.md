# Los Angeles AI log deployment

This candidate integrates the 0.2.15 logging snapshot with the current
0.2.13-custom.1 production code line. Automatic recharge and Cockpit token
sync remain source-identical to the production baseline. Existing provider
accounts, scheduling flags, model allowlists, balances and keys stay in the
existing PostgreSQL/Redis services. Do not copy fixture or central databases
over them.

## Source and runtime

The relay is AlmaLinux 9.7 / linux/amd64 with Python 3.9. Install only verified
prebuilt source-shipper wheels. The central Python 3.12 worker environment is
separate and is not installed on the relay. Use the dedicated site profile
confirmed for this server; the Wuhan credentials must not be installed here.
Keep the private shipper configuration outside Git and outside the image
build context. The central query credential stays on the authorized local/VPN
acceptance client, not on the public relay.

The host source spool is `/var/lib/sub2api-ai-log/spool` (0700, writable by
UID1000); both slots mount it at `/app/ai-log-spool`. It must remain outside
the staged `/app/data` directories. Start with the documented 20 GiB limit,
measure real backlog and capture overhead, and alert on disk headroom,
`ai_log_capture_degraded` and the shipper status file.

Inference does not wait for Kafka or the WAN. Full queues or exhausted WAL
capacity can lose logs while inference continues. Enable capture only after
the shipper's TLS/authentication and source identity work. A capture without
its end marker or with drops must be reported as incomplete. Source shutdown
must preserve the WAL and allow its shipper to drain.

## Build, migration and release

Use Tooooa GitHub Actions for CI and a complete linux/amd64 image, including
the frontend. The Dockerfile preserves pinned base-image digests and upgrades
the Go toolchain to 1.27.2. Never build on the user's Mac. The latest user
authorization conditionally permits a resource-bounded Los Angeles build for
this rollout, but the planned route remains CI; the general production build
ban is not relaxed for future automated updates.

The only new SQL migration relative to the deployed baseline is
`242_drop_platform_check_constraints.sql`, which removes two platform CHECK
constraints and uses application-level catalog validation. Earlier SQL files
are unchanged. Verify it against an isolated database copy, and keep the old
application compatible during slot overlap; an old container is not a database
backup.

Back up PostgreSQL, application data, environment, Caddy configuration, active
state and old image/container metadata immediately before the rollout. Preserve
live changes made by other administrators. Retain the occupied inactive slot
under a dated name, then use the existing blue-green script. Candidate health
and actual smoke requests must pass before Caddy cutover. Allow existing
streams a 300-second drain window.

Verify original domain/port, GPT/GLM text and function calls, images, SSE,
WebSocket, billing, unchanged account scheduling, auto-recharge and Cockpit
sync. For capture, use a new trace and verify this source's actual events,
sequence, capture.end, drop count and central HDD replay. Central synthetic
tests and a historical green probe do not establish this relay's production
deployment.

On failure, restore Caddy routing and active state to the healthy old slot.
For capture-only rollback deploy with `AI_LOG_ENABLED=false`, preserve the
WAL and its credentials until backlog drains. Central HDD R6 still has no
independent second body copy; this application rollout does not change that.
