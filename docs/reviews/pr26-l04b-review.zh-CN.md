# PR #26 L04b 评审报告

评审日期：2026-11-16。评审人：agent_2。评审基线：PR head `e5e5b90`，合并前 main
`e42023d`；PR 已由评审方合并为 `1ccb0f4`。对象：
[PR #26](https://github.com/jolearningusa/agent-os/pull/26)，agent_1 交付的 L04b
（GitHub Actions 执行同一 `make check`）及其对 #25 评审的响应。

本次未运行 Hermes、Ollama 或任何模型，未修改仓库设置，也未把检查设为 required
status。该 PR 涉及 15 个文件并新增 CI 工作流，超出评论评审的小 PR 范围，因此写成
报告；合并依据已在 PR 评论中记录。

## 结论

**符合 L04b 的验收口径，无阻塞项，已合并。** CI 与本地使用同一入口，权限最小，依赖
与 Action 均已固定，失败与恢复有真实运行证据。另有 2 条低严重度和 2 条信息级发现。

## 逐项核对

| 项目 | PR 声称 | 本次结果 |
| --- | --- | --- |
| 工作流权限 | 只读，`pull_request`，无 secrets | `permissions: contents: read`；未用 `pull_request_target`；checkout 关闭凭据持久化与 submodule；无 secrets 或部署环境 |
| Action 固定 | checkout、setup-python v6 固定 SHA | 两个 SHA 经 GitHub API 核对，分别等于官方 `v6` 标签指向的提交 |
| 依赖哈希 | `--require-hashes --only-binary` | jsonschema、attrs、jsonschema-specifications、referencing 的哈希与 PyPI 元数据一致且为纯 Python wheel；rpds-py 两个哈希对应 `cp313` macOS arm64 与 `manylinux x86_64` wheel，均未撤回 |
| 证据文件 | 工作流与依赖哈希、run 记录 | 工作流和 `requirements-config.txt` 的 SHA-256 与 PR head 重算结果一致 |
| 负例 | run 43829356196 在 `Run make check` 退出 2 | 实查：依赖准备成功，`Run make check` 失败，后续步骤未算通过 |
| 恢复 | run 43829777024 成功 | 实查：成功，30 项测试 |
| 最终 head | run 43830234779 成功 | 实查：成功；PR 状态为 SUCCESS，与 head `e5e5b90` 对应 |
| 首次失败 | 43828953269 为 YAML 解析失败，不计入证据 | 实查：无 job；正确排除，已记 E14 |
| 本地检查 | `make check` 通过 | 28 份 Markdown、91 个验收 ID、30 项测试、语法编译均通过 |
| #25 F1 的修复 | 行内代码限定在同一段落 | 重新探测：跨段落落单反引号、仅含空白的空行、多行代码跨行、行内示例，均符合预期 |

## 发现

### F1：协作规范中出现重复编号（低）

为修 #25 的 F2，`docs/agent-collaboration.zh-CN.md` 新增的“汇总格式”编号为 7，下一条
“记录 PR 走正常流程”原本也是 7，源文件里有两个第 7 条。渲染后顺序正常，但源文件
编号重复，也与 L06 脚本“不让文档不一致”的目标不符。建议后一条改为 8。

### F2：`cancel-in-progress` 对 main 也生效（低）

`concurrency` 设为 `cancel-in-progress: true`，分组为 `checks-${{ github.ref }}`。
对 pull_request 合理，但 main 上连续两次 push 时，后一次会取消前一次仍在运行的检查，
一个失败的提交可能没有留下结果。建议只对 PR 取消：
`cancel-in-progress: ${{ github.event_name == 'pull_request' }}`。

### F3：required status 仍待授权（信息）

检查成为 required status 属于仓库设置，作者已在描述中写明需另行授权。这意味着当前
CI 红灯不会阻止合并，只靠评审方核对。建议用户决定何时启用。

### F4：pip 本身未固定（信息）

`pip` 使用 setup-python 自带版本，依赖安装使用 `--require-hashes`，风险有限。如需完全
可复现，可在后续考虑固定 pip 或使用锁定的构建环境。

## 与计划的对照

L04（`make check` 与 CI 执行同一无网络命令，故意破坏后失败、修复后通过）已有真实
远端证据，L06 的 CI 部分一并满足。L0b 整体仍未完成，剩余为 L02 采集可行性探针。
该顺序由用户确认保留（L02 在 L04b 之后）。

## 建议的后续顺序

1. agent_1 评估 F1、F2，可并入 L02 的 PR 或一个小的修订 PR 一并记录。
2. 用户决定是否将检查设为 required status（F3）。
3. 开始 L02 采集可行性探针。
