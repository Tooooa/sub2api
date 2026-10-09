# Sub2API deployment documentation

The verified production baseline is `0.2.15-custom.1` / `f4d0a1527`, deployed
on the Los Angeles relay on 2026-10-10 Asia/Shanghai. It integrates the reviewed
0.2.15 snapshot `9c2cfe052`, preserves blue-green deployment/recharge/Cockpit
sync, and enables tan-jin source capture. The next move is normal monitoring
of source backlog, disk headroom and central archival. Native WS inference
still has no eligible account under the existing transport configuration;
this rollout preserves that policy. See the release record for evidence.

| Record | State | Read when | Path |
|---|---|---|---|
| Maintained customizations | Deployed | Integrating upstream or identifying local behavior | [CUSTOMIZATIONS.md](CUSTOMIZATIONS.md) |
| Los Angeles logging rollout | Deployed | Checking runtime and rollback | [AI_LOG_LOS_ANGELES.md](../deploy/AI_LOG_LOS_ANGELES.md) |
| 0.2.15 custom release evidence | Verified | Identifying the deployed image, tests and backups | [Release record](../deploy/RELEASE_0.2.15_CUSTOM_1.md) |
| Blue-green deployment | Implemented | Updating the production app image | [BLUE_GREEN.md](../deploy/BLUE_GREEN.md) |
| Capture contract | Implemented, production pending | Understanding payload capture and loss behavior | [AI_LOGGING.md](../deploy/AI_LOGGING.md) |
| Central source registry | Attachment evidence | Source identity, credentials and central retention | [AI_LOG_MULTI_SITE_DESIGN.md](../deploy/AI_LOG_MULTI_SITE_DESIGN.md) |
| Runtime GLM providers | Verified before release | Preserving existing provider configuration | [BIGMODEL.md](BIGMODEL.md) |
| Production model allowlist | Verified before release | Checking current models after an update | [model-access.md](model-access.md) |
| Image model access | Verified before release | Checking image models after an update | [image-model-access.md](image-model-access.md) |

Other upstream feature documents in this directory retain their original scope.
Production state is established by readback and release records, not a version
number copied to a branch by a release workflow.

No implementation work is currently in flight for this release.
