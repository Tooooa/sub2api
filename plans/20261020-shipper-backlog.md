# Preserve and drain tan-jin source WAL

User authorized diagnosis and correction of the previous ~2 GB log backlog,
preserving all logs. Production application stays on0.2.17-custom.1; no builds
on the Mac or LA server. Source identity/configuration must not change.

Evidence: actual queue at05:26 UTC ~307 MB/526 files/oldest1147s, falling.
Status file still reports2.36GB/3808s because it totals files before deletion
and only publishes after a potentially35-minute scan. Go WAL rotates each
second or4MiB; shipper flushes Kafka after every file, serializing batch
barriers across ~180ms WAN RTT and slow/variable cross-border bandwidth.
Three historical connection closures recovered; no segment failures in6h.

Private snapshot started at
/root/backups/sub2api-shipper-backlog-20261020T052923Z
with old script/config/service and queued WAL. Briefly stop shipper, keep app
writing, copy locked consistent files, restart existing shipper in finally.
Completed:358 files/253726016 bytes; parsed3688 unique events across101 captures,
189122834 body bytes;97 end markers and0 recorded drops. Expected per-event
identity/body hashes saved privately for a complete central archive comparison.

Implement bounded multi-file delivery, preserving file locks and order,
all-ack-before-unlink, stable IDs and retention on ambiguous outcome.
Reject malformed files before enqueue; isolate them without starving valid WAL.
Publish actual on-disk queue metrics on an independent30-second timer.
Test errors, retries, locked writers, malformed files, shutdown and stale metrics;
run relevant CI on3.9/3.12 and full log tests before installing Python source.
Measure delivery improvement and current drain; verify snapshot event identities
and body integrity in central HDD using local read-only query credential.
Keep raw backup until completeness is proven; never erase unconfirmed WAL.
Record evidence and backup/rollback, remove plan and clean worktree at completion.
