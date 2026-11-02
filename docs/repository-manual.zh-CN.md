# Agent OS 仓库使用手册

本手册适用于 `jolearningusa/agent-os`，面向开发者和 coding agent。
它描述仓库使用与协作流程，不是已上线产品的用户指南。

## 仓库当前能做什么

截至 2026-11-01，本次分支所基于的主干仅有研究、参考架构与开发规范，尚无
可启动的应用、依赖清单、数据库、测试套件或 CI workflow。不能使用其他仓库
的课程检查命令，也不应声称已能运行医疗 Agent。

研究与后续设计在 PR 中评审。未合并 PR 的内容不能当成主干已经具有的能力。
本手册独立于医疗设计 PR，可先后任意合并，不依赖其新增文件。

## 首次使用

需要 Git。若通过命令行管理 PR，还需要 GitHub CLI (`gh`) 并登录有权限的账号；
也可通过 GitHub 网页提交 PR。当前阅读文档不需要 Node、Python 或模型 API key。

在父目录执行一次克隆，已有 checkout 不要再次覆盖克隆：

```sh
git clone https://github.com/jolearningusa/agent-os.git
cd agent-os
git rev-parse --show-toplevel
git remote -v
git status --short --branch
```

确认仓库根目录确实是 `agent-os`，origin 指向目标仓库。若 Git 意外识别为父目录
仓库，先检查 `.git` 所在位置，不要在错误仓库中 commit 或 pull。

有本地改动时先判断归属，保留或提交自己的内容；不使用强制重置、清理或 stash
来掩盖他人的工作。未跟踪的系统文件如 `.DS_Store` 不应加入提交。

## 文档地图与优先级

- [README](../README.md)：项目入口。
- [AGENTS.md](../AGENTS.md)：coding agent 必须遵循的工程规则。
- [landscape](research/agent-os-landscape.md)：产品/架构方向的当前来源，直到被
  明确接受的新设计替代。
- [参考架构](research/agent-os-reference-architecture.md)：组件、任务生命周期、
  记忆、检索、部署和评测边界。
- [开发工作流](development-workflow.md)：设计、验证、PR 和完成定义的详细规则。
- [中文 Git 流程](git-workflow.md)：主干开发操作与 GitHub 设置要求。
- [PR 模板](../.github/pull_request_template.md)：提交说明、验证与 Prompt history。

行为、公开接口、隐私、权限、持久化或部署变更先更新设计，再实现；同一个变更中
保持文档、代码、示例与配置一致。设计草案必须标记待评审，不能悄悄覆盖已接受契约。

## 开始一个任务

先阅读 AGENTS.md 与相关设计，并检查 GitHub 的开放 PR，避免文件归属冲突。
主干干净后获取并快进，然后创建一个短期分支：

```sh
git fetch origin main
git switch main
git merge --ff-only origin/main
git switch -c docs/describe-current-task
```

`docs/describe-current-task` 是示例，请换成实际任务名。Agent OS 使用
`feature/*`、`fix/*`、`hotfix/*`、`refactor/*`、`test/*`、`docs/*`、`chore/*`；
会话已明确指定分支名时优先使用该名称。无需使用课程仓库的分支类别。

`--ff-only` 失败表示本地主干发生分叉，应调查原因，不能 force-push 或 reset
丢弃内容。main 上不写功能、不修复、不直接推送。

通常一次只交付一个 PR，目标是一个可评审意图；分支尽量一至两个工作日合并。
只有用户明确请求且工作真正独立时，才允许同时存在独立 PR；它们分别从最新
main 创建，文件归属不重叠，不能依赖另一 PR 的未合并契约。

## 实施时必须保持的边界

模型可以提出动作，可信策略和执行服务负责授权与副作用。外部 harness 作为
可替换适配器，项目拥有模型、工具、授权、隐私、检索、记忆、持久化和评测接口。

私有数据经过 Privacy Gateway 和 Token Vault，检索授权发生在内容进入上下文前。
生产自我改进只能离线候选、评测、审核、阶段发布与回滚。源码、fixture、普通日志、
提示样本、PR 和评测集不得包含真实个人信息或凭据。

新增行为提供有意义的成功与失败测试，重点覆盖授权、租户隔离、重试、恢复和
副作用；持久化变更补充兼容迁移和回滚方案。

## 提交前与推送前验证

当前只有 Markdown 文档，至少执行：

```sh
git diff --check
git diff --stat
git diff
```

新文件需单独阅读；`git diff` 不包含未跟踪文件。检查相对链接存在、代码围栏闭合、
示例命令与真实仓库一致、无敏感内容。Mermaid 如未渲染，应在 PR 中说明。
未来应用骨架必须提供一个根命令（优先 `make check`），CI 使用同一验证入口；
在命令建立前逐项运行实际已有检查，明确报告缺少的条件，不虚构通过结果。

只暂存本次拥有的明确文件，检查暂存差异后提交：

```sh
git add docs/the-file-you-changed.md
git diff --cached --check
git diff --cached
git commit -m "docs: explain the current task"
```

上面的文件名是占位示例，不是仓库已有文件；替换后再执行。

**每次 push 前重新检查 PR 状态**，不能沿用几分钟前的结论：

```sh
gh pr view --repo jolearningusa/agent-os --json number,state,mergedAt,headRefName
```

首次创建的分支可能没有 PR，可在 GitHub 页面或 `gh pr list --state all --head`
加实际分支名确认。PR 已合并时禁止继续推送旧分支；保存未交付改动，从最新 main
创建新分支，仅迁移剩余变更。PR 已关闭但未合并时调查原因，不自动新建替代 PR。

确认可以继续后：

```sh
git fetch origin main
git rebase origin/main
git diff origin/main...HEAD --check
```

解决冲突并重新运行受影响检查后，推送实际分支。若变基导致远端历史分歧，先确认
分支归属和远端最新提交；只有需要且有适当授权时才使用带期望值保护的
`--force-with-lease`，不默认覆盖其他会话的提交，绝不 force-push main。

## 创建 PR 与 Prompt history

以 `main` 为 base，优先 Draft，应用与内容相符的标签。按模板写清范围、设计、
隐私/安全、测试、运维、迁移、回滚和限制。文档改动通常使用 `documentation`。

Prompt history 引用促成 PR 的用户请求并标注用户所在时区的日期，列出遵循的
AGENTS.md、工作流及额外指令。只保留必要上下文，敏感内容删去并标明。

命令行示例（先将按模板完成的说明保存到本地文件）：

```sh
git push -u origin docs/describe-current-task
gh pr create --repo jolearningusa/agent-os --base main --head docs/describe-current-task --draft --title "docs: describe current task" --body-file /tmp/agent-os-pr.md --label documentation
```

多行说明使用文件传入，避免 shell 转义破坏正文。GitHub connector 权限不足时可
使用有授权的 gh 或网页；不能将权限不足误认为已完成创建。

## 评审、合并与清理

同一 PR 修复 CI 和评审问题，不新建 PR 绕过失败。相关检查通过、分支最新且讨论
解决后再 ready。仓库无 CI 时如实说明“未配置”，不能说“CI 绿灯”。

只有用户明确授权当次合并，才执行 squash merge；提交 PR 不等于授权合并。
确认合并后核实远端分支已自动删除，没有自动删除时再手动处理。随后：

```sh
git fetch origin main
git switch main
git merge --ff-only origin/main
git branch -d docs/describe-current-task
```

squash 后 Git 可能无法通过祖先关系确认分支已合并。若 `-d` 拒绝，先核对 PR 的
merged 状态、远端最终 head SHA、本地分支 SHA 和工作目录；确认没有未交付提交
后才可使用 `-D` 删除该已合并本地分支，不能直接照抄强制删除。

完成同步和清理后再进入下一依赖任务。GitHub 设置要求见中文 Git 流程，文档中的
要求不代表远端 ruleset、自动删除或 CI 已配置。
