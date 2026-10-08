# BigModel GLM 接入记录

2026-10-09，在生产 `0.2.13-custom.1` 上通过管理员 API 先后新增两个智谱官方账号，未修改程序或部署镜像。生产镜像源码仍为 `da33263c0`。

## 当前配置

| 配置 | 值 |
| --- | --- |
| 第一个账号 | `27`，`BigModel GLM（智谱官方）` |
| 第二个账号 | `28`，`BigModel GLM（智谱官方 2）` |
| 接入类型 | `platform=openai`、`type=apikey`，官方 OpenAI 兼容接口 |
| 上游 Base URL | `https://open.bigmodel.cn/api/paas/v4` |
| 分组 | `2`，`晴天纪`，继续使用现有 `openai` 平台 |
| Responses 模式 | `extra.openai_responses_mode=force_chat_completions` |
| 模型限制 | 下列五个模型的同名 `credentials.model_mapping`，透传关闭 |
| 每个账号的并发 / 优先级 / 计费倍率 | `2` / `2` / `1` |

已加入账号模型限制和分组模型白名单：

- `glm-5.3`
- `glm-5.3-flash`
- `glm-5.3-flashx`
- `glm-5.2`
- `glm-4.7`

采用兼容账号使现有晴天纪分组的中转 Key 可直接调用 GLM。原生 `zhipu` 账号调度需要相应供应商分组或 Composite 分组；本次没有调整分组平台。现有 GPT 和图片模型的白名单条目保持原值。

两个官方 Key 分别存储在对应生产账号的凭据中，不记录在文档或 Git。两个账号均启用调度，绑定相同分组和模型限制，按相同优先级参与调度。采用普通按量接口；这不是 Coding Plan 专用端点。

## 客户端使用

客户端继续使用自己的中转 Key，OpenAI SDK Base URL 为 `https://sub2api.huafucius.top:8443/v1`，模型选择上述任一 ID。

`glm-5.3`、`glm-5.3-flash` 和 `glm-5.3-flashx` 的官方接口要求开启思考，不要传 `thinking.type=disabled`；本次验证使用 `reasoning_effort=low`。Responses 请求对应使用 `reasoning.effort=low`。

官方模型和协议说明：[模型概览](https://docs.bigmodel.cn/cn/guide/start/model-overview)、[OpenAI 兼容接口](https://docs.bigmodel.cn/cn/guide/develop/openai/introduction)。

## 验证证据

验证由配置实施者执行，使用同一生产分组的临时中转 Key。首次接入账号 27 的证据：

1. 从生产服务器直连官方接口，五个模型均返回 HTTP 200 和 `OK`。
2. 公网 `GET /v1/models` 返回上述五个 GLM 模型，并保留现有 GPT 模型。
3. 五个模型经公网 `POST /v1/chat/completions` 均返回 HTTP 200、正确模型 ID 和 `OK`。
4. `glm-5.2` 经公网流式 `POST /v1/responses` 返回文本 `OK` 和 `response.completed`，验证 Chat Completions 到 Responses 的转换。
5. `glm-5.3` 经流式 Responses 请求成功生成 `echo({"text":"OK"})` 的函数调用并完成，验证流式工具参数转换。
6. 账号 27 的用量统计记录了中转请求和非零计费，验证请求进入新账号。

免费 `glm-4.7-flash` 的直连测试返回 HTTP 429、错误码 `1305`（上游访问量过大），本次未加入模型列表。

原始验证结果和配置快照保存在本机 `/Volumes/MacData/09_tmp/bigmodel-20261009/`。临时中转 Key ID `129` 已在验证后删除；临时官方 Key 文件、管理员 JWT 和含 Key 的创建请求也已删除。

第二次接入账号 28 的证据：

1. 新 Key 从生产服务器直连官方接口，五个模型均返回 HTTP 200 和 `OK`。
2. 使用独立 `X-Session-Id` 测试会话，五款公网 Chat Completions 请求均成功，GLM-5.3 流式 Responses 成功生成 `echo({"text":"OK"})` 函数调用并完成。
3. 账号 28 的请求数在上述独立会话验证前后从 1 增至 7，确认六个验证请求全部经过新增账号。验证期间仅临时将账号 28 优先级设为 1，完成后恢复为 2。
4. 账号 27 的配置和分组模型白名单与第二次接入前快照一致；账号 27、28 均为启用调度的活跃账号，公网健康检查通过。

首轮复用相同测试内容时，已有内容会话粘性将请求留在账号 27。独立会话验证用于确认账号 28 的实际转发，新增账号不会改变已有会话的粘性。

第二次配置快照和验证结果位于 `/Volumes/MacData/09_tmp/bigmodel-second-20261009/`。临时中转 Key ID `130`、临时官方 Key 文件、管理员 JWT 和含 Key 的创建请求已删除。

## 备份与撤回

首次接入前的分组配置 `groups-before.json`、白名单更新前的完整分组配置 `group-2-before-write.json` 和项目运维文档 `服务器运维说明.before.md` 在 `/Volumes/MacData/09_tmp/bigmodel-20261009/`；第二次接入前的 `group-before.json`、账号 27 的无密钥配置快照、`BIGMODEL.before.md` 和 `服务器运维说明.before.md` 在 `/Volumes/MacData/09_tmp/bigmodel-second-20261009/`。无需程序或镜像回滚。

撤回单个 Key 时，通过管理员 API 关闭对应账号的调度，保留分组模型白名单供另一账号使用。全部撤回时关闭账号 27、28 的调度，再从晴天纪分组白名单移除上述五个 GLM ID。若此后分组有其他修改，应按条目撤回，避免整份覆盖旧快照。官方 Key 如需更换，更新对应账号的凭据，并重新验证公网调用。
