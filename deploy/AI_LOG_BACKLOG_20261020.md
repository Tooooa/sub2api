# Source WAL backlog repair, 2026-10-20

Scope: tan-jin source `src-a3b2ed4c0008` on the Los Angeles relay. The
application remains `0.2.17-custom.1`; this repair changes the standalone
Python shipper only. No application/image builds or application restart ran
on the Mac or relay.

## Cause and historical loss

The gateway rotates WAL every second or4MiB. The old shipper waited for
Kafka acknowledgement after every file. Observed broker RTT was181–187ms;
serial barriers limited small-file throughput and partition concurrency on
the variable WAN link. The old status calculation added each file's size
before sending/deleting it and only published after the whole scan, so its
multi-GB backlog figures could include already delivered files for many
minutes. Three simultaneous historical connection timeouts/closures recovered;
there is no evidence of a persistent authentication failure.

At05:26 UTC, actual spool occupancy was306,565,368 bytes/526 files with oldest
age1147s, while stale status reported2,356,153,775 bytes/3808s. The old daemon
was already draining: actual occupancy fell to16,602,630 bytes/39 files/52s
by05:36:53 UTC. This earlier drain must not be credited to the new code.

Review of the retained old blue container log found pre-existing capture loss.
The first recorded nonzero count was45 at2026-10-10 08:54:41 UTC. On October19,
148 records reported `AI log spool capacity exceeded or unavailable`, first
at13:00:46 UTC and last at17:18:50 UTC. The cumulative drop count reached
285,887 at17:19:21 UTC and remained fixed until blue stopped on October20.
The old shipper recorded only two completed status scans in the six-hour
12:00–18:00 UTC window, with stale reported queues15.51GB and18.49GB.
Neither container overrides the default20GiB WAL cap. This establishes a
historical spool capacity/unavailability incident; the generic error cannot
alone distinguish every capacity rejection from a directory-read failure.
Earlier small increases have no more specific cause recorded.

These are dropped **capture events**, not a request count. They were rejected
before successful persistence; replay of retained WAL cannot reconstruct
absent payloads. No full-history zero-loss claim is made. The new green
container has no capture-degraded records in this verification window.

## Change and verification

[PR6](https://github.com/Tooooa/sub2api/pull/6), tested commit
`6cf55ea8d4212e24577c2006294d78f7c972f5ac`, merged as
`580360fd8d6026c28bde99827c8f64abd2a72424`:

- Batch at most32 files, target8MiB input, one Kafka acknowledgement barrier.
  Keep source/capture key, sorted enqueue order, TLS, `acks=all`, producer
  idempotence and the32MiB producer memory bound.
- Validate locked files before enqueueing; retain malformed files. Only unlink
  after every event receives a successful delivery callback and the queue
  drains. On errors, partial callbacks, timeouts or interrupted delivery,
  preserve WAL for stable-ID retries. Verify inode/size/mtime before deletion.
- Independently refresh actual on-disk bytes, file count and oldest age every
  30 seconds even during a slow flush. Delivery counters are process-local.

All 18 focused tests passed. All [nine CI jobs](https://github.com/Tooooa/sub2api/actions/runs/39375658714)
and [security checks](https://github.com/Tooooa/sub2api/actions/runs/39375658523)
passed, including Python3.9/3.12, complete log-pipeline tests and backend
unit/integration tests. This report is implementation verification by the
implementer, not an independent review.

A benchmark on the production network used **copies** of32 already-backed-up
small files,4,605,822 bytes/72 events, preserving original event IDs. Original
WAL and backup were untouched. The old path took9.334s/32 flushes, the new path
2.077s/one flush:4.49× faster for this workload. Central deduplication handles
replay; this does not imply4.49× improvement for arbitrary bandwidth-bound
traffic.

Before installation, the shipper was briefly stopped to obtain a consistent
private snapshot while the application kept writing. Backup contains358 WAL
files/253,726,016 bytes. Every backed-up event was compared against central HDD
replay from the Mac using the supplied operator credential, restricted to this
source: **101 captures,3,688 events,189,122,834 body bytes; zero missing events
or body hash/length mismatches; all101 archived captures complete with zero
recorded drops**. Full event-ID/sequence/kind, source/topic provenance and body
SHA256 were checked. Four captures still in progress at the snapshot edge
subsequently had complete end markers centrally. No query credential was sent
to the relay.

## Deployment and observation

The candidate bytes matched the committed file before installation. The old
shipper stopped gracefully, the Python file was replaced atomically, and the
service restarted at05:47:24 UTC. The configuration, source identity and systemd
unit remained byte-identical. Installation completed05:47:28 UTC with the app
healthy. Before replacement, reported queue was4,684,787 bytes/7s; immediately
afterwards2,816,301 bytes/7 files/5s. The app continued writing throughout.

Five samples over 120 seconds showed current status timestamps (23 seconds old
at each sample), zero failures and actual oldest age of 1 second. The reported
queue reached zero at 05:49:24 UTC; the later filesystem samples contained only
fresh traffic. At 05:50:07 UTC the queue had one current file / 2,321,921 bytes /
oldest age 0 seconds, all backed-up filenames had left the live spool, public
health was OK, green was healthy with zero restarts, and neither new capture
degradation nor shipper delivery/status failures appeared.

Fresh public trace `backlog-fixed-79284872285749adbb7d0aa60fcf2a05` used
GPT-5.6-luna and GPT-6-luna. The daemon delivered both captures without manual
replay: 20 events / 17,414 body bytes. The source observer and central replay
matched every event and body's SHA256/length; both captures had continuous
sequences, end markers and zero drops. Temporary API keys were deleted. An
earlier observer attempt used inode-based offsets, which are unsafe when
rapid deletion permits inode reuse; that observer was corrected to stable
segment names and the verification rerun. Both earlier API calls succeeded;
the failed observer result is retained separately and is not counted as proof.

Non-secret summaries, CI results and the operation report are in the user's
external-disk project `outputs/2026-10-20-ai-log-backlog/`. Temporary local
query credentials and private comparison manifests are deleted after evidence
is saved; the original user-supplied handoff archive is unchanged.

## Backup and rollback

Private server backup:
`/root/backups/sub2api-shipper-backlog-20261020T052923Z/`.
Retain the358 original WAL files, old `shipper.py`, `shipper_control.py`, private
`shipper.json`, systemd unit, snapshot manifest/audit and verification evidence.
The body snapshots and credentials must not be committed or published.

To roll back only the shipper, stop `sub2api-ai-log-shipper.service`, restore
that backup's `shipper.py` to `/opt/sub2api-ai-log/shipper.py` with mode0644,
and start the service. The application keeps writing to the shared spool.
Never delete spool files to clear an alarm. Pending files survive rollback;
acknowledged duplicates retain stable IDs. An empty source queue proves Kafka
acknowledgement, not central archival; use archive replay for completeness.

This fix removes unnecessary acknowledgement barriers and stale reporting.
Finite20GiB spool and32MiB/1024-entry capture queues still have limits during
prolonged outages or overload. Central archive durability and independent
second-copy limitations remain as documented in [AI logging](AI_LOGGING.md).
