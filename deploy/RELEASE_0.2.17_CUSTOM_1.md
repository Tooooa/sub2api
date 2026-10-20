# Verified Los Angeles release: 0.2.17-custom.1

Deployed 2026-10-20 Asia/Shanghai. Caddy switched at 05:06:48 UTC; the
30-second observation passed and the old blue container stopped normally at
05:07:18 UTC, with a 300-second maximum drain allowance.

## Source and image

- Original upstream: Wei-Shaw/sub2api `v0.2.17`,
  `060d0160417782cd962a0c7f460f6cd4565d4916`.
- Production source: `ae731617f027d3e66ef9ee976d649b181ca1512a`,
  tag `v0.2.17-custom.1`, merged through [PR 3](https://github.com/Tooooa/sub2api/pull/3).
- Image: `ghcr.io/tooooa/sub2api@sha256:36b8af5f75d6f2138af11fe2fa3e7c0633ebcb4d31c082fd7eeed2634341c648`.
- Platform: `linux/amd64`; version, revision and architecture checked after pull.
- Active: `sub2api-green`, loopback port18081; public
  `https://sub2api.huafucius.top:8443`.
- App data: `/opt/sub2api/deploy/.blue-green/data-green-20261020050523`.

The merge preserves blue-green deployment, automatic recharge, Cockpit OAuth
synchronization and AI traffic capture/central archival. Historical downstream
fixes remain; this is not a claim that only four source differences exist.
The VERSION conflict was resolved to0.2.17-custom.1. The ordinary upstream retry
limit remains5. Existing local dev commits and separate Cockpit runtime changes
were not replaced.

## Verification

- [Nine CI jobs](https://github.com/Tooooa/sub2api/actions/runs/39370972898) and
  [security scans](https://github.com/Tooooa/sub2api/actions/runs/39370972906)
  passed on037a7dc9068d21b3c70021dacdeeccb83fdccda0. Its tree exactly matches
  the merged release source. Tests cover backend unit/integration, frontend,
  lint, release helpers, deployment extensions and log runtime Python3.9/3.12.
- [Release CI](https://github.com/Tooooa/sub2api/actions/runs/39372106468)
  built the complete image. No builds ran on the Mac or production server.
  The temporary SIMPLE_RELEASE repository variable was removed afterward.
- A full production database backup was restored on an isolated internal
  Docker network, using existing prebuilt PostgreSQL/Redis images. Four additive
  migrations registered:242_group_i18n,243_gemini_cached_contents,
  244_gemini_cached_contents_channel_usage,245_gemini_cached_contents_mutation_lease.
  Migration count292→296; users56, accounts31, groups2, keys159 and usage
  rows1,809,216 stayed unchanged. New columns were checked. Both the new image
  and old0.2.15-custom.1 image started healthy against the migrated copy.
- Candidate real requests passed GPT5.6-luna/GPT6-luna Chat Completions,
  GPT6.1-sol/GPT6-sol SSE, a forced GPT function call and Sunburst image
  generation (1,012,241 bytes, valid image signature). Public health, homepage,
  model list and two Chat calls passed after cutover. Green had zero restarts.
- Live model catalog14 entries matched the old image exactly. The allowlist
  still has19 entries; GLM providers27/28 were already unschedulable before
  this upgrade. Their configuration was preserved and live GLM tests skipped.
  The first gate used the historical19-model expectation and correctly stopped
  before cutover; old-image readback and unchanged business snapshots established
  the correct baseline. No provider was enabled to make a test pass.
- All account scheduling, priority/concurrency, group and account-group
  configuration compared identically before/after. Temporary test keys were
  deleted. Six candidate usage rows cost$0.2012101000; two public rows
  cost$0.0000135000, matching their key quota deductions.
- Automatic recharge remained active, resolved green/18081 and authenticated
  successfully, reading56 users. Existing stable Cockpit LaunchAgent stayed
  unchanged; post-cutover dry-run exited0 (local20, server OAuth9), and the
  scheduled task's last exit was0.

## Logging evidence and limits

Source `src-a3b2ed4c0008` (tan-jin), credentials and shared
`/var/lib/sub2api-ai-log/spool` remained unchanged. The installed deploy script
was older than the tested repository version; it was backed up and updated
before deployment to preserve the shared WAL mount and pre-cutover gate.

Candidate trace `v0217-candidate-edd6be8f93e24c28afb981cd55184bd6` produced
6 captures/112 events; public trace
`v0217-public-8c8ea082a32b4f9ea4ffcd58a7ac1e71` produced2 captures/20 events.
All sequences, start/end markers and source IDs were checked; recorded drops0,
and no capture-degraded log entries appeared.

The existing background shipper was active and advancing through a backlog
already present before deployment. Its last completed-loop report showed about
2.02GB pending, oldest age2930 seconds and0 failures; that report was stale
while a long batch ran. These are not instantaneous queue metrics.
Only the complete synthetic test captures were replayed with the installed
shipper and original stable event IDs, receiving Kafka acknowledgements for all
132 events. The production WAL was untouched; downstream deduplication handles
later copies. This confirms Kafka delivery, not background backlog drainage.
Central HDD replay subsequently passed using the read-only operator credential
in the user-provided handoff archive, from the Mac only. The web administrator
password is not included in that archive and was not needed for this check.
Only source `src-a3b2ed4c0008` and the two rollout traces above were queried.
All8 captures/132 events were complete: candidate body bytes2,756,975 and
public body bytes16,286. The verifier checked trusted source/topic provenance,
each body's SHA256 and length, sequence continuity, end markers and zero drops.
Capture IDs, event counts and body-byte totals exactly matched the local
pre-cutover/public evidence. Only non-secret summaries were added to rollout
evidence; temporary query credentials were removed after verification and never sent to the
relay. This verifies these traces' central archive, not backlog drainage.
No central archival service changed. The historical independent-second-copy
limitation remains.

The subsequent [backlog repair and complete snapshot audit](AI_LOG_BACKLOG_20261020.md)
resolved the source throughput/reporting issue and verified drainage plus new
background-delivered captures. It also disclosed pre-existing capture drops
in the old blue container; the release tests above do not establish global
historical zero loss.

## Backup, rollback and cleanup

Private server backup:
`/root/backups/sub2api-v0.2.17-custom.1-20261020T042531Z/`.
Initial PostgreSQL archive320,504,913 bytes was completely restored for tests.
Fresh pre-cutover archive320,548,688 bytes completed05:03:40 UTC; archive
indexes were validated. Backups include app data, env, Caddy, active state,
old container/image metadata, deployment script, shipper configuration/unit,
recharge script/units, private business snapshots and verification evidence.
These contain secrets and must not be published.

Old `sub2api-blue`0.2.15-custom.1 remains stopped for immediate application
rollback. Its immutable image ends `34f58c14a62a250239c4c5e0cb9422e0e6163858366b3e808226d06fff47ebc4`.
The earlier green0.2.13-custom.1 is retained as
`sub2api-green-pre-v0217-20261020`.
Caddy backup: `/opt/sub2api-https/Caddyfile.backup.20261020050647`.
Start and health-check blue, restore only this site's route and matching active
state, then drain green. The old image passed compatibility testing after these
migrations; a retained container does not restore a database or later writes.

Task-owned fixture containers, internal network, PostgreSQL volume, secret
fixture environment, failed candidate data and temporary keys were removed.
Keep the live source spool/config, current and rollback containers/images,
release tag and private backup. The external-disk rollout evidence directory
contains non-secret summaries; private payload/configuration stays on the server.
