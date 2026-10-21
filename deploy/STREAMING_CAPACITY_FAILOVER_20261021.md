# Responses metadata and capacity failover

## Fault and correction

On2026-10-21, live production WAL showed seven complete overload attempts
with this sequence and no model output:

`response.created -> response.in_progress -> response.metadata -> error -> response.failed`

All seven failed responses had `output: []`. The shared first-output classifier
recognized created/in-progress/keepalive as metadata but treated
`response.metadata` as semantic output. Native SSE committed its staged attempt;
the following capacity error then logged
`gateway.failover_suppressed_after_semantic_output` instead of returning an
`UpstreamFailoverError`. This also affected passthrough SSE and the first-turn
HTTP-to-WebSocket bridge because they share the classifier.

The correction classifies `response.metadata` as lifecycle metadata. It remains
buffered with the attempt until real output or a terminal event. Pre-output
capacity failures use the existing bounded same-account/account-switch retry
policy. A successful retry exposes only its own events. Real text and function
arguments still commit the stream and prohibit replay; exhausted retries and
failures after actual output can still reach the client.

## Verification

The author implements and verifies this change. Regression tests reproduce the
observed sequence, including a64KiB preamble, for native/passthrough SSE and the
first-turn HTTP-to-WebSocket bridge. They verify that the failed attempt writes
no client bytes, another account can finish without leaked failure events, and
actual text/tool output still prevents replay. Metadata also does not start
semantic TTFT. Unknown event types retain conservative commit behavior.

The tests-first commit90645ed2e failed all three affected-path regressions in
[baseline CI](https://github.com/Tooooa/sub2api/actions/runs/39532443440),
reproducing the production suppression warning. The correction4a2805b0c and
patch-version commita53e8b7ad passed all nine jobs in
[branch CI](https://github.com/Tooooa/sub2api/actions/runs/39532988712), including
full backend unit/integration suites, frontend, lint and operational extensions.
[Security scans](https://github.com/Tooooa/sub2api/actions/runs/39532988708)
also passed. [PR8](https://github.com/Tooooa/sub2api/pull/8) contains the change.

## Release checks

The initial security scan found newly reported patch requirements in the
existing baseline: Go standard-library `GO-2026-6809` requires Go1.27.3, and
`follow-redirects`1.16.0 requires1.16.1 for
[GHSA-q3jh-wrc6-jgq8](https://github.com/advisories/GHSA-q3jh-wrc6-jgq8) and
[GHSA-8r9p-f939-6h3c](https://github.com/advisories/GHSA-8r9p-f939-6h3c).
The release uses those patch versions; the official Go image index was checked
for linux/amd64 before pinning its digest.

## Image and deployment

[Branch image build](https://github.com/Tooooa/sub2api/actions/runs/39533029426)
compiled sourcea53e8b7ad22174ab696b5a75a3b7ad669e7477ea on GitHub Actions.
The workflow's legacy retry-10 name does not change runtime retry limits.
Artifact12316810046 contains the full prebuilt linux/amd64 image. Its OCI
manifest, configuration and rootfs were checked against the loaded image;
the binary reports0.2.17-custom.2. No build ran on the Mac or production.

- Immutable loaded manifest/image ID:
  `sha256:6b64a456a71594d962a3ae52c939d8fe68e18398167def31d2fc340d4a013841`.
- OCI config digest:
  `sha256:1e52897923c23772bf197cb684605b3792b9e46bc12d0e6b0dbc5802e4a194cf`.
- Local production tag:`sub2api:0.2.17-custom.2-a53e8b7ad`. This hotfix image
  was loaded from the CI artifact; it was not published as a GHCR release.
- Candidate:`sub2api-blue`,127.0.0.1:8080, data directory
  `/opt/sub2api/deploy/.blue-green/data-blue-20261021023926`.
- Caddy cutover:2026-10-21T02:39:40Z (10:39:40 Asia/Taipei). The30-second
  observation passed; old green stopped normally at02:40:37Z with a maximum
  300-second drain allowance.

Before cutover, real GPT-6.1-sol and GPT-6-astra Responses SSE requests and a
forced GPT-6.1-sol function call completed without error events. Public Sol
and Astra SSE then passed. Both temporary keys were deleted. Local/public
health returned200, the new container had zero restarts/OOMs, and account
status/scheduling/priority/concurrency matched the backup exactly. There were
no new database migrations. The shared AI-log WAL mount, shipper and automatic
recharge timer remained active.

Live traffic confirmed the retry branch was restored: request
`298863da-e24e-471e-afea-614b2799226e` retried account17 three times after503,
switched accounts, and recorded `Recovered upstream error 503` with status200.
Four other recovered overload records were observed in the first post-cutover
sample. This demonstrates recovery for these requests; all-account exhaustion
and failures after actual output remain possible.

## Backup and rollback

Private server backup:
`/root/backups/sub2api-streaming-capacity-20261021T022628Z/`.
It contains a326,125,748-byte PostgreSQL archive (archive index validated),
app data, environment, Caddyfile, active state, container/image metadata,
deployment script, shipper configuration, business snapshots, CI/image identity
and smoke/recovery summaries. Configuration and database backups contain
secrets and must not be published.

Old0.2.17-custom.1 remains stopped as`sub2api-green` on18081, image ending
`36b8af5f75d6f2138af11fe2fa3e7c0633ebcb4d31c082fd7eeed2634341c648`.
To roll back, start/health-check green, restore the previous site's Caddy route
and matching active state, reload Caddy, then drain blue. No schema restoration
is required for this application-only hotfix. Caddy backup:
`/opt/sub2api-https/Caddyfile.backup.20261021023939`.
The previous stopped blue0.2.15 image/container was retained under
`sub2api-blue-pre-metadata-20261021` before reusing the blue slot.

The root operator document was backed up to the external-disk task directory
before updating. Task-owned test credentials and transfer files are cleaned
after verification; production backups and rollback containers are retained.

## Messages compatibility follow-up

Post-cutover checks exposed the same boundary problem in `/v1/messages`: the
Responses converter emitted an empty Anthropic `message_start` immediately
for `response.created`. That preamble and keepalive pings set the local output
flag before any content. The Messages handler also compared raw byte counts,
so a ping alone prevented account retry.

The follow-up stages converted preambles with the existing bounded first-output
stage, commits them with real output, records ping bytes as transport-only,
and uses the handler's shared heartbeat-adjusted replay guard. Pings write
only generic SSE headers. Exhaustion after pings retains an Anthropic SSE
error; text, thinking and tool output still prohibit replay. Regression tests
cover preamble-only and ping-only failure followed by another account's
success, plus the no-replay boundary for actual content.

Version0.2.17-custom.3 is under verification; production remains on the
verified0.2.17-custom.2 image above until the follow-up checks pass.
