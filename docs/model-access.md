# 生产模型清单

## 2026-11-02 两站新增 GLM API Key

纽约分组 `2` 新增 `GLMrcy` / `GLMzxh2`（账号 `45/46`），武汉分组 `4` 新增同名账号（账号 `35/36`）。四个账号均为 active、可调度、并发 `5`、优先级 `2`、倍率 `1`，沿用 BigModel Coding Plan 端点和四个同名 GLM 映射。两个 Key 均经官方接口返回 `OK`，两站公网 `/v1/models`、GLM Chat Completions 和 `/health` 核验通过；验证 Key 已删除。详见 [BigModel GLM 接入记录](BIGMODEL.md)。

## 2026-11-02 两站启用 GPT-6.1 Terra

纽约“晴天纪”分组 `2` 和武汉“晴天纪武汉”分组 `4` 均已在白名单追加 `gpt-6.1-terra`，两边的模型数都由 18 个变为 19 个。原有模型顺序、图片开关、消息分发开关、账号调度状态和其他分组字段保持原值。

纽约已经运行 `0.2.19-custom.1-dba6cd764`；武汉原先仍是 `0.2.18-custom.5-cfe937198`，因为旧镜像的静态 OpenAI 模型目录不含 Terra，白名单虽已写入但公网列表仍只有 18 个。为使武汉真正对外可用，复用纽约已验证的 `linux/amd64` 预构建镜像 `sub2api:0.2.19-custom.1-dba6cd764`，经镜像传输后按武汉蓝绿脚本发布：蓝槽 `18080` 接管流量，旧绿槽 `18081` 保留回滚。没有在本机或服务器构建源码、容器镜像。

发布后两站均完成线上读回：

| 站点 | 分组 | `/v1/models` | 真实测试 |
| --- | --- | ---: | --- |
| 纽约 | `2`「晴天纪」 | 19，包含 Terra | 管理员账号 `17`：`test_complete/success=true` |
| 武汉 | `4`「晴天纪武汉」 | 19，包含 Terra | 管理员账号 `22`：`test_complete/success=true`；公网 Responses 流式返回 `public_terra_ok` 和 `response.completed` |

武汉发布后的健康检查为 `{"status":"ok"}`。AI 日志 shipper 和自动充值 timer 均为 active，旧绿槽镜像仍保留。详细配置快照和请求证据位于 `/Volumes/MacData/02_Areas/04_Development/实验室中转站/outputs/2026-11-02-gpt61terra-enable/`；武汉发布备份位于服务器 `/root/backups/gpt61terra-v0219-wuhan-20261102T115007Z/`。

回退时先将武汉 Caddy 上游切回保留的 `sub2api-green`，再按最新分组配置只移除 `gpt-6.1-terra`；不要用旧整份快照覆盖后续账号或分组变更。

## 2026-11-02 软件升级后的清单

纽约主站已蓝绿升级至 `0.2.19-custom.1-dba6cd764`，蓝槽 `8080`。下面早间审计的 18 个白名单条目与顺序保持不变；新版增加了 Terra 的目录和协议支持，但本次未追加分组白名单。候选与公网列表均仍为 18 个条目，GPT、GLM、Sunburst 真实调用与用量记录通过。详见 [发布证据](../deploy/RELEASE_0.2.19_CUSTOM_1.md)。

## 2026-11-02 当前主站与新模型核验

生产主栈已于 10 月 27 日迁至纽约 `23.252.107.103`（`ssh newYork`），本轮运行镜像仍为 `0.2.18-custom.5-cfe937198`，镜像 ID 为 `sha256:1cbd71402cc7e691f8634b3ddce2bc9f2237974ee3cca73dc5edb68b2e6d8e7e`，green / `18081`，容器健康。主公网入口为 `https://api.aura-home.online`；旧 `https://sub2api.huafucius.top:8443` 仍作兼容核验。洛杉矶旧栈不是本轮操作目标。

分组 `2` 最终保留本轮开始时的 18 个条目及原顺序：

| 类别 | 模型 ID |
| --- | --- |
| GPT（9 个） | `gpt-5.6-sol`、`gpt-5.6`、`gpt-5.6-terra`、`gpt-5.6-luna`、`codex-auto-review`、`gpt-6-astra`、`gpt-6.1-sol`、`gpt-6-sol`、`gpt-6-luna` |
| GLM（4 个） | `glm-5.3`、`glm-5.3-flash`、`glm-5.2`、`glm-4.7` |
| 图片（5 个） | `gpt-image-1`、`gpt-image-1.5`、`gpt-image-2`、`gpt-image-2.5-flare`、`gpt-image-2.5-sunburst` |

此表是本轮配置及公网列表读回，未重复推理测试旧模型或生成旧模型图片。`gpt-image-1` 保留既有配置，本轮没有重新判断其可用性；10 月 26 日曾记录官方退役公告与实际调用仍成功的差异。GLM 当前实际账号与端点见 [BigModel 接入记录](BIGMODEL.md)，不能沿用 10 月 9 日的账号清单。

### GPT-6.1 Terra 试启用后回退

[官方发布记录](https://developers.openai.com/api/docs/changelog)于 10 月 26 日发布 [`gpt-6.1-terra`](https://developers.openai.com/api/docs/models/gpt-6.1-terra)。账号 `17` 的管理员单账号实际调用返回非空文本 `Hi! How can I help?` 和 `test_complete/success=true`，没有 SSE error。生产运行时计费查询返回 `found=true`，输入/输出/缓存读取/缓存写入分别为每百万 token $1/$5/$0.05/$1.25，与[官方 Standard 定价](https://developers.openai.com/api/docs/pricing)一致；未写入或伪造价格。

北京时间 10:02，仅在最新分组 `model_allowlist.models` 末尾追加此同名 ID，读回 18 → 19，其他变化只有 `updated_at`。使用同组、限额 $0.10、一天有效的临时 Key `204` 验证公网时，`GET /v1/models` 仍只返回原有 18 个条目，缺少 Terra，因此没有继续公网 Responses/Chat Completions 推理验收，也没有宣布启用成功。

随即重新读取最新分组，仅移除本轮追加的 Terra，回读恢复 18 个；原有顺序、无关设置、账号映射均保留。源码 `cfe937198` 的 `GatewayService.GetAvailableModels` 对未设映射的 OAuth 账号补充静态 `openai.DefaultModelIDs()`，`GroupModelAllowlist.FilterForListing` 再与候选目录求交；该静态目录没有 Terra。管理员账号目录能够动态看到 Terra，不代表普通 `/v1/models` 会自动纳入。当前授权只允许为 GPT 增量追加白名单，不能借此修改 OAuth 账号映射、切换列表模式、改源码或升级部署来绕过限制。完成启用需要另行处理目录能力并重新验收。

10:04 使用临时 Key `205`（限额 $0.02、一天有效）读回两个公网地址的模型清单，均与恢复后的 18 项完全一致，`/health` 为 `ok`。两个临时 Key 均已删除。核心账号设置、GLM 端点和映射前后比较无差异；没有新增路由、刷新凭据、构建、部署或重启服务。

### 本轮其他候选

- `gpt-6-rosalind`：10 月 30 日官方发布，面向获批内部生命科学研究；现有 OAuth 账号 `2` 实测返回 HTTP 400 / `model_not_found`，明确不支持 ChatGPT 登录调用，未启用。
- `glm-5.3-flashx-legal`：[官方模型文档](https://docs.bigmodel.cn/cn/guide/models/vlm/glm-5.3-flash#glm-5-3-flashx-legal)说明企业定向开放、需申请。现有账号 `32` 使用其原 Coding Plan 端点实测返回 HTTP 429、代码 `1113`（余额不足或无可用资源包），未得到成功输出，未启用、充值或改端点。该结果不等于已证明当前四款 GLM 均不可用。
- `gpt-6-chat-thinking`、`gpt-reserve`：部分账号目录出现，但本轮官方文档精确检索未建立独立公开模型身份和定价，不推断为可启用新模型。

原始 SSE、运行时定价、修改前/后/回退配置、脱敏账号目录、原文档和最终核验保存在 `/Volumes/MacData/09_tmp/weekly-model-discovery-20261102/`。本轮没有保留新增模型。以后重试须先核对目录能力有新证据，再重新执行账号及公网实际调用；不要恢复整份旧快照。

## 2026-10-20 升级时的实时可用状态

`0.2.17-custom.1` 升级前后，旧版与新版 `/v1/models` 均返回 14 个模型（9 个 GPT、5 个图片模型），清单完全一致。分组白名单仍保留下列 19 个条目，但两个 GLM 账号 `27`、`28` 在升级前已是 `schedulable=false`，因此 5 个 GLM 未出现在实时可用列表中。本次保留停用状态，未执行 GLM 真实调用测试。白名单允许与当前可调度账号可用是两项不同条件。

升级验证通过 GPT-5.6 Luna、GPT-6 Luna 普通调用、GPT-6.1 Sol/GPT-6 Sol 流式、GPT 函数调用及 Sunburst 图片生成；完整证据见 [0.2.17 发布记录](../deploy/RELEASE_0.2.17_CUSTOM_1.md)。下面 10 月 15 日逐模型实测保留为历史记录。

## 2026-10-15 全模型实测（历史）

2026-10-15 对生产“晴天纪”分组 `2` 的 20 个公开模型逐项实测，确认 `gpt-5.5` 已不支持后移除。当时白名单保持启用，允许 19 个模型；其余条目和顺序保持原值。10 月 10 日新增的 GPT-6.1 Sol、GPT-6 Sol、GPT-6 Luna 均已包含在当前清单中：

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
