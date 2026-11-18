# Agent OS

Build and deploy a customizable agent operating system, adapting open-source
agent harnesses where they provide a strong foundation.

This repository's Agent OS is the project documented here. It is not Agno's
AgentOS product. Agno is cited only as an external completeness checklist.

## Research and architecture

- [Agent OS landscape and recommended architecture](docs/research/agent-os-landscape.md)
- [Agent OS reference architecture and component model](docs/research/agent-os-reference-architecture.md)
- [资源感知 Harness：三个产品方案（中文，待评审）](docs/research/resource-aware-harness-options.zh-CN.md)

## Local Harness Lab

- [Hermes 本地实验交付物与里程碑（中文，待评审）](docs/plans/local-harness-deliveries.zh-CN.md)
- [PR #10 评审与改进建议（中文，待评审）](docs/reviews/local-harness-deliveries-review.zh-CN.md)

- [L0a 决策与平台验证 ADR](docs/adr/0001-hermes-local-lab.zh-CN.md)
- [PR #15 L0a 产出检查报告（中文，待评审）](docs/reviews/pr15-l0a-verification.zh-CN.md)
- [PR #26 L04b 评审报告（中文，待评审）](docs/reviews/pr26-l04b-review.zh-CN.md)
- [PR #28 L02a 评审报告（中文，待评审）](docs/reviews/pr28-l02a-review.zh-CN.md)
- [PR #31 L02b 执行前预检评审报告（中文，待评审）](docs/reviews/pr31-preflight-review.zh-CN.md)

当前 L0b 配置契约可独立校验。本地平台为 macOS arm64 / Python 3.13，CI 目标为
Ubuntu x86_64 / Python 3.13.0；两者 wheel 哈希均已固定。以下安装仅用于校验工具环境。

```sh
umask 077
python3 -m venv .local/harness-lab/config-check-env
.local/harness-lab/config-check-env/bin/python -m pip install --require-hashes -r requirements-config.txt
.local/harness-lab/config-check-env/bin/python scripts/check_harness_config.py configs/local-hermes.json
.local/harness-lab/config-check-env/bin/python -m unittest discover -s tests -v
```

CI 配置位于 `.github/workflows/checks.yml`，与本地执行相同入口。
依赖准备后，统一本地检查入口为 `make check`，命令内容见 [文档检查契约](docs/design/document-checks.zh-CN.md)。

字段与失败行为见 [本地配置契约](docs/design/local-harness-config.zh-CN.md)。
事件结构与离线校验见 [上下文事件契约](docs/design/local-harness-events.zh-CN.md)。

## Vendor harnesses

Agent OS references external harnesses as pinned, auditable sources. Each vendor
harness is a replaceable adapter behind project-owned interfaces, not a public
contract.

### Hermes

- Fork: `jolearningusa/hermes-agent` (pinned in `harness.lock.json`)
- Role: experiential learning, skill lifecycle, scheduled tasks reference

### DeepSeek Harness (DSH)

- Fork: `jolearningusa/deepseek-harness` (pinned in `dsh.lock.json`)
- Submodule: `vendor/dsh`
- Role: call lifecycle, model streaming contract, and plugin architecture
  reference for the capability plane
- [DSH 子模块设计（中文，待评审）](docs/design/dsh-submodule.zh-CN.md)

Clone with submodules:

```sh
git clone --recurse-submodules https://github.com/jolearningusa/agent-os.git
```

If already cloned without submodules:

```sh
git submodule update --init --recursive
```

## Medical Agent development

- [医疗 Agent 开发设计（中文，待评审）](docs/design/medical-agent.zh-CN.md)
- [实施步骤与逐项验证计划（中文）](docs/plans/medical-agent-implementation.zh-CN.md)
- [医疗 Agent 设计合理性与可行性评审（中文）](docs/reviews/medical-agent-design-feasibility.zh-CN.md)

- [PR #5/#6 后续评估与小步修改建议（中文）](docs/reviews/medical-agent-followup.zh-CN.md)

## Contributing

- [Trunk-based development workflow](docs/development-workflow.md)
- [Repository instructions for coding agents](AGENTS.md)
- [agent_1 / agent_2 分工与 agent_2 评审操作规范（中文，待评审）](docs/agent-collaboration.zh-CN.md)
- [Agent 自我改进记录（中文，待评审）](docs/agent-self-improvement.zh-CN.md)
