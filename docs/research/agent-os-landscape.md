# Agent OS Landscape and Recommended Architecture

_Research snapshot: October 23, 2026_

## Executive recommendation

Start with **OpenClaw as the control plane and product shell**, but keep the
parts that differentiate this Agent OS behind project-owned interfaces:

- privacy gateway and token vault;
- policy and authorization engine;
- tool and fulfillment executor;
- retrieval, RAG, and search services;
- event, logging, evaluation, and analysis pipeline;
- memory and skill-learning policy.

Use **Hermes Agent as the main reference for experiential learning** and
consider adopting isolated parts of its skill and memory lifecycle. Use
**RRSI as an offline harness-optimization process**, never as an unrestricted
production self-modification loop.

Do not begin by forking OpenClaw or Hermes. Integrate through plugins, hooks,
tools, MCP, and telemetry first. Both projects are large and fast-moving; a
fork should be a last resort after an extension-point gap is demonstrated.

## Define the layers clearly

"Agent OS" is not one standardized component. It is useful to separate four
layers:

1. **Agent** — model, instructions, working context, decision loop, delegation,
   and stopping policy.
2. **Runtime** — state transitions, sessions, persistence, checkpoints,
   retries, scheduling, approvals, and sandboxing.
3. **Capabilities** — search, retrieval, browser, code execution, APIs, and
   other tools the agent may invoke.
4. **Platform services** — identity, authorization, privacy, fulfillment,
   logging, tracing, evaluation, analytics, cost controls, and audit.

Logging and evaluation are not agent identities. Search is normally exposed
to an agent as a tool. RAG is a larger knowledge subsystem whose query surface
may be exposed as a tool.

## Current open-source options

### OpenClaw

OpenClaw is the closest match to a broad, production-shaped Agent OS. It
includes a long-running gateway, desktop/mobile/web/CLI clients, messaging
channels, sessions, memory, multi-agent routing, tools, plugins, hooks, skills,
MCP integration, automations, sandboxes, policy controls, secrets, audit
records, and OpenTelemetry export.

Its Skill Workshop lets an agent save and update its own procedural skills,
with change history and undo. This is persistent skill learning, not model
weight training.

**Best fit:** the initial control plane, integration platform, and user-facing
shell.

**Watch-outs:** large surface area, trusted-single-operator defaults in some
configurations, plugins running in-process, and the maintenance cost of a core
fork. Strong tenant isolation still requires separate trust boundaries,
sandboxing, and explicit policy.

### Hermes Agent

Hermes is a Python-first personal-agent platform with a CLI, desktop app,
messaging gateway, tools, plugins, MCP, subagents, schedules, multiple
execution backends, persistent memory, session search, and evaluation code.

Its central differentiator is a closed learning loop: it curates memory,
creates skills after complex work, improves skills during use, searches prior
conversations, and builds a persistent user model.

**Best fit:** a personal agent or research system where learning from repeated
user workflows is the main product feature.

**Watch-outs:** built-in PII redaction is currently narrower than a general
privacy firewall, and convenience redaction must not be confused with a strong
security boundary. Sensitive deployments still need external privacy,
authorization, and sandbox layers.

### LangGraph

LangGraph is a low-level orchestration runtime for long-running, stateful
agents. It provides explicit graphs, persistence, durable execution,
streaming, and human-in-the-loop control while leaving prompts and agent
architecture largely to the application.

**Best fit:** building a new runtime from first principles when owning the
execution model is itself the product.

**Trade-off:** maximum architectural control, but substantially more platform
work than adopting OpenClaw or Hermes.

### OpenAI Agents SDK

The OpenAI Agents SDK is a compact code-first runtime for agent loops, tools,
handoffs, guardrails, sessions, tracing, and human review. The application
retains responsibility for storage, deployment, approvals, and tool
implementations.

**Best fit:** an OpenAI-centric service that needs a smaller abstraction than
a full Agent OS.

### PydanticAI and Mastra

- **PydanticAI** is a strong Python option when typed dependencies, structured
  output, testing, and explicit application composition matter most.
- **Mastra** is a strong TypeScript option when a batteries-included stack for
  agents, workflows, memory, observability, datasets, and scorers is desired.

They are viable alternatives, but neither currently changes the primary
recommendation for this repository.

## Self-improvement systems

### RRSI

Google Research's **Regularized Recursive Self-Improvement of Agent Harnesses
(RRSI)** improves a frozen model's surrounding harness. Its editable surface
can include prompts, control flow, configuration, context management, tools,
skills, memory, and subagents.

RRSI proposes candidate changes, screens them for suite-specific leakage,
evaluates candidates in isolated Git worktrees, and accepts changes only when
measured gains exceed evaluation noise and justify added inference cost. The
history is auditable and the incumbent harness remains a Git commit.

RRSI is research code, not a supported Google product. It should be used as an
offline improvement pipeline:

```text
production traces and outcomes
        -> curated evaluation set
        -> isolated RRSI candidates
        -> held-out/security/cost gates
        -> human review
        -> staged deployment
```

### EnvHarness

Google Research's **EnvHarness** improves the environment that teaches an
agent. A designer diagnoses weaknesses from trajectories and generates
wrappers that change starting conditions, observations, or allowed actions
without changing the environment's trusted success verifier.

RRSI and EnvHarness are complementary: RRSI evolves the agent harness;
EnvHarness evolves the teaching environment.

## Privacy and fulfillment boundary

The model must not be the system of record for identity, credentials, payment
details, medical information, or other sensitive user data. Prompt
instructions alone cannot enforce this boundary.

Introduce two explicit services:

1. **Privacy Gateway** — classifies, minimizes, redacts, or tokenizes data
   before any external model call.
2. **Fulfillment Executor** — resolves opaque references after authorization
   and performs side effects without revealing the underlying values to the
   model.

Example:

```text
User request containing jane@example.com
        -> privacy gateway
LLM receives CONTACT_17
        -> LLM proposes send_email(CONTACT_17, body)
        -> policy and optional human approval
fulfillment executor resolves CONTACT_17 locally
        -> email provider receives the real address
```

The privacy boundary should contain:

- local PII and secret detection;
- deterministic tokenization where cross-turn references are required;
- encrypted token mappings separated from prompts and transcripts;
- deny-by-default model-input schemas;
- per-agent, per-tool, per-user, and per-tenant authorization;
- output DLP before responses, logs, or external delivery;
- content-free telemetry by default;
- retention, deletion, and provenance controls.

Microsoft Presidio is a useful local, extensible PII detector and anonymizer.
It supports replacement, redaction, masking, hashing, and encryption. Its own
documentation warns that automated detection cannot guarantee finding all
sensitive data, so data minimization and typed allowlists remain the primary
control.

For Google Cloud deployments, Sensitive Data Protection offers redaction,
masking, replacement, and reversible cryptographic tokenization. A strict
"data must not leave our environment" policy should use local inspection
rather than sending raw data to a cloud DLP endpoint.

OpenClaw's telemetry excludes raw prompts, responses, and tool content by
default, which is a good operational baseline. This protects observability
export, not the model request itself; an outbound privacy hook is still needed.
Hermes has platform-specific PII hashing and credential-output redaction, but
these are not substitutes for a general Privacy Gateway.

## RAG and search architecture

Treat RAG as a separate knowledge service:

```text
ingestion -> parsing -> classification -> chunking -> indexing
                                              |
agent -> authorized query -> retrieve -> rerank -> cite -> safe context
```

Important requirements:

- enforce tenant and document authorization before retrieval, not after;
- prevent embeddings and caches from mixing tenant data;
- store document provenance, revision, and deletion state;
- return the minimum useful passages instead of whole documents;
- scan retrieved content for prompt injection and sensitive data;
- make citations and access decisions auditable;
- allow deterministic pre-retrieval when the agent should not decide whether
  required policy context is loaded.

Expose web search and knowledge retrieval through small typed contracts, for
example `web_search(query, policy)` and
`knowledge_search(query, tenant, filters)`. The implementation can then change
without changing agent behavior.

## Proposed architecture

The detailed component boundaries, state models, and deployment topology are
defined in the
[Agent OS reference architecture](agent-os-reference-architecture.md).

```text
Clients and channels
        |
OpenClaw gateway and session control
        |
Identity + authorization + privacy gateway
        |
Agent runtime / model adapter
        |
Tool policy and approval boundary
        |
Fulfillment executor ---- RAG/search ---- sandboxed compute
        |
Event stream (content-free by default)
        |
Tracing ---- evaluations ---- analytics ---- audit

Offline only:
traces + curated datasets -> RRSI/other optimizers -> reviewed release
```

Project-owned interfaces should include:

```text
AgentRuntime
ModelProvider
ToolRegistry
PolicyEngine
PrivacyGateway
TokenVault
FulfillmentExecutor
Retriever
MemoryStore
TraceSink
Evaluator
CheckpointStore
ApprovalPolicy
```

## Delivery phases

### Phase 1: secure vertical slice

- Run OpenClaw without a core fork.
- Implement one model provider and one low-risk tool.
- Add local privacy/tokenization before model calls.
- Keep telemetry content disabled.
- Add typed tool schemas, policy checks, and human approval.
- Build a small deterministic evaluation dataset.

### Phase 2: knowledge and operations

- Add authorization-aware RAG and search.
- Add durable jobs, retries, cost budgets, and audit queries.
- Add offline and sampled production evaluations.
- Add sandboxed execution and tenant-isolated workers.

### Phase 3: controlled learning

- Enable reviewed skill creation and revision.
- Build promotion gates for learned skills.
- Run RRSI against curated evolve and held-out sets.
- Require security, privacy, regression, and cost checks before release.
- Preserve rollback to every accepted harness version.

## Non-negotiable principles

1. The LLM proposes; trusted code authorizes and fulfills.
2. Raw secrets and unnecessary PII never enter model context.
3. Every side effect is attributable, policy-checked, and idempotent where
   possible.
4. Memory and learned skills retain source provenance and support deletion.
5. Self-improvement happens against held-out evidence and never deploys itself
   directly to production.
6. Telemetry captures behavior and cost without capturing content by default.
7. Retrieval authorization happens before content reaches the agent.
8. Open-source dependencies remain replaceable behind project-owned contracts.

## Primary sources

- [OpenClaw repository](https://github.com/openclaw/openclaw)
- [OpenClaw Gateway architecture](https://docs.openclaw.ai/concepts/architecture)
- [OpenClaw skills and Skill Workshop](https://docs.openclaw.ai/tools/skills)
- [OpenClaw security trust model](https://docs.openclaw.ai/gateway/security/trust-model)
- [OpenClaw telemetry privacy](https://docs.openclaw.ai/gateway/opentelemetry/privacy-and-trace-context)
- [Hermes Agent repository](https://github.com/NousResearch/hermes-agent)
- [Hermes privacy configuration](https://hermes-agent.nousresearch.com/docs/user-guide/configuration/)
- [Hermes security](https://hermes-agent.nousresearch.com/docs/user-guide/security)
- [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview)
- [OpenAI agent runtime comparison](https://developers.openai.com/api/docs/guides/agents)
- [OpenAI Agents SDK](https://developers.openai.com/api/docs/guides/agents/sdk)
- [PydanticAI](https://pydantic.dev/docs/ai/overview/)
- [Mastra](https://mastra.ai/docs)
- [Google Research RRSI](https://github.com/google-research/rrsi)
- [Google Research EnvHarness](https://github.com/google-research/envharness)
- [Microsoft Presidio](https://microsoft.github.io/presidio/)
- [Google Sensitive Data Protection transformations](https://cloud.google.com/sensitive-data-protection/docs/transformations-reference)
