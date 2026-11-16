# Hermes 本地配置契约 v1

依据 [L0a ADR](../adr/0001-hermes-local-lab.zh-CN.md) 与
[交付计划 L00](../plans/local-harness-deliveries.zh-CN.md)，本切片定义配置校验入口。
适用单机合成实验，校验命令不获取源码、不启动 Harness、不发起模型调用。

## 文件与格式

`harness.lock.json` 固定已接受的 fork、commit、源码文件 SHA-256、上游运行时要求和
模型 manifest。取值源于 L0a evidence，锁文件与证据漂移时拒绝，升级需同步 ADR/证据。
`schemas/harness-lock.schema.json` 检查其字段和类型。

`configs/schema.json` 定义版本 1 配置，所有对象拒绝未知字段。初始 preset 使用
JSON 文件 `configs/local-hermes.json`，模式为 mock。模型连接只允许 IPv4 loopback，
端口为 1–65535 的整数，API path 固定 `/v1`；后续适配器据此组装 endpoint。
配置中的 `source_commit` 必须匹配锁文件。Ollama 模式另要求模型名称、端口 11434、
上下文和输出上限与已接受锁文件一致。mock 模式保留可选端口和合成模型名。

调用次数 1–4、超时 1–120 秒、并发固定 1。上下文不少于 64000，输出上限 512，
且输出严格小于上下文。synthetic 固定 true，capture_body 默认 preset 为 false，
只有显式 true 才授权后续合成调试采集。凭据不属于此配置，未知凭据字段直接拒绝。

## 校验入口与错误行为

独立校验工具在 macOS arm64 / Python 3.13 验证，使用哈希锁定的 jsonschema 依赖。
依赖清单包含该平台及 CI 的 Linux x86_64 wheel，新增平台哈希须独立审核。Hermes 的 Python
3.14 要求由运行时步骤处理。命令依次检查锁文件 schema、L0a 证据一致性、配置
schema 和跨文件约束，通过返回 0，失败返回 1 并显示字段路径。错误信息显示字段
和失败规则，隐藏字段值，防止误填凭据进入日志。重复 JSON key、非标准 NaN/Infinity
和无法解析的 JSON 均拒绝。相对配置路径按调用者 cwd 解析，内置 schema/证据路径
从脚本所在仓库定位，支持从其他目录执行。

## 验证与后续

L00 用临时负面 fixture 覆盖缺模型、端口越界、非完整 commit、未知字段、外部地址、
锁文件漂移、重复 key、JSON 语法错误和模式约束；正例覆盖 mock 与已锁定 Ollama
配置。测试同时检查退出码和字段错误，并断言校验路径无网络调用。

后续事件契约由 L05 单独交付，检查入口/CI 属于 L04/L06，Hermes 实际采集探针属于
L02。本切片仅将配置契约固定为这些步骤的输入，运行时仍需执行沙箱与隐私门禁。
