# Sub2API deployment documentation

The verified production baseline is `0.2.19-custom.1`, application source
`dba6cd764`, CI-built for `linux/amd64`, deployed on New York `23.252.107.103`
on 2026-11-02. Active blue listens on `8080`; old green `0.2.18-custom.5` is
stopped and retained for rollback. Both public sites switched together after
real-request gates and a five-minute monitor. Full CI/security and restored-DB
new/old compatibility checks passed. The four operational extensions, capacity
failover and stream replay guards remain intact; scheduling flags and the
19-model allowlist, including GPT-6.1 Terra, were preserved. Builds remain prohibited on the user's Mac
and production relay.

The pre-existing New York-to-Wuhan log transport outage was repaired using a
restricted Japan TCP relay. Original full spool data remains in place and is
draining; newest request WAL checks passed, but historical recovery and central
replay of those newest captures are not yet complete. See the
[release evidence](../deploy/RELEASE_0.2.19_CUSTOM_1.md) for identity, backups,
relay dependency, limits and rollback.

| Record | State | Read when | Path |
|---|---|---|---|
| 0.2.19 custom release evidence | Deployed and verified | Current image, migration, two-site cutover and log transport recovery | [Release record](../deploy/RELEASE_0.2.19_CUSTOM_1.md) |
| Maintained customizations | Deployed | Integrating upstream or identifying local behavior | [CUSTOMIZATIONS.md](CUSTOMIZATIONS.md) |
| 0.2.18 custom release evidence | Retained green rollback | Auditing the current image, backup, migration, rollback slot, and AI log spool | [Release record](../deploy/RELEASE_0.2.18_CUSTOM_5.md) |
| 0.2.17 custom release evidence | Historical base, with logging limits recorded | Identifying the upstream merge and original custom baseline | [Release record](../deploy/RELEASE_0.2.17_CUSTOM_1.md) |
| Faster capacity account switching | Deployed and verified | Reducing pre-output overload latency | [Fast failover](../deploy/FAST_CAPACITY_FAILOVER_20261023.md) |
| Streaming capacity failover | Historical custom.3 rollout; guards retained | Investigating metadata mistaken for output and replay boundaries | [Failover repair](../deploy/STREAMING_CAPACITY_FAILOVER_20261021.md) |
| Source WAL backlog repair | Deployed and archive-verified; historical loss disclosed | Investigating queue metrics, throughput, backup and recovery | [Backlog repair](../deploy/AI_LOG_BACKLOG_20261020.md) |
| Los Angeles logging rollout | Deployed | Checking runtime and rollback | [AI_LOG_LOS_ANGELES.md](../deploy/AI_LOG_LOS_ANGELES.md) |
| 0.2.15 custom release evidence | Historical rollback baseline | Identifying the retained blue image | [Release record](../deploy/RELEASE_0.2.15_CUSTOM_1.md) |
| Blue-green deployment | Implemented | Updating the production app image | [BLUE_GREEN.md](../deploy/BLUE_GREEN.md) |
| Capture contract | Deployed | Understanding payload capture and loss behavior | [AI_LOGGING.md](../deploy/AI_LOGGING.md) |
| Central source registry | Attachment evidence | Source identity, credentials and central retention | [AI_LOG_MULTI_SITE_DESIGN.md](../deploy/AI_LOG_MULTI_SITE_DESIGN.md) |
| Runtime GLM providers | Current configuration read back 2026-11-02 | Preserving existing provider configuration | [BIGMODEL.md](BIGMODEL.md) |
| Production model allowlist | 19 enabled, including GPT-6.1 Terra, as of 2026-11-02 | Checking current models after an update | [model-access.md](model-access.md) |
| Image model access | Verified before release | Checking image models after an update | [image-model-access.md](image-model-access.md) |

Other upstream feature documents in this directory retain their original scope.
Production state is established by readback and release records, not a version
number copied to a branch by a release workflow.

Source WAL backlog repair is complete; see its verification record above.
Check the current release record before reusing historical runtime observations.
