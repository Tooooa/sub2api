# Verified Los Angeles release: 0.2.15-custom.1

Deployed 2026-10-10 Asia/Shanghai (Caddy switch 2026-10-09 19:01:50 UTC,
active state 19:02:21 UTC). The implementation and deployment verification
were performed by the same agent. The release preserves the production
lineage, recharge, Cockpit synchronization and blue-green deployment, and
enables tan-jin traffic capture.

## Immutable candidate

- Source: `f4d0a152719873d81acbadd137c0184806ecce5c`.
- Reviewed logging input: MaYiding dev `9c2cfe05223208ae6ed49d83fec315f935bc78d9`.
- Tag: `v0.2.15-custom.1`; platform `linux/amd64`.
- Image: `ghcr.io/tooooa/sub2api@sha256:34f58c14a62a250239c4c5e0cb9422e0e6163858366b3e808226d06fff47ebc4`.
- Active application: `sub2api-blue`, host loopback port8080.
- Public entry: `https://sub2api.huafucius.top:8443`.
- Active app data: `/opt/sub2api/deploy/.blue-green/data-blue-20261009185736`.
- Source: `src-a3b2ed4c0008` (tan-jin), credential generation2.

Source shipper: `/etc/sub2api-ai-log/shipper.json` mode0600;
`sub2api-ai-log-shipper.service`; spool `/var/lib/sub2api-ai-log/spool` mode0700,
shared into the app at `/app/ai-log-spool`. Private credentials are absent
from Git and image contexts. Central query credentials were retained on the
local acceptance client and were never installed on the public relay.

## Verification

- [All nine CI jobs](https://github.com/Tooooa/sub2api/actions/runs/37969676352)
  passed, including Go unit/integration, frontend, lint, deployment extensions,
  logging pipeline and Python3.9/3.12 source wheel tests.
- [Security scans](https://github.com/Tooooa/sub2api/actions/runs/37969676226)
  passed; [complete image release](https://github.com/Tooooa/sub2api/actions/runs/37972132636)
  succeeded in GitHub Actions. No compilation on the user's Mac or Los Angeles
  server was performed. Image platform/revision/version were checked after pull.
- Full production database snapshot: migration242 removed exactly two CHECK
  constraints while users/accounts/groups/API-key row counts remained unchanged.
  Both retained old and new images started successfully on the isolated copy.
  The new migration runner registered the same242 file. Existing SQL files
  were unchanged.
- Pre-cutover real requests passed GPT5.6-luna/GLM5.3-flash Chat Completions,
  GLM5.3 function calls, GPT and GLM5.2 SSE, client stream cancellation and a
  Sunburst image (1,023,387 bytes with a valid image signature).
- Native WebSocket inference returned close1013/no available account on both
  old and new images. Existing account transport settings were preserved.
  The WS policy closure and client frame were captured; WS inference success
  is **not** claimed. Capturing WS paths also passed CI tests.
- Candidate trace `qingtianji-rollout-20261010-b2c50b5e7ba84280`: eight archived
  captures,117 events,3,166,618 body bytes; source/topic provenance, byte hashes,
  sequence continuity, all end markers and zero recorded drops verified.
- Seven usage rows totaled `$0.202561869`, matching temporary key142's quota
  usage within database decimal precision. Key142 was deleted after tests.
  Business account/group/user configuration compared identically before and
  after candidate checks.
- Public health and homepage returned200 after cutover; public model list
  contained18 entries and actual GPT chat passed. Public trace
  `qingtianji-public-cutover-20261010-8f37e38671f548ef` replayed as one complete
  capture with10 events/6,693 body bytes and no recorded loss; key143 deleted.
- Recharge timer remained active and its runtime resolved
  `http://127.0.0.1:8080/api/v1`, `sub2api-blue`. Cockpit LaunchAgent remained
  running on its30-second schedule with last exit0; post-cutover dry run exit0.
- Source backlog drained from a28MB burst to approximately176KB/age0, with
  zero shipper failures and no `ai_log_capture_degraded` entries at readback.

## Backup and rollback

Private backup directory:
`/root/backups/sub2api-v0.2.15-custom.1-20261009T173632Z/`.
It contains the original full database snapshot, fresh
`postgres-pre-cutover.dump`, application data, environment, Caddy, active state,
old container/image metadata, business configuration and verification summaries.
The fresh archive was294,665,359 bytes and its archive index was validated.
The initial301,624,834-byte snapshot was restored completely for migration
and old/new runtime tests. Do not publish this backup: it contains credentials.

Old green `0.2.13-custom.1` was drained with a300-second upper bound and stopped
normally. It remains the immediate rollback application. Original inactive blue
`0.2.8-custom.1` is retained as `sub2api-blue-pre-v0215-20261010`.
Caddy's cutover backup is
`/opt/sub2api-https/Caddyfile.backup.20261009190149`.
Validate old green health, then restore only the target site's route and the
matching active state. A retained container does not restore a database;
snapshot testing established this migration's compatibility, but later writes
must still be assessed before rollback. Preserve source WAL and credentials
until backlog drains when disabling capture.

Task-owned old/new test containers, private fixture network/volume (the6.4GB
database copy), private fixture configuration, failed candidate data directories
and duplicate secret staging were removed. Retained: live application/source
runtime, source spool/config, published image, old rollback containers and
private backup/evidence. Central HDD R6 still lacks an independent second body
copy; this release does not establish one.
