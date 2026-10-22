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

## Candidate verification

Candidate: `0.2.17-custom.4`, pending CI and deployment. Production remains on
verified custom.3 until the linux/amd64 branch artifact passes all checks.
Tests cover immediate capacity switching, unchanged ordinary 429 and other
transient retries, deadline/count overrides, conservative classification of
errors that merely echo overload text, and existing switch-budget exhaustion.
The prior metadata/preamble/heartbeat replay regressions remain in full CI.

## Deployment and rollback

Pending. Build in CI only; never build on the Mac or Los Angeles production.
Back up the current database, app data, environment, Caddy and active state,
then deploy the verified immutable image through the existing blue-green gate.
Use real Responses and Messages text/tool checks before cutover, verify public
health, retry logs and unchanged account settings, and retain custom.3 rollback.
