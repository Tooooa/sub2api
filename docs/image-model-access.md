# 图片模型启用与验证

## Codex 文本与原生图片额度隔离（2026-11-13）

故障证据：账号 44 在 11 月 12 日 22:24:41 调用 `gpt-6-astra` 收到
`usage_limit_reached`，周窗口重置时间被写成账号整体停调。11 月 13 日
10:29:32 家庭网页 Flare 生图因无可用账号返回 503；10:30:02 一次额度查询
清除了旧停调状态，随后普通生图和礼帖分别在 19.0 / 21.8 秒完成。

修复候选将明确的 Codex OAuth 文本配额耗尽写入保留 scope
`openai:codex_text`，原生 `/v1/images/*` 已知直调模型不继承该限制或文本
5h/7d 自动暂停阈值。Responses 图片工具仍需文本驱动，不享受该豁免。
原生图片的明确配额耗尽仍写 `openai:image_generation`；Spark、登录失效、
账号停用、风控和其他供应商规则保持独立。额度恢复只使文本保留 scope
过期，不删除其他模型限制。旧版账号整体冷却不会被无条件迁移或清除。

候选基于线上 `f4098e09a` 和随后仅文档的 main 更新；无数据库迁移。
CI 测试、linux/amd64 镜像、蓝绿发布和真实请求验证完成后补充发布证据。

## 当前状态

2026-10-09，在生产 `0.2.13-custom.1` 的“晴天纪”分组 `2` 启用 `gpt-image-2.5-sunburst`。仅在原有 `model_allowlist.models` 中追加此 ID，保持白名单启用状态及所有既有条目。程序已支持该模型，未修改源码、构建、部署或重启应用。

客户端继续使用原中转 Key，调用：

- OpenAI SDK Base URL：`https://sub2api.huafucius.top:8443/v1`
- 生图端点：`POST /v1/images/generations`
- 模型：`gpt-image-2.5-sunburst`

本次仅开放不带日期的模型 ID。现有 `gpt-image-2.5-flare` 白名单条目继续保留。

## 实际生图验证

验证由配置实施者执行。用户明确指定中转站及模型，使用 `imagegen` 技能的 bundled CLI，通过 `OPENAI_BASE_URL` 指向中转公网 API，使用晴天纪分组的临时测试 Key `131`。请求 `n=1`、`quality=low`、`size=1024x1024`、`output_format=png`。

最终提示词原文：

> A clean flat illustration of a blue laboratory flask beside a small golden sun on a white background. Centered composition, crisp shapes, no text, no watermark.

| 验证项 | 结果 |
| --- | --- |
| 公网模型列表 | `/v1/models` 包含 Sunburst，既有 Flare 仍可见 |
| 实际生图 | 成功返回 1 张图片，CLI 耗时约 22.6 秒 |
| 用量记录 ID | `1636630` |
| 实际账号 | `26` |
| 请求模型 | `gpt-image-2.5-sunburst` |
| 上游模型 | `gpt-image-2.5-sunburst` |
| 上游端点 | `/v1/images/generations` |
| 输出校验 | 可完整解码的 PNG，`1254 × 1254`，`1,006,102` 字节 |
| 肉眼检查 | 白底、蓝色烧瓶和金色太阳，无文字与水印，符合提示词 |
| 公网健康检查 | `{"status":"ok"}` |

测试请求指定 `1024x1024`，实际返回的图片为 `1254x1254`，已按原始返回保存。本记录确认生图可用及实际模型归属，不保证上游输出严格遵循请求尺寸。

测试图保存在工作区 `/Volumes/MacData/02_Areas/04_Development/实验室中转站/outputs/2026-10-09-sunburst/sunburst-test.png`。请求参数、提示词、模型列表、图片检查、用量记录和配置摘要位于 `/Volumes/MacData/09_tmp/sunburst-20261009/`。

参考：[OpenAI 官方模型说明](https://developers.openai.com/api/docs/models/gpt-image-2.5-sunburst)、[Images API 参数](https://developers.openai.com/api/reference/resources/images/methods/generate)。

## 备份、清理与撤回

修改前的完整分组配置 `group-before.json` 和项目运维文档 `服务器运维说明.before.md` 已备份到上述验证目录。临时测试 Key `131` 已删除；管理员 JWT、临时 Key 文件、含 Key 创建请求和测试用 Python 环境/依赖缓存均已清理。保留测试图及不含密钥的备份和验证记录。

撤回时，通过管理员 API 从分组 `2` 的 `model_allowlist.models` 中移除 `gpt-image-2.5-sunburst`，保留其余条目与现有启用状态。如分组后续有其他改动，应按条目撤回，避免用旧快照覆盖新配置。
