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

当前 L0b 配置契约可独立校验。已验证平台为 macOS arm64 / Python 3.13，
其他平台需补充审核后的依赖 wheel 哈希。以下安装仅用于校验工具环境。

```sh
umask 077
python3 -m venv .local/harness-lab/config-check-env
.local/harness-lab/config-check-env/bin/python -m pip install --require-hashes -r requirements-config.txt
.local/harness-lab/config-check-env/bin/python scripts/check_harness_config.py configs/local-hermes.json
.local/harness-lab/config-check-env/bin/python -m unittest discover -s tests -v
```

字段与失败行为见 [本地配置契约](docs/design/local-harness-config.zh-CN.md)。

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
