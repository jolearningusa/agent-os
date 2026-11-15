# PR #15 L0a 产出检查报告

检查日期：2026-11-15。基于 main `bc04da9`，对照已合并的
[PR #15](https://github.com/jolearningusa/agent-os/pull/15) 与
[交付计划](../plans/local-harness-deliveries.zh-CN.md) 中 L0a 的要求。
本次独立复算 PR 声称的证据，未安装 Hermes 依赖、未下载模型、未运行 Ollama，
也未验证 Docker daemon 状态，这些不在结论范围内。

## 结论

**L0a 产出符合预期，可以进入 L0b，没有阻塞项。** 声称的源码、哈希、网络 canary
和模型 manifest 证据均复现通过。有 2 处声明措辞不够准确、2 处供应链与平台风险
需在 L0b 前后处理，以及若干状态措辞问题，见“发现”。

## 逐项核对

| 项目 | PR 声称 | 本次结果 |
| --- | --- | --- |
| fork 与提交 | 组织 fork，固定 `557254fa…`，MIT | 提交存在；仓库为 `NousResearch/hermes-agent` 的 fork，GitHub 识别许可证为 MIT |
| 源码哈希 | 6 个文件 SHA-256 | 从固定提交取回 6 个文件，哈希与 `l0a-source-inventory.json` 全部一致 |
| 运行时要求 | Python 3.14、Node 26 | `.python-version` 为 3.14，`.nvmrc` 为 26 |
| `uv.lock` | 356 包、3587 个 artifact 均带哈希 | 356 个包；3587 个 sdist/wheel，缺哈希 0 个 |
| `package-lock.json` | 1376 个 resolved 均有 integrity | 1376 个 resolved，其中 1369 个有 integrity，见 F1 |
| 容量检查 | `MINIMUM_CONTEXT_LENGTH = 64_000` | 固定提交 `agent/model_metadata.py` 第 274 行一致 |
| 模型 manifest | SHA-256 `de63045f…`，合计 1,322,069,277 字节 | 从注册表重新取回，哈希一致；config 与各 layer 合计 1,322,069,277 |
| 网络 canary | 允许端口通，另一监听端口和 192.0.2.1 被拒 | 复跑通过：允许端口 connected，其余 denied，阻断监听器未收到连接 |
| 私有目录忽略 | `.local/harness-lab/` 被忽略 | `git check-ignore` 命中 `.gitignore` 第 2 行 |
| 文档检查 | 链接、空白、围栏、JSON | 全部 docs 与 README 通过；验收 ID 36 个且唯一 |
| 验收项 | L01、L03 证据 | L01 源码与锁文件清单、L03 隐私与顺序决策均已成文；与计划一致 |

canary 脚本只创建本地监听端口并调用 `sandbox-exec`，不访问公网，已读完再运行。

## 发现

### F1：npm integrity 声明不准确（低）

ADR 与 PR 写“1376 个 resolved package 均有 integrity”。实际 1369 个带 integrity，
另 7 个是本仓库内的 workspace 链接（`apps/*`、`ui-tui`、`web` 等），本就没有
integrity。这不是缺陷，但措辞应改为“1369 个外部包均有 integrity，另有 7 个本地
workspace 链接”。该项影响 L4 的 Node 安装，对 L0b 无影响。

### F2：`uv.lock` 有不受 artifact 哈希覆盖的来源（中）

“所列 artifact 均带 SHA-256”成立，但锁文件还有 3 个非注册表来源：
`misaki` 与 `psutil` 来自 Git，只固定到提交；`kittentts` 是直链 wheel。它们是否在
核心安装集合里，ADR 没有说明。Git 来源在安装时需要联网构建，也不适用
“artifact 哈希”这一保证。建议 L0b 安装前确认这 3 项是否属于 `--no-dev` 核心依赖；
若属于，记录其提交或 URL 校验方式，或在核心集合中排除。

### F3：Seatbelt 路径的平台风险（中）

- ADR 选择 `sandbox-exec` 作为 L0b 验证路径。该命令在 macOS 中长期被标记为弃用，
  ADR 没有提及，也没有写系统升级后失效时的处理。
- canary 只覆盖 TCP 连接，profile 使用 `(allow default)`。ADR 已承认这一点，也已写明
  DNS、Unix socket/IPC、文件边界待 L0b/L36 验证。这是诚实的范围声明，本项只是提醒：
  现有 `pass` 证据不能引用为 L23 或 L36 的任何部分。
- Docker daemon 不可用，因此 Linux 容器备选路径尚无证据。

### F4：状态措辞已过时（低）

- ADR 状态写“待本 PR 评审接受”，PR 已合并，且合并时无任何 review 记录。
- 计划的 L0a 复选框仍未勾选，写“待 PR 评审接受”。
- 建议加一条明确的接受记录，写明接受人和日期，之后再勾选 L0a。

### F5：维护负责人未具名（低）

计划要求在 L0a 指定上游维护负责人，ADR 写的是“本仓库维护者”，没有具体人。
每周检查安全公告需要有人负责，建议补上姓名或角色。

### F6：证据文件缺少可追溯元数据（低）

`l0a-network-macos.json` 没有记录脚本的哈希或提交、运行时间。日后复核时无法判断
结果对应哪一版脚本。建议加入脚本 SHA-256 与运行时间字段。

### F7：8 GiB 机器上的 64K 上下文未经验证（信息）

ADR 已标注“内存峰值、64K 分配待 L2 测量”，本次不判断可行性。补充一点：注册表
manifest 里除模型权重外还有 projector（约 207 MB）和 draft（约 303 MB）两个 layer，
实际占用可能高于“约 0.8B 权重”的直觉，L2 测内存时应一并记录。

### F8：README 格式（极低）

PR #15 在 README 的列表中间插入了一个空行，把同一小节的链接拆成两段。无功能影响。

## 与计划的对照

计划对 L0a 的要求是 ADR 固定平台、fork/commit、许可证、模型与硬件、运行方式和
隐私策略，并先验证出站白名单能否实现，且无法强制时要标注缺口。以上 ADR 均已覆盖，
平台缺口也已明确标注。尚未完成的是计划中本来就属于 L0b 之后的工作：依赖安装、
完整沙箱、L02 采集探针、模型下载。本次不视为缺失。

## 建议

1. 小 `docs/*` PR 处理 F1、F4、F5、F6、F8，并在 ADR 补充 F2、F3 的说明。
2. 然后开始 L0b。L0b 的第一步先确认 F2 的 3 个非注册表依赖是否在核心安装集合，
   并评估 `sandbox-exec` 弃用对备选路径的影响。
3. L0b 的探针通过之前，不要用现有 canary 证据声明任何完整隔离。
