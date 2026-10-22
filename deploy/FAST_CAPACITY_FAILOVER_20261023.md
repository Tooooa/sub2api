# Fast capacity failover — 2026-10-23

## Decision and boundary

Production latency inspection found 49 recovered requests in the last hour.
Estimated first output was 10.6 seconds at the median without retry and
25.5 seconds with retry; 95th percentiles were 32.2 and 74.0 seconds. These
are observational samples, not controlled proof of a fixed latency saving.
The previous policy allowed three retries on the same account for recognized
capacity rejection, adding three upstream round trips and 0.5 + 1 + 2 seconds
of backoff before switching accounts.

The shared handler retry policy now declines same-account retry for typed
OpenAI capacity errors (`server_is_overloaded`, `slow_down` and recognized
overload messages). Responses, Messages, Chat Completions and other consumers
of this guard immediately use their existing bounded account-switch loop.
It preserves request-scoped attribution, so capacity does not ban an account.
Ordinary OAuth 429 deadlines, authentication recovery and unrelated transient
retry rules remain unchanged. Real semantic output and client disconnects
continue to prevent replay. No model, reasoning effort or account settings change.

This removes repeated attempts on each overloaded account; it cannot shorten
normal model reasoning. A single-account pool or all-account capacity outage
can exhaust sooner because there is no same-account capacity fallback. Existing
maximum switch budgets and exhaustion responses remain authoritative.

## Verification

The author implemented and verified candidate `0.2.17-custom.4`, source
`183d82934b8d5ee6792d056fb8afb9a6a05a1a9f`. All nine jobs in
[full CI](https://github.com/Tooooa/sub2api/actions/runs/39815666928), the
[PR CI](https://github.com/Tooooa/sub2api/actions/runs/39816132801), and
[security scans](https://github.com/Tooooa/sub2api/actions/runs/39815666778)
passed. [PR 9](https://github.com/Tooooa/sub2api/pull/9) merged the code to main.

Regression tests cover immediate capacity switching, unchanged ordinary 429
and other transient retries, deadline/count overrides, conservative
classification of errors that merely echo overload text, and existing
switch-budget exhaustion. Prior metadata/preamble/heartbeat replay regressions
remain in full CI. No database migrations or account settings changed.

## Verified image and deployment

[Branch image build](https://github.com/Tooooa/sub2api/actions/runs/39815669133) compiled the exact source above.
The legacy retry-10 workflow name does not change runtime retry limits.
Platform, OCI index/config, complete Config and rootfs layers were verified
against the loaded image. Its binary reports custom.4 (default build commit
label `docker`; workflow head SHA supplies source provenance). No build ran
on the Mac or production server.

- Immutable manifest / Docker image ID: `sha256:f650ea4e867a6242d8449040550b6e33f8bd3641e5d04e7fe46c51ec2eac369a`.
- OCI config digest: `sha256:7f5449ab7096a369b6e048038af217c755851b25f3d57bc0161c7f1c88435a21`.
- Local tag: `sub2api:0.2.17-custom.4-183d82934`; CI artifact loaded directly, not a GHCR release.
- Active: `sub2api-blue`, `127.0.0.1:8080`.
- App data: `/opt/sub2api/deploy/.blue-green/data-blue-20261022165023`.
- Caddy cutover: `2026-10-22T16:51:51Z` (2026-10-23 00:51:51 Asia/Taipei).
  State written at 16:52:22Z; old green drained and stopped at 16:52:53Z
  within the 300-second allowance.

Before cutover, five real checks passed: Sol/Astra Responses text SSE, forced
Sol function call, Messages text SSE and forced tool call. Public Sol/Astra
Responses and Messages text SSE then passed. Temporary keys were deleted.
Local/public health returned 200; container restart count is zero with no OOM.
Account status/scheduling/priority/concurrency matched the immediate pre-cutover
snapshot. No new migrations appeared. Shared AI-log WAL, shipper and automatic
recharge timer were preserved and active.

## Observed post-cutover behavior

From 2026-10-22T16:51:51Z to 2026-10-22T16:54:09.634879+00:00, new blue logged
30 inference request completions and 12 switch events.
8 requests had recovered upstream errors and positive output usage;
there were 0 same-account retry events, 0 final upstream failure records
and 0 semantic-output suppression warnings in this short window.
Some switch events can belong to requests still in flight at the window end.

Completed examples:

| Request | Endpoint | Account sequence | First recorded error → switch decision | Output tokens |
|---|---|---|---|---|
| `6851c662-6abc-4bd2-b7e8-268e8825328f` | `/responses` | 25 → 21 | 3.0 ms | 336 |
| `9295934d-6084-49f5-a14a-cabc3aa439c4` | `/responses` | 17 → 25 | 3.0 ms | 202 |
| `dacd4462-dc4c-4ccc-83ae-a3efc54c49f5` | `/responses` | 17 → 23 → 25 → 21 | 2.0 ms | 257 |
| `774db3de-356b-470e-a47c-aab7cf53f67f` | `/responses` | 30 → 17 | 31.0 ms | 243 |
| `011f9a54-b44b-412e-8d36-bb3d0ca41fa8` | `/responses` | 23 → 30 → 17 | 2.0 ms | 85 |
| `be95f5e7-e2f5-4168-8c8e-a25699510be2` | `/v1/messages` | 25 → 21 | 2.0 ms | 6 |
| `ab7e6894-07f7-432b-9890-ff25b93d6e86` | `/v1/responses` | 17 → 25 → 23 | 3.0 ms | 6 |
| `9fc8d3b4-5643-467e-ad75-e00e83f44531` | `/responses` | 23 → 30 | 2.0 ms | 204 |

The completed examples switched 2–31 ms after the first recorded upstream
error, with no same-account retry. This measures the gateway decision, not the
next account's upstream response or end-user network time. First-output
estimates still varied from 3.5 to 58.5 seconds across these inputs. The short,
non-controlled sample establishes the new retry path, not a fixed percentage
improvement in overall TTFT. Normal model inference remains outside this fix.

## Backup and rollback

Private backup: `/root/backups/sub2api-fast-capacity-20261022T163858Z/`.
It includes a 335,501,857-byte PostgreSQL archive (archive index
validated, not a full restore drill), app data, environment, Caddy, active state,
container/image metadata, deployer, account snapshots, CI/image identities,
smoke results, deployment log and post-release summary. It contains secrets
and must stay private.

Direct rollback is stopped `sub2api-green`, custom.3,
`sha256:79b002ff708f2148e38fe1802146178539064d77ccad99249550f28a73aa6969`,
using `/opt/sub2api/deploy/.blue-green/data-green-20261021031622` on 18081.
Start and health-check green, restore the previous site's Caddy route and the
matching active state from backup, reload Caddy, then drain blue. Caddy backup:
`/opt/sub2api-https/Caddyfile.backup.20261022165150`. No schema rollback is needed.
The prior stopped custom.2 container is retained as
`sub2api-blue-pre-fast-capacity-20261023`.

The operator document's pre-edit copy is retained on the external disk at
`/Volumes/MacData/09_tmp/fast-capacity-20261023/服务器运维说明-更新前.md`.
Task-owned transfer archives, temporary local helper scripts, worktree and
branch are removed after verification; backup and rollback artifacts remain.
