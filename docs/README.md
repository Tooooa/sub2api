# Sub2API deployment documentation

The approved production baseline is `0.2.13-custom.1` / `da33263c0` on the
Los Angeles relay. The current candidate integrates the verified 0.2.15 dev
snapshot `9c2cfe052` and adds optional AI traffic archival while preserving
blue-green deployment, recharge and Cockpit token synchronization. It is not
yet verified or deployed. The next move is remote CI/image validation and a
backed-up blue-green rollout; site identity must be confirmed before logging.

| Record | State | Read when | Path |
|---|---|---|---|
| Maintained customizations | Candidate | Integrating upstream or identifying local behavior | [CUSTOMIZATIONS.md](CUSTOMIZATIONS.md) |
| Los Angeles logging rollout | Candidate | Preparing this release, checking runtime and rollback | [AI_LOG_LOS_ANGELES.md](../deploy/AI_LOG_LOS_ANGELES.md) |
| Blue-green deployment | Implemented | Updating the production app image | [BLUE_GREEN.md](../deploy/BLUE_GREEN.md) |
| Capture contract | Implemented, production pending | Understanding payload capture and loss behavior | [AI_LOGGING.md](../deploy/AI_LOGGING.md) |
| Central source registry | Attachment evidence | Source identity, credentials and central retention | [AI_LOG_MULTI_SITE_DESIGN.md](../deploy/AI_LOG_MULTI_SITE_DESIGN.md) |
| Runtime GLM providers | Verified before release | Preserving existing provider configuration | [BIGMODEL.md](BIGMODEL.md) |
| Production model allowlist | Verified before release | Checking current models after an update | [model-access.md](model-access.md) |
| Image model access | Verified before release | Checking image models after an update | [image-model-access.md](image-model-access.md) |
| Current work | In progress | Resuming this rollout | [plan](../plans/20261010-ai-log-rollout.md) |

Other upstream feature documents in this directory retain their original scope.
Production state is established by readback and release records, not a version
number copied to a branch by a release workflow.
