# Git 主干开发流程

本仓库采用 Trunk-Based Development：只有一个长期分支 `main`，它必须始终处于
可发布状态。日常变更使用短生命周期分支，不建立 `develop`、`staging` 或长期
release 分支。本页与 [开发工作流](development-workflow.md) 及
[AGENTS.md](../AGENTS.md) 保持一致；细化检查与定义以开发工作流为准。

## 标准流程

1. Fetch `origin/main`，确认本地 `main` 干净后 fast-forward；从该验证过的版本
   创建本次任务分支。工程任务使用 `feature/*`、`fix/*`、`hotfix/*`、
   `refactor/*`、`test/*`、`docs/*` 或 `chore/*`。明确指定分支名的 agent 会话
   使用指定名称。
2. 分支尽量在一至两个工作日内合并。大任务拆成兼容的小 PR 或使用显式功能开关；
   一次一个意图，设计变更先于实现。这个时限是交付目标，超时不会触发删除。
3. 每次 push 前确认该分支 PR 状态。若已经合并，不在合并历史上继续提交或推送；
   保存未交付工作，从更新后的 `main` 建立新的短期分支，只迁移剩余变更。
   若未合并，fetch 最新 `origin/main` 并 rebase，运行所有相关本地检查。
4. 按 [.github/pull_request_template.md](../.github/pull_request_template.md)
   填写目标为 `main` 的带标签 Draft PR。Prompt history 引用用户请求、日期及
   遵循的指令；敏感信息必须删去并标记，不能把患者资料或凭据复制到 PR。
5. 修复 CI 与评审问题，检查通过后才能 ready；只有获得本次用户合并授权后才
   squash merge。单人项目也不绕过 PR 路径，不合并失败的 PR。
6. 确认已合并后删除远端分支：已配置 GitHub 自动删除时由 GitHub 完成；否则
   确认状态后手动删除。随后 fetch、fast-forward 本地 `main`，删除本地主题分支。
7. 完成同步和清理后再开始下一任务。禁止直接 push、force-push 或在 `main` 修复。

**一次只做一个依赖 PR**：当前 PR 合并之前，不从其未合并分支叠加下一任务。
真正独立且用户明确要求的并行交付仍须满足文件与契约隔离；不能绕过依赖顺序。

**多个会话并行**：每个会话只改自己负责的文件，不修改另一个未合并 PR 占用的
文件。无法避免冲突时，等该 PR 合并后再 rebase。

## 清理已合并的远端分支

合并后自动删除只处理触发该次合并的 PR 分支。启用设置后，历史遗留分支仍需逐个核对。
清理前确认 PR 已合并到 `main`，且远端分支当前 SHA 与该 PR 合并时的 head SHA
一致。squash merge 会生成新提交，因此以 PR 记录为准。分支上有后续提交、仍被开放
PR 使用，或找不到对应合并记录时，保留分支并核实归属。禁止删除 `main`。

操作步骤和本地清理命令见 [仓库使用手册](repository-manual.zh-CN.md#评审合并与清理)。

## 本地检查与当前仓库状态

当前 `make check` 已串联文档检查、配置/事件 CLI、全部 unittest 和 Python 语法编译。
先按 README 安装既有校验工具依赖，再运行该命令。独立 formatter、类型检查与应用
构建随对应组件加入；CI 入口为 `.github/workflows/checks.yml`，执行同一命令，
首次远端验证结果记录在本次 PR。

本仓库没有课程、幻灯片或 Pages 构建检查，不复制其他仓库的脚本名与状态检查名。
已有 CI 时新增检查须同步接入；初始统一入口与首次 CI 按 L04a/L04b 连续切片交付，
CI 证据齐备后才关闭完整门禁。不能为了通过检查而跳过、弱化或静默替换已有检查。
文档变更的当前检查方法见
[仓库使用手册](repository-manual.zh-CN.md)。

## GitHub 仓库设置

以下为需要实施/核验的设置要求，本次文档提交不表示远端设置已修改。

在 `Settings → General → Pull Requests`：

- 只启用 **Allow squash merging**，关闭 merge commit 和 rebase merging。
- 勾选 **Automatically delete head branches**，在 PR 合并后删除远端 head 分支。

在 `Settings → Rules → Rulesets` 为 `main` 配置：

- Require a pull request before merging；单人阶段可不要求 review approval，
  但仍禁止直接 push，并保留用户对合并的明确授权。
- Block force pushes、Restrict deletions、Require linear history。
- Require conversation resolution，并要求分支基于最新主干。
- Require status checks to pass：在本仓库 CI 首次成功运行后选取实际作业名称。
  不将不存在的作业配置为必需检查，以免所有 PR 无法合并。

仓库规则集的适用计划/权限、现有必需检查和自动删除状态，需在设置执行时读取
确认。设置变更属于独立的管理操作，不能把本页文字当成设置已经生效的证据。

2026-11-07 通过 GitHub API 核验：`delete_branch_on_merge` 为 `false`，squash、
merge commit 和 rebase 三种合并方式均已开启。拥有仓库管理权限的维护者可在上述
设置中应用目标配置，再用以下只读命令复核：

```sh
gh api repos/jolearningusa/agent-os --jq '{delete_branch_on_merge, allow_squash_merge, allow_merge_commit, allow_rebase_merge}'
```

目标值依次为 `true`、`true`、`false`、`false`。Ruleset 的生效状态须在
`Settings → Rules → Rulesets` 单独核验。
