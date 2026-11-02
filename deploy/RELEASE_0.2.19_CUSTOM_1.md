# 0.2.19-custom.1 New York release evidence

Deployed and verified on 2026-11-02 (Asia/Shanghai). Caddy switched both public
sites at 11:10:03; the five-minute monitor completed, the active pointer changed
at 11:15:04, and the old green container stopped normally at 11:15:07.

## Source and CI

Application source: `dba6cd76484c3fabd73a30190546b8ad60ff63e7`, based on
Tooooa main `b2a5ae676` and upstream v0.2.19
`dece26153621959ccd7635814f4b2d08304e681a`.
Selected upstream patches:

- `6b2fdfcac`: non-streaming OAuth Responses return JSON with the right header.
- `9b5407449`: incomplete/cancelled terminal responses retain JSON and usage.
- `4db8402b5`: recognize OAuth SSE without Content-Type.
- `d851a3847`: vue-i18n 11.4.16 and decode-uri-component security fixes; Node24 CI.

The merge also fixes a duplicate declaration in `ClearAccountError` and pins
follow-redirects 1.16.2 for GHSA-mrwp-f3q8-3g9p discovered by release CI.
Management MCP and migration 249 from newer upstream main are excluded.

- [Full CI](https://github.com/Tooooa/sub2api/actions/runs/41379742614): all nine
  jobs passed, including Go unit/integration, lint, frontend critical and release
  regressions, deployment extensions and AI-log/source-runtime checks.
- [Security scan](https://github.com/Tooooa/sub2api/actions/runs/41379742673):
  backend and frontend passed.
- [Image archive CI](https://github.com/Tooooa/sub2api/actions/runs/41379744928):
  build, embedded version/commit, platform, revision label and checksum passed.
- Independent source/migration and multi-site deployment review found no
  blocking issue. Both production sites use separate Caddy blocks.

No application or image build ran on the user's Mac or either production host.

## Image identity

- Server tag: `sub2api:0.2.19-custom.1-dba6cd764`.
- Platform: `linux/amd64`.
- OCI manifest / New York Docker29 image ID:
  `sha256:b2674e3e736887bfd28a0218ac1471fc95149bea80a2663bcecf9b2b9ee2130c`.
- Config digest / CI legacy Docker image ID:
  `sha256:883d0f68f46ddfd4ae20f57ccc899a63c53f1a7cdbe3180622e2d53dde733156`.
- Archive: 46,282,752 bytes; CI checksum verified after download and transfer.

Docker29's containerd store reports the OCI manifest as image ID, whereas the
CI legacy store reports its config digest. The archive index, platform manifest,
config digest, embedded commit and revision label were cross-checked; these are
two identities of the same verified image, not evidence of a different build.

## Backup and migration compatibility

Private New York backup directory:
`/root/backups/sub2api-v0.2.19-custom.1-20261102/`.

It retains PostgreSQL dumps (initial 376,840,210 bytes; fresh pre-cutover
376,875,042 bytes, both archive indexes verified), app-data archive excluding
live runtime logs, environment, old container/image metadata, active pointer,
Caddy files, deployment and recharge scripts, systemd units and log metrics.
The shared `/var/lib/sub2api-ai-log/spool` was preserved in place rather than
copied, cleared or moved. Local operations-document backup and sanitized
acceptance evidence are in `outputs/2026-11-02-v0219-rollout/` outside the Git
checkout. Secrets remain in private server files, not this repository.

A complete database restore ran in an internal Docker network. New image
startup applied additive migrations 247 (scoped admin keys) and 248 (group image
count billing, boolean/non-null/default false). The old `cfe937198` image then
started healthy against that migrated database. Counts remained 57 users,
22 undeleted accounts and 126 undeleted keys. Temporary database/application
containers, network and volume were removed after evidence was saved.

## Blue-green rollout and acceptance

- Active: `sub2api-blue`, `127.0.0.1:8080`, New York `23.252.107.103`.
- Retained rollback: `sub2api-green`, stopped, old `0.2.18-custom.5` image.
- Candidate data: `/opt/sub2api/deploy/.blue-green/data-blue-20261102030917`.
- Caddy cutover backup:
  `/opt/sub2api-https/Caddyfile.backup.20261102031002`.

Before candidate startup, both Caddy sites were fixed to current green only:
the previous dormant-blue-first ordering could otherwise route live traffic
before the candidate gate. The source-managed deployment script now accepts
`SUB2API_CADDY_SITE_HOSTS`; both explicit sites are rendered, validated and
reloaded atomically. Missing/duplicate matches fail before replacing Caddy.

Candidate real-request gate passed:

| Surface | Evidence |
|---|---|
| OAuth JSON | GPT-6 Luna, HTTP200, application/json, non-empty response |
| OAuth stream | GPT-6.1 Sol, 10 SSE events, response.completed |
| Existing GLM provider | glm-5.3-flash Chat Completions HTTP200 |
| Images | Sunburst HTTP200, one valid image, 989,623 bytes |
| Billing | Four usage records; image_count=1, image actual_cost=$0.201 |
| Capture | Four real captures, 57 contiguous events, capture.end/status200, zero request or WAL drops |
| State | All scheduling booleans and group configuration unchanged; shared spool/source settings inherited |
| Models | Original 18-model public list unchanged; no Terra allowlist addition |

After cutover, local and both public health endpoints returned ok. A real curl
client through `https://api.aura-home.online` returned the same 18 models and a
non-empty GPT-6 Luna JSON response. A Python urllib probe hit the pre-existing
Cloudflare 1010 browser-signature rule; it never reached the gateway. No Cloudflare
rule was relaxed. Temporary acceptance keys 206-209 were deleted.

Ego-browser verified the new version badge and translated administrator security
settings, including scoped-key controls, without saving settings. Temporary UI
credentials were removed from task files and the test browser origin; its
TaskSpace and SSH forwarding channel were closed.

## Existing log transport outage repaired

Before this release, the source spool was full: 21,474,836,426 bytes / 37,793
files, delivered_events=2,593,495, with Kafka CONNECT timeouts. All broker names
and the control host resolved to Wuhan `113.57.11.196`; direct New York TCP443
timed out. The Japan host `20.63.215.95` verified TLS1.3 to all three brokers.

A narrow deployment-only relay now restores that path:

- New York `sub2api-ai-log-relay.service`: SSH local listener `127.0.0.1:19443`
  forwards through Japan to `113.57.11.196:443`.
- One NAT OUTPUT rule matches only UID1000 and that destination TCP443.
  TLS hostname/certificate checks, SASL, source identity, credentials and spool
  content remain unchanged. No new public listening port was opened.
- The dedicated SSH key is restricted on Japan to source `23.252.107.103` and
  `permitopen=113.57.11.196:443`. Its private key stays on New York.
- Relay startup installs the exact rule; service stop removes it. To roll back
  this network repair, disable/stop this unit, then remove only its dedicated
  public-key entry on Japan, preserving unrelated authorized keys.
- Original NAT snapshot is `iptables-nat.before.txt` in the release backup;
  Japan authorized-keys backup is
  `/home/azureuser/.ssh/authorized_keys.pre-sub2api-ailog-20261102`.

Shipper was not reinstalled or restarted. By 11:15:52, delivered_events rose to
2,607,485 and backlog fell to 20,921,464,902 bytes / 36,031 files. The current
long delivery pass still reports two earlier failures; it must not be described
as failures=0. Recharge timer, log shipper and log relay remain active; the local
Cockpit task remains loaded with exit0 and the New York destination.

Historical backlog recovery is still in progress and depends on Japan until the
direct network path recovers. New-request WAL evidence is complete; central HDD
replay of these newest captures was not claimed during the backlog. Saturation
before this repair may already have lost events, which this release cannot
recreate. No full historical recovery or new independent archive copy is claimed.

## Application rollback

Start retained green, change both selected Caddy sites back to green18081 first,
validate/reload and update the active pointer consistently. Drain blue before
stopping it. Additive migrations can stay in place, as proven by the restored
copy; do not delete migration records or restore an old database over newer
production writes merely to roll back the application image.
