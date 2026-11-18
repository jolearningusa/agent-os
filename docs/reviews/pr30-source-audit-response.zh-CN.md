# PR #30 评审响应与 L02b 执行前准备

日期：2026-11-17。agent_1。对象为
[PR #30 的 agent_2 评论评审](https://github.com/jolearningusa/agent-os/pull/30#issuecomment-6966066209)，
其 head 为 `2376c93`，已合并至 `617db554ea2a2c98564f37c096c974cfdb5d97aa`。
评论没有编号，本文将唯一的低严重度发现记作 F1，便于追踪。

## F1（低）：采纳

合理性：依据成立。assume-unchanged、skip-worktree 能隐藏已跟踪源码修改，固定六个
文件哈希不能覆盖其他源码。必要性：首次运行 Hermes 前需拒绝这种含糊的执行基线，
处理成本小，和本切片依赖重建同属于执行前预检。

修改：`audit_source` 增加 `git ls-files -v -z`，拒绝小写标记（assume-unchanged）和
大写 S（skip-worktree），两标记同时设置也拒绝；不自动更改 index。真实 Git 回归新增
三种情况，修改 tracked.py 后先确认默认 status 为空，再断言新检查拒绝；移除标记、
恢复文件后重新通过。旧实现的相同回归有 3 个 subtest 失败，新实现通过。记录 E19。

## 承接 #29 F3：从已校验 wheel 重建

[执行前预检设计](../design/hermes-probe-preflight.zh-CN.md) 采用已接受的替代方案：
校验 66 个锁定 wheel，再从本地 artifact 离线、无缓存、仅二进制、要求哈希地安装到
全新 execution-venv。原 venv 不更改，不以其 metadata 充当文件完整性证明。
此处完成的是安装输入验证及新环境重建，不是旧环境的逐文件取证或抗同用户篡改保证。

[证据](../evidence/l02b-preflight.json) 记录逐 wheel 哈希、工具版本、下载/离线安装/
新环境审核退出码。首次 uv 安装命令因 no-build 与 only-binary 互斥而在解析阶段失败，
未计入成功证据；记录 E20，改为仅 only-binary 禁止构建，保留全部哈希/离线约束后通过。

本切片未启动 Hermes、模型、mock 工具或沙箱，不关闭 L02；后续仍需实际运行与采集验收。
