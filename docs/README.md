# Sub2API deployment documentation

The verified production baseline is `0.2.15-custom.1` / `f4d0a1527` on the
Los Angeles relay. The current candidate is `0.2.17-custom.1`, merging the
original Wei-Shaw `v0.2.17` tag while preserving the four documented operational
extensions. The next move is restoring the fork Actions workflow gate (GitHub has paused
it due to usage scale), then complete CI, CI-built linux/amd64 image verification,
isolated migration/old-image compatibility checks, then a backed-up blue-green
rollout authorized by the user. No builds may run on the user's Mac or relay.

| Record | State | Read when | Path |
|---|---|---|---|
| Maintained customizations | Candidate | Integrating upstream or identifying local behavior | [CUSTOMIZATIONS.md](CUSTOMIZATIONS.md) |
| Los Angeles logging rollout | Deployed | Checking runtime and rollback | [AI_LOG_LOS_ANGELES.md](../deploy/AI_LOG_LOS_ANGELES.md) |
| 0.2.15 custom release evidence | Verified | Identifying the deployed image, tests and backups | [Release record](../deploy/RELEASE_0.2.15_CUSTOM_1.md) |
| Blue-green deployment | Implemented | Updating the production app image | [BLUE_GREEN.md](../deploy/BLUE_GREEN.md) |
| Capture contract | Deployed | Understanding payload capture and loss behavior | [AI_LOGGING.md](../deploy/AI_LOGGING.md) |
| Central source registry | Attachment evidence | Source identity, credentials and central retention | [AI_LOG_MULTI_SITE_DESIGN.md](../deploy/AI_LOG_MULTI_SITE_DESIGN.md) |
| Runtime GLM providers | Verified before release | Preserving existing provider configuration | [BIGMODEL.md](BIGMODEL.md) |
| Production model allowlist | Verified before release | Checking current models after an update | [model-access.md](model-access.md) |
| Image model access | Verified before release | Checking image models after an update | [image-model-access.md](image-model-access.md) |

Other upstream feature documents in this directory retain their original scope.
Production state is established by readback and release records, not a version
number copied to a branch by a release workflow.

Current work: [0.2.17 upgrade plan](../plans/20261020-upstream-v0217.md).
