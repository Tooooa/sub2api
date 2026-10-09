# 生产模型清单

## 当前允许的模型

2026-10-09，根据当天 10:19 完成的全模型实测，清理生产“晴天纪”分组 `2` 的 `model_allowlist.models`。白名单保持启用，当前允许 17 个模型：

| 类别 | 模型 ID |
| --- | --- |
| GPT（7 个） | `gpt-5.6-sol`、`gpt-5.6`、`gpt-5.6-terra`、`gpt-5.6-luna`、`gpt-5.5`、`gpt-6-astra`、`codex-auto-review` |
| GLM（5 个） | `glm-5.3`、`glm-5.3-flash`、`glm-5.3-flashx`、`glm-5.2`、`glm-4.7` |
| 图片（5 个） | `gpt-image-1`、`gpt-image-1.5`、`gpt-image-2`、`gpt-image-2.5-flare`、`gpt-image-2.5-sunburst` |

实测范围：GPT 使用公网流式 Responses 请求，GLM 使用公网 Chat Completions 请求，图片模型各实际生成 1 张图片。20 个原有条目中，以上 17 个成功，下面 3 个返回 400。

全模型诊断快照、测试记录和图片保存在 `/Volumes/MacData/09_tmp/relay-health-20261009-101215/`。此列表记录该次实测及清理时的状态；供应商权限、账号状态和限额仍可能变化。

## 已移除的条目

- `gpt-5.4`
- `gpt-5.4-mini`
- `gpt-5.3-codex-spark`

三者在当前 ChatGPT/Codex 上游账号下实测均返回：`The '<model>' model is not supported when using Codex with a ChatGPT account.` 用户随后授权从模型清单移除。

本次通过管理员 API 仅从分组白名单移除这三个 ID，保留其余条目的原有顺序和白名单启用状态。配置更新后，用同一分组的临时 Key `133` 核对公网 `GET /v1/models`，结果与保留的 17 个 ID 完全一致，已不包含被移除条目；公网 `/health` 返回 `{"status":"ok"}`。

本次不需要构建、部署或重启应用。临时验证 Key 和管理员 JWT 文件已删除。

## 备份与恢复

改动前的完整分组配置 `group-before.json`、改动后的 `group-after.json`、验证记录 `verification.json` 和项目运维文档 `服务器运维说明.before.md` 保存在 `/Volumes/MacData/09_tmp/remove-unsupported-models-20261009/`。

若之后新增可支持被移除模型的上游账号，应先通过该账号实测，再将对应 ID 加回分组白名单。如果此后分组存在其他修改，恢复时应按模型条目追加，避免用旧快照覆盖新配置。

相关记录：[BigModel GLM](BIGMODEL.md)、[图片模型启用与验证](image-model-access.md)。
