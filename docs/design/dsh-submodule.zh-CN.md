# DeepSeek Harness 子模块设计（待评审）

## 背景

Agent OS 已在医疗 Agent 设计和可行性评审中引用 DSH 的调用生命周期与模型流式契约
作为参考。此前引用指向 upstream `deepseek-ai/deepseek-harness` 的 `master` 分支，
未固定 commit，存在引用漂移风险。本切片将 fork `jolearningusa/deepseek-harness`
作为 git submodule 引入仓库，并通过 `dsh.lock.json` 固定 commit、源码哈希与许可证，
使引用可复现、可审计。

## 决策

### 为什么用 submodule

DSH 是一个大型 TypeScript monorepo，通过 pnpm workspace 管理。直接复制源码会
造成维护负担和同步困难。Submodule 保持了 DSH 的完整构建链和测试套件，同时允许
Agent OS 在 fork 上进行适配实验，不影响 upstream。

### 为什么用 fork

upstream `deepseek-ai/deepseek-harness` 处于活跃开发中，developer preview 阶段
明确会有 breaking changes。fork `jolearningusa/deepseek-harness` 允许 Agent OS
在需要时固定一个已审核的快照，或在不等待 upstream 的情况下进行适配修改。这与
Hermes 的 fork 策略一致。

### 为什么放在 vendor/dsh

- `vendor/` 目录明确标识为第三方依赖，与项目自有代码分离。
- `dsh` 使用仓库通用简称，与文档和社区约定一致。
- 与 `.local/harness-lab/`（运行时私有数据）不同，`vendor/` 是版本控制的源码引用。

## 子模块契约

### 锁文件

`dsh.lock.json` 固定以下信息：

| 字段 | 值 |
|---|---|
| `upstream` | `https://github.com/deepseek-ai/deepseek-harness.git` |
| `fork` | `https://github.com/jolearningusa/deepseek-harness.git` |
| `commit` | `ce7073d51254c26cd63b22a60835b8f948deb447` |
| `branch` | `master` |
| `license` | MIT |
| `submodule_path` | `vendor/dsh` |

源码文件 SHA-256 包括 `LICENSE`、`package.json`、`pnpm-lock.yaml`、
`pnpm-workspace.yaml`、`tsconfig.json`、`tsconfig.base.json`、`tsdown.config.ts`、
`Makefile`、`AGENTS.md`、`SAFETY.md`。这些文件覆盖许可证、构建配置、测试入口和
安全说明，足以验证子模块完整性。

### Schema

`schemas/dsh-lock.schema.json` 定义版本 1 锁文件结构。所有对象拒绝未知字段。
`patches` 数组允许记录 fork 相对 upstream 的修改文件和描述；当前为空数组，
表示 fork 与 upstream 在该 commit 无差异。`patches` 是结构化数组而非 `const: []`，
因为 fork 后续可能需要适配补丁。

### .gitmodules

```ini
[submodule "vendor/dsh"]
    path = vendor/dsh
    url = https://github.com/jolearningusa/deepseek-harness.git
```

## 边界

### 不做什么

- **不运行 DSH。** 本切片仅引入源码引用，不安装 Node、不执行 `pnpm install`、
  不启动 Web UI 或 headless 模式。运行时集成属于后续切片。
- **不 fork DSH 核心。** 与 Hermes 策略一致：先通过 plugins、hooks、MCP 和配置
  集成；fork 核心是最后手段。
- **不将 DSH 作为 Agent OS 的公共契约。** DSH 是可替换适配器，项目自有接口
  （Privacy Gateway、Token Vault、Policy Engine 等）不依赖 DSH 的内部 API。
- **不在源码、fixture 或日志中放置真实凭据。** DSH 的 `.dsh/.credentials.yaml`
  不属于本仓库。

### DSH 的角色

DSH 在 Agent OS 中有两个参考角色：

1. **调用生命周期参考** — DSH 的 `docs/agent-lifecycle.md` 和
   `docs/subsystems/llm-streaming.md` 已在医疗 Agent 设计中作为调用控制点参考。
   引入子模块后，这些文档可在本地 `vendor/dsh/docs/` 直接阅读。
2. **插件架构参考** — DSH 的"一切皆插件"（Cordis 内核）设计是 Agent OS
   能力平面（Capability plane）的参考实现之一。项目可在配置层选择、替换或
   扩展能力，而不修改 DSH 源码。

## 安全考量

- DSH 的 `SAFETY.md` 明确了沙箱、权限和执行边界。Agent OS 的隐私网关和策略引擎
  是独立的信任边界，不依赖 DSH 的内置安全机制。
- DSH 的 telemetry 默认排除 raw prompt 和 response 内容，这与 Agent OS 的
  "content-free telemetry by default" 原则一致，但仍需独立配置 Agent OS 的
  出站隐私 hook。
- 子模块引入不增加 Agent OS 的攻击面：`vendor/dsh` 不参与 Agent OS 的 Python
  校验工具链，不被 `check_harness_config.py` 加载。

## 验证

### 子模块完整性

```sh
git submodule status vendor/dsh
git -C vendor/dsh rev-parse HEAD
```

两个命令的输出应匹配 `dsh.lock.json` 中的 `commit` 字段。

### 锁文件校验

锁文件的 JSON Schema 校验复用 Hermes 锁文件的相同工具链（`jsonschema` +
`Draft202012Validator`）。后续切片可扩展 `check_harness_config.py` 或新增独立
脚本来校验 DSH 锁文件。

当前可手动验证：

```sh
.local/harness-lab/config-check-env/bin/python -c "
import json
from pathlib import Path
from jsonschema import Draft202012Validator
schema = json.loads(Path('schemas/dsh-lock.schema.json').read_text())
lock = json.loads(Path('dsh.lock.json').read_text())
Draft202012Validator.check_schema(schema)
errors = list(Draft202012Validator(schema).iter_errors(lock))
print('PASS' if not errors else errors)
"
```

### 源码哈希验证

```sh
cd vendor/dsh
sha256sum LICENSE package.json pnpm-lock.yaml pnpm-workspace.yaml \
  tsconfig.json tsconfig.base.json tsdown.config.ts Makefile AGENTS.md SAFETY.md
```

输出应匹配 `dsh.lock.json` 中 `source_files_sha256` 的对应值。

## 后续

- **L-dsh-1**：在 `check_harness_config.py` 或新脚本中添加 DSH 锁文件和子模块
  commit 一致性校验。
- **L-dsh-2**：评估 DSH 作为 Agent OS 执行平面的适配器可行性，定义项目自有
  `AgentRuntime` 接口到 DSH 插件系统的适配契约。
- **L-dsh-3**：DSH 运行时环境搭建（Node >= 24.9.0、pnpm、Docker 沙箱）和
  合成实验配置。
