# 0.2.18-custom.5 release evidence

## Source and CI

- Application source: `cfe9371980f845c0d24e600997096157c6401b1f`.
- Upstream release: `v0.2.18` (`de86961b627e48db75d61fff8c05535d44a00cbe`).
- Reviewed `MaYiding/sub2api` `origin/dev` relay updates after the shared
  ancestor: AI-log WAL/session fixes, response-writer restoration, idempotent
  repeated blue-green rollout, retention/sessionizer tooling and their tests.
- Full CI: [run 40113106482](https://github.com/Tooooa/sub2api/actions/runs/40113106482).
- `linux/amd64` image archive: [run 40113128263](https://github.com/Tooooa/sub2api/actions/runs/40113128263).
- No source or image build ran on the Mac or the Los Angeles production server.

## Image

- Server tag: `sub2api:0.2.18-custom.5-cfe937198`.
- Image ID: `sha256:1cbd71402cc7e691f8634b3ddce2bc9f2237974ee3cca73dc5edb68b2e6d8e7e`.
- Platform: `linux/amd64`.
- Embedded version: `0.2.18-custom.5`.
- The image was transferred from the CI archive and tagged after `docker load`;
  the server did not build it.

## Backup and deployment

Backup directory on the production server:
`/root/backups/sub2api-v0.2.18-custom.5-20261024T170137Z/`

It contains the PostgreSQL custom-format dump, the active app-data archive
(excluding the continuously changing local runtime-log directory), active
blue-green state, Caddyfile, deployment environment, container/image inspect
records, the previous deployment script, the transferred image archive, and a
manifest of the shared AI-log spool. The spool itself was not moved or cleared.

Deployment facts:

- Active slot: `sub2api-green`, port `18081`.
- Previous active slot: `sub2api-blue`, stopped and retained with the
  `0.2.17-custom.4` image for rollback.
- Previous inactive green container was retained as
  `sub2api-green-pre-v0218-20261024`.
- Caddy backup: `/opt/sub2api-https/Caddyfile.backup.20261024170457`.
- Caddy switched only after the candidate health gate; the old container was
  drained for 60 seconds before it was stopped.

## Verification

- Candidate and public application health returned `{"status":"ok"}` at
  `http://127.0.0.1:18081/health` and
  `https://sub2api.huafucius.top:8443/health`.
- Caddy configuration validation passed.
- Migration `246_enable_gemini_image_generation_groups.sql` is recorded in
  `schema_migrations`; the current database has no Gemini/Antigravity groups,
  so its data update was a no-op.
- `AI_LOG_ENABLED=true` remained enabled; the new container mounts the same
  `/var/lib/sub2api-ai-log/spool` host directory. At verification the shipper
  reported `failures=0`, `pending_files=221`, and `pending_bytes=292729761`.
- The shared spool was approximately 256MB after cutover and was not deleted,
  reinstalled, or moved.
