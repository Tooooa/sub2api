# Streaming capacity failover — 2026-10-21

> Historical custom.3 rollout. Production has moved to custom.4; see the
> [current fast-failover record](FAST_CAPACITY_FAILOVER_20261023.md) for the
> active image, capacity retry policy and rollback. The output guards below remain.

## Verified rollout state

`0.2.17-custom.3` was deployed on the Los Angeles production server. Source
`aeacc96dd752d69293c23bae160e90861254ab68` was built by the
[branch image workflow](https://github.com/Tooooa/sub2api/actions/runs/39536973864)
and merged into main through [PR 8](https://github.com/Tooooa/sub2api/pull/8).
The workflow's legacy retry-10 name does not change runtime retry limits.

- Platform: `linux/amd64`; no build ran on the Mac or production server.
- Immutable OCI manifest / Docker 29 image ID:
  `sha256:79b002ff708f2148e38fe1802146178539064d77ccad99249550f28a73aa6969`.
- OCI config digest:
  `sha256:aa71fb73512eb4711e5f440f3341bedf1f87dd722349c26630ed8d64640c2961`.
- Local tag: `sub2api:0.2.17-custom.3-aeacc96dd`; loaded from the CI artifact,
  not published as a GHCR release.
- Active container: `sub2api-green`, `127.0.0.1:18081`.
- App data: `/opt/sub2api/deploy/.blue-green/data-green-20261021031622`.
- Caddy cutover: `2026-10-21T03:17:28Z` (11:17:28 Asia/Taipei).
  Observation passed; state was written at 03:17:59Z and old blue drained
  normally by 03:18:29Z, within the 300-second drain allowance.

## Fault and correction

The server had normal CPU, memory and disk headroom. Capacity errors came from
upstream. Seven complete production WAL attempts had this sequence:

`response.created -> response.in_progress -> response.metadata -> error -> response.failed`

All seven failed responses had `output: []`. The shared first-output classifier
omitted `response.metadata`, committed the staged attempt and suppressed
failover after the subsequent overload error. Classifying it as lifecycle
metadata restores existing bounded retry and account switching in native SSE,
passthrough SSE and the first-turn HTTP-to-WebSocket bridge.

Inspection also confirmed a Messages compatibility defect. The Responses
converter emitted an empty Anthropic `message_start` for `response.created`.
That preamble and ping bytes were counted as output, including by the handler's
raw-byte comparison. This diagnosis is based on code inspection; complete WAL
sequences were not captured for the particular Messages failures.

The Messages correction stages converted preambles with the existing bounded
first-output stage, commits with real output, records heartbeat bytes separately
and uses the shared heartbeat-adjusted handler guard. Pings use generic SSE
headers. Exhaustion after pings returns an Anthropic SSE error. Client
disconnects stop retries. Real text, thinking and tool output still prohibit
replay, because retrying after visible output could duplicate content/actions.

Before actual output, capacity errors can retry and switch accounts under the
existing limits. Exhaustion of all available attempts and errors after actual
output can still reach the client. Account settings and retry limits did not
change.

## Verification

The author implemented and verified the change. Tests-first commit `90645ed2e`
failed all three metadata regressions in
[baseline CI](https://github.com/Tooooa/sub2api/actions/runs/39532443440),
reproducing the production suppression warning. Final
[full CI](https://github.com/Tooooa/sub2api/actions/runs/39536170582) and
[security scans](https://github.com/Tooooa/sub2api/actions/runs/39536170523)
passed for `aeacc96dd`, including backend unit/integration suites, frontend,
lint and operational extensions.

Regressions cover metadata-only failure including a 64 KiB preamble, native
and passthrough SSE, HTTP-to-WebSocket bridging, Messages preamble/ping followed
by another account's success without failed-attempt leakage, real
text/thinking/tool replay boundaries, client disconnects and semantic TTFT.
Unknown Responses event types retain conservative commit behavior. The ping
test synchronizes on an actual write rather than a fixed timer delay.

The downloaded OCI index, manifest/config and rootfs were checked against the
loaded image, including platform and complete image Config. The binary reports
`0.2.17-custom.3`; its default commit label is `docker`, so source provenance is
established by the workflow head SHA and verified artifact, not that label.

Before cutover, five real checks passed: GPT-6.1-sol and GPT-6-astra Responses
text SSE, a forced Sol function call, and GPT-5.6-sol Messages text and forced
tool calls. After cutover, public Sol/Astra Responses and Messages text SSE
passed. Messages streams had one `message_start`, one `message_stop` and no
error events. All temporary test keys were deleted.

Final readback: local/public health 200, zero container restarts/OOMs, account
status/scheduling/priority/concurrency equal to the pre-cutover snapshot, zero
new database migrations, preserved shared AI-log WAL mount, active shipper and
active automatic recharge timer. Evidence is retained privately with backups.

## First-stage rollout and live recovery

The Responses correction first deployed as `0.2.17-custom.2`, source
`a53e8b7ad22174ab696b5a75a3b7ad669e7477ea`, through
[CI](https://github.com/Tooooa/sub2api/actions/runs/39532988712),
[security](https://github.com/Tooooa/sub2api/actions/runs/39532988708) and
[image build](https://github.com/Tooooa/sub2api/actions/runs/39533029426).
Its blue-slot cutover occurred at `2026-10-21T02:39:40Z`; three candidate and
two public Responses checks passed.

Live request `298863da-e24e-471e-afea-614b2799226e` retried account 17 three
times after 503, switched to account 25, completed, and recorded
`Recovered upstream error 503` with status 200. Four other recovered overload
records were observed in the initial sample. This demonstrates restoration of
retry for these requests without promising success when every account fails.
The Messages follow-up above is included in the final custom.3 rollout.

Release security checks required patch updates in the existing baseline:
Go standard-library `GO-2026-6809` requires Go 1.27.3; follow-redirects 1.16.0
requires 1.16.1 for
[GHSA-q3jh-wrc6-jgq8](https://github.com/advisories/GHSA-q3jh-wrc6-jgq8) and
[GHSA-8r9p-f939-6h3c](https://github.com/advisories/GHSA-8r9p-f939-6h3c).
The release uses those patches and a pinned official Go image with amd64 support.

## Backup and rollback

Private server backup:
`/root/backups/sub2api-streaming-capacity-20261021T022628Z/` and `followup/`.
The initial PostgreSQL archive is 326,125,748 bytes and the follow-up archive
is 326,292,983 bytes; both archive indexes were validated. Backups also retain
app data, environment, Caddy, active state, container/image metadata, deploy
script, shipper configuration, account snapshots, CI/image identity, deployment
logs and smoke/recovery summaries. They contain secrets and must stay private.

Direct rollback is the stopped `sub2api-blue` on 8080, custom.2 image:
`sha256:6b64a456a71594d962a3ae52c939d8fe68e18398167def31d2fc340d4a013841`,
OCI config `sha256:1e52897923c23772bf197cb684605b3792b9e46bc12d0e6b0dbc5802e4a194cf`,
local tag `sub2api:0.2.17-custom.2-a53e8b7ad`, with app data
`/opt/sub2api/deploy/.blue-green/data-blue-20261021023926`.
Start and health-check blue, restore the previous site's Caddy route and
matching blue active state from the follow-up backup, reload Caddy, then drain
green. Caddy backup: `/opt/sub2api-https/Caddyfile.backup.20261021031728`.
No schema restoration is required for this application-only hotfix.

Earlier rollback containers remain stopped as
`sub2api-green-pre-messages-20261021` (custom.1, image `36b8af5f…`) and
`sub2api-blue-pre-metadata-20261021` (0.2.15). The initial-stage Caddy backup is
`/opt/sub2api-https/Caddyfile.backup.20261021023939`.

The root operator document's pre-edit copy is retained on the external disk at
`/Volumes/MacData/09_tmp/streaming-capacity-failover/服务器运维说明-更新前.md`.
Task-owned test keys, local transfer archives, temporary helper scripts and the
isolated worktree are removed after final verification; production backups,
rollback containers and sanitized verification records are retained.
