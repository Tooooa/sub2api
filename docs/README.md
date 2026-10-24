# Sub2API deployment documentation

The verified production baseline is `0.2.18-custom.5` / image
`sha256:1cbd71402cc7e691f8634b3ddce2bc9f2237974ee3cca73dc5edb68b2e6d8e7e`
on the Los Angeles relay, deployed on 2026-10-25 (Asia/Shanghai). It is the
`cfe937198` image built by GitHub Actions for `linux/amd64`; the prior
`0.2.17-custom.4` blue slot remains stopped for rollback. Recognized capacity
errors still switch accounts immediately instead of retrying on the same account.
The metadata/preamble/heartbeat output guards and AI log capture remain intact.
Full CI, security scan, image identity, blue-green health, migration, and
logging checks passed. Builds are prohibited on the user's Mac and production
relay.

| Record | State | Read when | Path |
|---|---|---|---|
| Maintained customizations | Deployed | Integrating upstream or identifying local behavior | [CUSTOMIZATIONS.md](CUSTOMIZATIONS.md) |
| 0.2.18 custom release evidence | Deployed and verified | Auditing the current image, backup, migration, rollback slot, and AI log spool | [Release record](../deploy/RELEASE_0.2.18_CUSTOM_5.md) |
| 0.2.17 custom release evidence | Historical base, with logging limits recorded | Identifying the upstream merge and original custom baseline | [Release record](../deploy/RELEASE_0.2.17_CUSTOM_1.md) |
| Faster capacity account switching | Deployed and verified | Reducing pre-output overload latency | [Fast failover](../deploy/FAST_CAPACITY_FAILOVER_20261023.md) |
| Streaming capacity failover | Historical custom.3 rollout; guards retained | Investigating metadata mistaken for output and replay boundaries | [Failover repair](../deploy/STREAMING_CAPACITY_FAILOVER_20261021.md) |
| Source WAL backlog repair | Deployed and archive-verified; historical loss disclosed | Investigating queue metrics, throughput, backup and recovery | [Backlog repair](../deploy/AI_LOG_BACKLOG_20261020.md) |
| Los Angeles logging rollout | Deployed | Checking runtime and rollback | [AI_LOG_LOS_ANGELES.md](../deploy/AI_LOG_LOS_ANGELES.md) |
| 0.2.15 custom release evidence | Historical rollback baseline | Identifying the retained blue image | [Release record](../deploy/RELEASE_0.2.15_CUSTOM_1.md) |
| Blue-green deployment | Implemented | Updating the production app image | [BLUE_GREEN.md](../deploy/BLUE_GREEN.md) |
| Capture contract | Deployed | Understanding payload capture and loss behavior | [AI_LOGGING.md](../deploy/AI_LOGGING.md) |
| Central source registry | Attachment evidence | Source identity, credentials and central retention | [AI_LOG_MULTI_SITE_DESIGN.md](../deploy/AI_LOG_MULTI_SITE_DESIGN.md) |
| Runtime GLM providers | Verified before release | Preserving existing provider configuration | [BIGMODEL.md](BIGMODEL.md) |
| Production model allowlist | Verified before release | Checking current models after an update | [model-access.md](model-access.md) |
| Image model access | Verified before release | Checking image models after an update | [image-model-access.md](image-model-access.md) |

Other upstream feature documents in this directory retain their original scope.
Production state is established by readback and release records, not a version
number copied to a branch by a release workflow.

Source WAL backlog repair is complete; see its verification record above.
Check the current release record before reusing historical runtime observations.
