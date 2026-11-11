# 0.2.19-custom.2 refresh-token rotation release

Candidate prepared on 2026-11-11. The user authorized the New York blue-green
deployment after the upstream review. The running source before this release
is `dba6cd764`, `0.2.19-custom.1`, blue on loopback port 8080.

## Change

Upstream commit `7122efee948fc31a086202e75caff1ea2e1562c8` makes login
refresh-token consumption atomic in Redis. Concurrent requests presenting the
same refresh token can issue only one replacement token pair. Redis consumption
errors return service unavailable. Existing stored refresh tokens retain their
format and work through the updated rotation path.

Upstream dependency patch `b6c0ca4256b3` updates brotli to 1.2.7 and
klauspost/compress to 1.20.2 for GO-2026-6888 and GO-2026-6865, which the
existing branch security scan identified as reachable.

The candidate retains the deployed four operational extensions and capacity
failover/replay guards. It adds no database migration. The release workflow
runs the upstream concurrency regressions with Go's race detector before
building and verifying the linux/amd64 image. Full CI and security scans must
also pass.

## Deployment verification

Pending CI image and New York rollout. Back up the database, active application
data, Caddy, environment, deployment pointer, scripts and operational units.
Preserve the shared AI-log spool in place. Verify candidate login and token
rotation, OAuth JSON and SSE, Terra, images, model list, billing and log capture
before switching both Caddy sites to green18081. Monitor and drain blue8080,
retaining that image/container for rollback.

Application rollback starts blue8080 and restores both Caddy routes and the
active pointer consistently. It also withdraws the refresh-token rotation fix.
