# 生产模型清单

## 2026-10-20 升级时的实时可用状态

`0.2.17-custom.1` 升级前后，旧版与新版 `/v1/models` 均返回 14 个模型（9 个 GPT、5 个图片模型），清单完全一致。分组白名单仍保留下列 19 个条目，但两个 GLM 账号 `27`、`28` 在升级前已是 `schedulable=false`，因此 5 个 GLM 未出现在实时可用列表中。本次保留停用状态，未执行 GLM 真实调用测试。白名单允许与当前可调度账号可用是两项不同条件。

升级验证通过 GPT-5.6 Luna、GPT-6 Luna 普通调用、GPT-6.1 Sol/GPT-6 Sol 流式、GPT 函数调用及 Sunburst 图片生成；完整证据见 [0.2.17 发布记录](../deploy/RELEASE_0.2.17_CUSTOM_1.md)。下面 10 月 15 日逐模型实测保留为历史记录。

## 当前允许的模型

2026-10-15 对生产“晴天纪”分组 `2` 的 20 个公开模型逐项实测，确认 `gpt-5.5` 已不支持后移除。白名单保持启用，当前允许 19 个模型；其余条目和顺序保持原值。10 月 10 日新增的 GPT-6.1 Sol、GPT-6 Sol、GPT-6 Luna 均已包含在当前清单中：

| 类别 | 模型 ID |
| --- | --- |
| GPT（9 个） | `gpt-5.6-sol`、`gpt-5.6`、`gpt-5.6-terra`、`gpt-5.6-luna`、`gpt-6-astra`、`gpt-6.1-sol`、`gpt-6-sol`、`gpt-6-luna`、`codex-auto-review` |
| GLM（5 个） | `glm-5.3`、`glm-5.3-flash`、`glm-5.3-flashx`、`glm-5.2`、`glm-4.7` |
| 图片（5 个） | `gpt-image-1`、`gpt-image-1.5`、`gpt-image-2`、`gpt-image-2.5-flare`、`gpt-image-2.5-sunburst` |

本次实测：10 个 GPT 文本模型使用公网流式 Responses，5 个 GLM 使用公网 Chat Completions，5 个图片模型各实际生成 1 张有效 PNG。GPT-5.5 返回 HTTP 400，其余 19 个全部成功，且用量记录与相应模型一致。`gpt-5.6` 是已保留的 Sol 别名，其用量上游为 `gpt-5.6-sol`。

本轮原始响应、五张测试图、用量记录、配置和文档备份保存在 `/Volumes/MacData/09_tmp/audit-model-access-20261015-194223/`。供应商权限、账号状态和限额仍可能变化；本次验证基础文本和图像生成接口，不代表穷尽所有功能。

## 2026-10-15 清理 GPT-5.5

[OpenAI 官方说明](https://learn.chatgpt.com/docs/models#gpt-55-retirement)：GPT-5.5 于 2026-10-14 19:00 UTC（北京时间 10 月 15 日 03:00）退出使用 ChatGPT 登录的 Codex；直接使用 OpenAI API Key 的 API 不受该退役影响。本站 GPT-5.5 上游为 ChatGPT OAuth，因此该退役适用于当前接入方式。

公网实际调用返回 HTTP 400：`The 'gpt-5.5' model is not supported when using Codex with a ChatGPT account.` 该失败属于明确的模型不支持，非令牌过期、临时限流或网络故障。按用户此前“移除不支持模型”的要求，仅从分组白名单移除此 ID，保留其他 19 个条目和全部无关配置。

移除前已保存最新完整分组配置及文档副本；更新后通过原有审计 Key 核对公网 `GET /v1/models` 为 19 个条目，与白名单完全一致且不包含 GPT-5.5。其余 9 个 GPT、5 个 GLM、5 个图片模型均通过本轮真实调用，且分别有成功的用量记录；五个图片用量记录的生成数量均为 1。

临时验证 Key `155`、`156` 已删除，JWT 仅在进程内存使用；未修改账号、计费或上游端点，未构建、部署或重启服务，公网 `/health` 正常。备份和验证报告位于 `/Volumes/MacData/09_tmp/audit-model-access-20261015-194223/`。若以后接入实际支持 GPT-5.5 的其他上游，应先实测再增量恢复该 ID，不用旧快照覆盖其他后续修改。

## 已移除的条目

### 2026-10-15

- `gpt-5.5`：当前 ChatGPT OAuth 上游已退役，见本轮实测。

### 2026-10-09

- `gpt-5.4`
- `gpt-5.4-mini`
- `gpt-5.3-codex-spark`

三者在当前 ChatGPT/Codex 上游账号下实测均返回：`The '<model>' model is not supported when using Codex with a ChatGPT account.` 用户随后授权从模型清单移除。

2026-10-09 通过管理员 API 仅从分组白名单移除这三个 ID，保留其余条目的原有顺序和白名单启用状态。配置更新后，用同一分组的临时 Key `133` 核对公网 `GET /v1/models`，结果与保留的 17 个 ID 完全一致，已不包含被移除条目；公网 `/health` 返回 `{"status":"ok"}`。

上述模型清理均不需要构建、部署或重启应用。10 月 9 日的临时验证 Key 和管理员 JWT 文件已删除。

## 备份与恢复

改动前的完整分组配置 `group-before.json`、改动后的 `group-after.json`、验证记录 `verification.json` 和项目运维文档 `服务器运维说明.before.md` 保存在 `/Volumes/MacData/09_tmp/remove-unsupported-models-20261009/`。

若之后新增可支持被移除模型的上游账号，应先通过该账号实测，再将对应 ID 加回分组白名单。如果此后分组存在其他修改，恢复时应按模型条目追加，避免用旧快照覆盖新配置。

相关记录：[BigModel GLM](BIGMODEL.md)、[图片模型启用与验证](image-model-access.md)。
