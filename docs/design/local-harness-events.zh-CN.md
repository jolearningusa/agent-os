# Hermes 上下文事件契约 v1（L05）

本契约承接 [配置契约](local-harness-config.zh-CN.md) 和
[交付计划](../plans/local-harness-deliveries.zh-CN.md)，定义最小调用生命周期事件。
校验工具仅离线读取合成 fixture，真实请求正文采集由 L02/L3 另行交付。

## 事件与版本

文件采用非空 JSON 数组。`schemas/context-event.json` 定义单条事件，包含版本、
事件 ID、实例单调序号、UTC 时间、instance/session/turn/call/attempt ID、可空 parent
call ID，以及模型、Hermes commit、配置 hash 和调用状态。

`call_started` 状态固定 running，`call_finished` 状态为 completed/failed/cancelled/unknown。
完成事件必须包含 latency_ms、finish_reason 和 usage；usage 的 input/output tokens
可独立为 null，表示 unknown。unknown 调用结果可记录，恢复策略仍由后续执行器授权。

schema_version 固定 1。同版本允许未来增加可选字段，未知主版本拒绝；现有字段和枚举
保持语义稳定，新增必填项或不兼容状态需要版本迁移。时间必须为 UTC Z 格式并通过
实际日历校验，精度最多微秒。校验器显式注册日期检查，避免可选格式依赖缺失时静默跳过。字段错误仅显示规则和路径，不回显字段值。

## 文档级约束

事件 ID 在文档内唯一，sequence 在同一 instance 内按数组顺序严格递增，允许间隙。
不同实例序号独立。call ID 在同一实例内标识唯一会话/轮次/模型/版本/父调用，attempt
标识该调用的一次尝试；相同 call ID 的重试保留这些身份，使用新的 attempt ID。

每个 attempt 先出现一个 started，可接至多一个 finished。finished 身份与 started
一致。父调用必须在同实例同 session 内先出现 started，不能引用自己。这个先出现
约束同时阻止循环依赖。父调用可与子调用处于不同 turn，例如后续摘要关联原调用。

started 后没有 finished 的文档允许通过结构校验，命令显示 open_attempts 数量，
明确区分契约合法与采集完整。导出片段若缺少父调用或 started，当前版本拒绝并报告
文档关系缺失，之后如需部分导出再定义专门格式。

## 使用与验证

沿用 requirements-config.txt 的校验工具环境：

```sh
.local/harness-lab/config-check-env/bin/python scripts/check_context_events.py tests/fixtures/context-events.json
.local/harness-lab/config-check-env/bin/python -m unittest discover -s tests -v
```

命令成功返回 0，输出事件数与未结束 attempt 数。失败返回 1，不修改源文件。
使用上一切片的严格 JSON 解析和字段错误工具。schema 正反例及 CLI 测试覆盖非法版本、
缺字段、错误状态、非法时间、负用量、重复序号/事件、跨 session 父引用、完成前缺少
started、身份漂移和重复完成。无网络断言验证离线路径。

本切片增加字段格式校验的可选参数，配置校验现有入口与行为保持兼容。
正文、隐私过滤、大小边界和事件落盘完整性由 L30–L37 的采集层提供，此处只固定元数据
契约。后续上下文内容通过独立 schema 演进，合成 fixture 全部为人工编写。
