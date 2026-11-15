# ADR 0001 Hermes 本地实验的 L0a 决策

日期：2026-11-15。状态：已形成决策与验证证据，待本 PR 评审接受。
适用范围为单机、单用户、人工合成输入的本地 Harness 实验。

## 执行顺序与边界

接受本 ADR 后执行 L0b 的 mock 采集探针，随后按 L1–L5 交付。
医疗 M0–M9 的临床、权限、预算与发布验收仍独立执行。Hermes 在实验中承担运行与
上下文研究功能，项目自有配置、事件和业务接口作为后续集成边界。

本 PR 将 L0a 的文件与网络探针入库。L0b 负责实际依赖安装和 Hermes 模拟会话，
L2 才验证真实 Ollama 调用。源码检查、平台 canary 和运行时测试分别留证。

## 固定源码、许可证与供应链

沿用已有组织 fork `jolearningusa/hermes-agent`，上游为 `NousResearch/hermes-agent`。
固定提交 `557254faa24ef5d86f67595c4c64dc61644d0f68`，当前本地补丁清单为空。
选择已有 fork 的可获取提交作为复现起点，后续安全更新经独立 PR 和探针回归后升级。

[源码清单](../evidence/l0a-source-inventory.json) 记录 LICENSE、pyproject、uv.lock、
package-lock 和运行时版本文件的 SHA-256。固定提交已从 fork 检出，工作树干净。
MIT 许可中的版权和许可声明随复制分发保留；依赖与模型许可证独立核对。
固定提交文件见 [fork LICENSE](https://github.com/jolearningusa/hermes-agent/blob/557254faa24ef5d86f67595c4c64dc61644d0f68/LICENSE)。

复核源码时可从仓库根目录执行以下只读获取步骤，再按源码清单逐项计算 SHA-256：

```sh
umask 077
mkdir -p .local/harness-lab
git clone --filter=blob:none --no-checkout https://github.com/jolearningusa/hermes-agent.git .local/harness-lab/source
git -C .local/harness-lab/source checkout --detach 557254faa24ef5d86f67595c4c64dc61644d0f68
```

Python 依赖使用上游 `uv.lock`，安装采用 Python 3.14、`uv sync --frozen --no-dev`，
先使用核心依赖，工具或 UI extras 按实际需要逐项审核。锁文件包含 356 个包、3587 个
sdist/wheel 记录，所列 artifact 均带 SHA-256。Node UI 延后至 L4，采用上游 Node 26
和 `npm ci`；1376 个 resolved package 均有 integrity。L0b 安装前固定 uv 与 Python
下载产物的版本/校验值，L4 对 Node 同样处理。锁文件语法和哈希已检查，实际安装、
平台 wheel 可用性和生命周期脚本审计在对应安装 PR 验证；禁止隐式重写锁文件。

本仓库维护者负责每周查看上游安全公告及依赖更新，patch 清单记录目的、提交和
上游关联。严重问题暂停受影响实验，升级后重跑 L02。安装期允许下载到专用目录，
运行期使用固定产物，自动插件、技能安装和后台模型发现须由 L0b 检查并关闭。

## 目标机器与模型

本机实测 macOS 14.4.1、arm64、Apple M2、8 GiB 统一内存。Python 3.13.0、Node
20.13.1 已存在，但低于所选上游运行时要求，L0b 在独立环境安装 Python 3.14；
系统解释器保持现状。uv 与 Ollama 当前缺失。

真实模型 smoke preset 选择 `qwen3.5:0.8b`，manifest SHA-256 为
`de63045f29755d4721c09d54c9b45c2dadb644f4fd7d604d4cac90d96049971c`。
注册表清单列出的 config/layer 合计 1,322,069,277 字节，尚未下载权重。模型来源页
提供 Apache 2.0 许可入口，L2 下载后核对本地 manifest、blob digest 和许可。
标签发生变动时拒绝静默替换，改用新的显式版本决策。[模型来源](https://ollama.com/library/qwen3.5:0.8b)

模型选择依据为当前 8 GiB 机器的低权重体积。配置真实上下文 64,000、输出最多 512，
单并发、最多 4 次调用、每次超时 120 秒。固定 Hermes 源码的
`agent/model_metadata.py` 定义 `MINIMUM_CONTEXT_LENGTH = 64_000`，因此不能仅修改
声明值绕过实际容量检查。内存峰值、工具调用、64K 分配及实际模型效果均待 L2 测量。
容量不足或失败时保持 blocked，再评估更大本地机器或新模型，不自动切换云端。
Ollama 的容量必须由服务配置并通过运行状态复核。[容量配置](https://docs.ollama.com/context-length)

主请求和摘要等辅助请求统一指向 `http://127.0.0.1:11434/v1`。首个 L0b 会话使用
mock endpoint，不安装或加载模型权重。真实模型仅用于合成连通与行为观察，医学
有效性需要专门评测。

## 运行方式与网络 canary

Docker CLI 28.4.0 存在，但 daemon 不可连接，启动 Docker 应用失败。选择本机
macOS Seatbelt 进程沙箱作为 L0b 的验证路径，后续正式运行方式仍以 L02/L36 结果为准。
基础 Python/Node 在沙箱外安装到独立环境，执行 Hermes 及其子进程时继承沙箱。

本次使用 `sandbox-exec` 执行最小 socket client，父进程先创建两个真实 loopback
监听端口。profile 拒绝全部网络，只放行 `remote ip "localhost:<允许端口>"`。
该系统接受 localhost 语法，直接使用 127.0.0.1 的 policy 语法会被拒绝。

结果为允许端口连接成功，另一监听端口与保留测试网地址 192.0.2.1 的连接返回
EPERM/EACCES，阻断监听器未收到连接。只有超时或 connection refused 会判为
inconclusive 并失败，防止把服务不可用误判为隔离成功。
[本次结果](../evidence/l0a-network-macos.json)

从仓库根目录复跑：

```sh
python3 scripts/check_l0a_network.py
```

探针使用动态本地端口，退出时关闭监听器及临时 policy。证据限于网络 canary，
未运行 Hermes/Ollama，未验证 DNS、Unix socket/IPC 代理路径、文件边界或完整子进程
树。L0b/L23 必须继续验证这些可能的绕行路径，L36 实测文件与工具限制。
当前 canary profile 的 `(allow default)` 仅用于单个合成 socket client，正式 Harness
profile 需要受限文件访问与 IPC 规则，不能直接把 canary profile 当作生产运行配置。

L0b 为 mock server 开放唯一端口，L2 为 Ollama 开放唯一端口，DNS 与其他出站保持
关闭。mock server 和 Ollama 是边界外可信依赖，Ollama 运行本地权重并关闭云端路径；
L23 验证服务本身及 Harness 全链路。发现绕行或运行方式不兼容时保持对应门禁
blocked。备选为具备强制出站策略的 Linux 容器/VM；切换平台须另记 ADR 并重跑探针。

## 数据、正文调试与清理策略

数据根目录固定 `.local/harness-lab/<instance-id>/`，Git 忽略规则已加入。
目录权限 0700、文件 0600，进程 umask 0077。fixture 是人工合成内容，只读挂载；
写入限定实例目录及临时目录。禁止挂载宿主 home、凭据或容器 socket。
L36 在真实执行环境验证授权与拒绝行为。

正文采集默认关闭，只允许显式启用 synthetic-debug，启动时记录该模式及配置 hash。
日志记录引用、状态和用量，凭据在入库前过滤；临时环境不继承用户提供方密钥。
关闭消息平台、插件、外部工具和自动学习写入，后续仅注册本仓库 fixture 工具。

本地 session、事件、日志、派生缓存及导出统一保留 7 天。启动/退出/每日清理时检查
到期数据；应用停止期间无后台删除服务，重启后先清理再提供读取。用户可主动删除
session，传播至相关正文和缓存；清理失败停止该实例并报告。单实例调试数据上限
512 MiB，写入失败或到达配额停止采集并标记 incomplete。既有用户其他文件不纳入清理。
配额、权限、自动清理及过滤的执行代码在 L1/L3 实现，本次固定其合同。

查看器采用终端短时配对码建立 HttpOnly/SameSite cookie。配对码有效期 5 分钟，
最多 5 次失败后作废；CSRF token 单独绑定会话。退出/重启使会话失效，命令行凭据
独立校验。验收按 L43/L44 执行。

## 评测、状态与接受记录

L54 测量预登记每组 N=5 对、预热 1 次、交替运行顺序、每对恢复相同初始会话，
缓存条件单独记录。结果为探索性样本，延迟从提交到完整响应，事件落盘耗时独立报告。

L01 的源码检出、许可证与锁文件清单已完成，实际依赖安装继续由 L0b 验证。
L03 的隐私与顺序决策已成文。平台最小 canary 已通过。L0a 评审记录由本 PR 的
review/合并记录提供，评审接受前里程碑状态为待评审，不勾选完成。

尚未完成的运行工作为 Python/uv 安装、完整沙箱、L02 采集探针及 Ollama/模型部署。
这些分别归属 L0b/L1/L2/L3。L0a 决策被评审接受后可开始 L0b，遇到完整隔离或采集
失败按既有门禁停止并记录 blocked。回滚本 PR 可还原文档与探针，无安装和用户数据迁移。
