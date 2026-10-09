# Los Angeles AI log rollout

User authorized integrating the supplied dev snapshot, preserving the production extensions, building a deployment image, and deploying with blue-green. Never compile on the user's Mac. The latest user message conditionally permits a Los Angeles build if resources suffice; prefer the existing Tooooa GitHub Actions route, which has successful release/CI evidence.

Baseline: production `da33263c0` / `ghcr.io/tooooa/sub2api:0.2.13-custom.1`; local documentation-only follow-ups through `27ba739d9`. Candidate: verified attachment / origin/dev `9c2cfe05223208ae6ed49d83fec315f935bc78d9` / 0.2.15. All 4,339 source files match the remote Git archive. Both histories diverge; simulation identified seven conflict files. Recharge and Cockpit sync files match exactly.

Worktree: `/Volumes/MacData/01_Projects/05_codex-worktree/sub2api-ai-log-deploy/sub2api`, branch `feature/ai-log-losangeles-20261010`.

Source identity question is pending: whether Los Angeles is the attachment's tan-jin source. Do not install credentials or enable capture until confirmed. The other profile belongs to Wuhan. Keep secret configs out of Git, logs, public artifacts and the build context.

Production readback: AlmaLinux 9.7, Python 3.9.25, SELinux disabled, 6 cores, ~12 GiB available memory, 243 GB free disk; green 18081 is healthy. Existing blue container is stopped and retained. No shipper installed. Active recharge timer. One additive release migration drops two platform CHECK constraints; all earlier SQL files unchanged. Need isolated migration/rollback validation.

Next: merge the snapshot in this worktree; resolve with reviewed 0.2.15 dependency/version and logging deployment changes while preserving local runtime docs and the pinned build strategy. Add source/runtime verification in CI. Build linux/amd64 remotely. Back up live PostgreSQL, data, Caddy, env and active state just before deployment, preserving concurrent provider/model/account configuration. Archive the occupied inactive slot only after backup. Validate candidate before switching, then real GPT/GLM/image/SSE/WS and bookkeeping. Enable/source-verify logging and replay the actual test capture with the central query credential kept on this Mac/VPN.

Thread reference inspected: `01a08a39-2cc6-71d0-83a0-7a290b9197fe` (app title: 调查 image2 限流原因); recent suggestions explicitly used CI and awaiting authorization. Current user authorization supersedes that wait.
