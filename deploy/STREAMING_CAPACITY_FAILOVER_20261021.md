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

CI results, image identity and rollout evidence will be recorded after checks
complete. Builds are restricted to CI or an independent build host.

## Release checks

The initial security scan found newly reported patch requirements in the
existing baseline: Go standard-library `GO-2026-6809` requires Go1.27.3, and
`follow-redirects`1.16.0 requires1.16.1 for
[GHSA-q3jh-wrc6-jgq8](https://github.com/advisories/GHSA-q3jh-wrc6-jgq8) and
[GHSA-8r9p-f939-6h3c](https://github.com/advisories/GHSA-8r9p-f939-6h3c).
The release uses those patch versions; the official Go image index was checked
for linux/amd64 before pinning its digest.

Production remains on the previous image until all release gates pass.
Backup and rollback details will be recorded at deployment.
