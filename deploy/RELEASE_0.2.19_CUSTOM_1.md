# 0.2.19-custom.1 candidate

Status: user-approved candidate; CI, migration compatibility and New York
runtime acceptance are pending. This record must not be read as evidence
that production has already changed.

## Source

Base: Tooooa/sub2api main b2a5ae676, including the November 2 production model
audit. Upstream release v0.2.19 is dece26153621959ccd7635814f4b2d08304e681a.
Selected upstream patches:

- 6b2fdfcac: preserve non-streaming OAuth Responses as JSON.
- 9b5407449: retain incomplete/cancelled terminal response JSON and usage.
- 4db8402b5: recognize OAuth SSE without Content-Type.
- d851a3847: vue-i18n 11.4.16 and decode-uri-component security fixes; Node24 CI.

Management MCP and migration 249 from newer main are outside this candidate.
The four operational extensions, capacity account switching and stream output
guards remain in the production lineage. Static merge conflicts were limited
to VERSION, documentation ignore exceptions and dependency override unions.

## Required release gates

- Full Go unit/integration, lint, frontend critical and release regression
  suites, shell/deployment extensions, logging pipeline, source Python runtimes
  and dependency security checks in CI.
- CI-produced linux/amd64 archive with embedded source commit, revision label,
  image identity and archive checksum. No local or production builds.
- Fresh New York PostgreSQL, app-data, environment, Caddy, deployment and
  independent automation backups; preserve continuously changing shared spool.
- Isolated database restore: apply additive migrations 247 and 248 with new
  image, then prove old image startup. New billing switch defaults false.
- Candidate blue:8080 health and real OAuth JSON/SSE, image and configured
  provider checks before Caddy cutover. Preserve all manual scheduling flags,
  group configuration, source logging identity and shared spool mount.
- Public health and billing/log verification after cutover; retain green:18081
  with old 0.2.18-custom.5 image for direct application rollback.

The source main branch documents the current 18-model group allowlist and a
rolled-back Terra listing attempt. This release does not pre-authorize an
unrelated model/group configuration replacement.
