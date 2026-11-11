# 0.2.19-custom.2 refresh-token rotation release

Deployed and verified on New York on 2026-11-11. Both Caddy sites switched
at 17:41:07 Asia/Shanghai. The five-minute monitor completed and the active
pointer changed at 17:46:07. The previous blue container exited normally at
17:46:10.

## Source and security fixes

Application source `f4098e09ac87d67798771ca1aec801267e957d8c`, based on the
production `0.2.19-custom.1` source `dba6cd764` and its subsequent documentation.

- Upstream `7122efee948fc31a086202e75caff1ea2e1562c8` makes login refresh-token
  consumption atomic in Redis. Concurrent requests can issue one replacement
  token pair. Redis consumption errors return service unavailable. Stored token
  formats remain compatible.
- Upstream `b6c0ca4256b3` updates brotli to 1.2.7 and klauspost/compress to
  1.20.2 for reachable GO-2026-6888 and GO-2026-6865.
- The compiler, pinned Docker builder and CI use Go 1.27.4 for standard-library
  GO-2026-6859, which this release's security scan identified as reachable.
- Python 3.9 source-shipper CI uses Ubuntu 22.04. The Ubuntu 26.04 runner has
  no corresponding setup-python build.

The four operational extensions and deployed capacity failover/replay guards
are retained. The database migration set is identical to the previous image.
The candidate and final live readbacks verified scheduling flags, account model
mappings and full group configuration against the pre-deployment snapshot.

## CI and image

- [Full CI](https://github.com/Tooooa/sub2api/actions/runs/42994765836) passed all
  nine jobs, including Go unit/integration, lint, frontend regressions,
  deployment extensions and both source-shipper Python runtimes.
- [Security scan](https://github.com/Tooooa/sub2api/actions/runs/42994766017)
  passed backend and frontend.
- [Image CI](https://github.com/Tooooa/sub2api/actions/runs/42994810773) passed
  the upstream concurrency regressions with Go's race detector, then built and
  verified the version, source label, platform and archive checksum.

Image `sub2api:0.2.19-custom.2-f4098e09a` is `linux/amd64`. The CI image and
loaded server image both report
`sha256:1249faaeca285b9c1bd433cab5b70100aaa1149053180aa91fa8988499827263`.
The embedded version and revision match the source above. The CI archive was
fetched on New York and its checksum verified before loading. Compilation
ran in GitHub Actions.

## Runtime acceptance

The candidate's real HTTP login and refresh tests passed ordinary rotation,
rejection of consumed tokens, eight concurrent refreshes producing one success
and seven HTTP401 results, and subsequent rotation of the winning family.
Temporary refresh tokens were revoked.

| Surface | Verified result |
| --- | --- |
| GPT-6 Luna non-streaming Responses | HTTP200, JSON, non-empty `OK` |
| GPT-6.1 Terra streaming Responses | HTTP200, `response.completed` |
| Existing GLM provider | GLM-5.3 Flash Chat Completions HTTP200 |
| Images | Sunburst HTTP200, one valid 937,073-byte image |
| Billing | Four usage records, image_count=1 and image actual_cost=$0.201 |
| AI capture | Four requests, 52 contiguous events, capture.end/status200, zero capture/WAL drops |
| Public curl client | Same 19 models and a non-empty GPT-6 Luna JSON response |
| Final runtime | Green healthy, restart count0, both public health endpoints HTTP200 |

The first candidate was stopped before cutover when the operator's live WAL
observer reported missing sequences. The observer tracked read offsets by inode,
which can be reused after the shipper consumes and deletes a segment. Tracking
the unique segment filename fixed the observer. Repeating the gate with the
same application image produced all 52 events continuously. This correction
changed the deployment verification script.

The shared `/var/lib/sub2api-ai-log/spool` was retained. Final shipper metrics
showed pending_bytes=0, pending_files=0, failures=0 and delivered_events=6,138,939.
The shipper, recharge timer and restricted Japan transport relay are active.
This verification covers source WAL delivery and does not establish independent
central HDD replay of the new captures.

## Backup and rollback

Private server backup directory
`/root/backups/sub2api-v0.2.19-custom.2-20261111/` contains a verified
385,916,817-byte PostgreSQL dump, application data excluding live logs,
environment, Caddy and slot state, deployment/recharge scripts, operational
units, old container/image metadata and sanitized acceptance reports. The shared
spool was preserved in place. Counts were 58 users, 24 accounts and 127 keys.
Temporary verification keys 217–220 were deleted.

- Active green listens on `127.0.0.1:18081` with application data at
  `/opt/sub2api/deploy/.blue-green/data-green-20261111094026`.
- Retained blue `0.2.19-custom.1` is stopped on its original `8080` mapping.
- The earlier `0.2.18-custom.5` green container was renamed to
  `sub2api-green-pre-custom2-20261111` and retained.
- Caddy cutover backup is
  `/opt/sub2api-https/Caddyfile.backup.20261111094106`.

Rollback starts retained blue8080, switches both Caddy sites and the active
pointer consistently, then drains green. Keep the current shared database in
place. Rolling back the application also withdraws the security fixes in this
release.

Local operations-document backup, CI metadata and sanitized acceptance reports
are in `outputs/2026-11-11-auth-rollout/` outside the Git checkout.
