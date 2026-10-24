# Agent OS Reference Architecture

_Research snapshot: October 23, 2026_

## Purpose

There is no single standard architecture called "Agent OS." Current systems
converge on a collection of services around an agent loop. OpenClaw emphasizes
the gateway, channels, sessions, and plugins. Hermes emphasizes tools, durable
personal memory, learned skills, and scheduled jobs. Agno's AgentOS describes
a runtime API with agents, teams, workflows, sessions, memory, knowledge,
evaluations, authorization, tracing, scheduling, and durable execution.
LangGraph focuses on explicit state, checkpoints, interrupts, and resumable
workflows.

The architecture below combines those established patterns while keeping the
security-critical and product-defining boundaries under project control.

## System model

An Agent OS is best understood as five cooperating planes:

```text
                         Control plane
      identity, agent definitions, policy, schedules, administration
                                  |
Interfaces -> privacy gateway -> Execution plane -> delivery
                                  |
              agent loop, workflows, tasks, queues, workers
                    |             |             |
              Data plane    Capability plane   Assurance plane
              sessions      tools              audit
              memory        RAG/search         traces
              checkpoints   sandboxes          evaluations
              artifacts     fulfillment        learning gates
```

- **Control plane** defines who and what may run, with which configuration.
- **Execution plane** turns requests and triggers into durable runs.
- **Data plane** stores state required to resume, retrieve, and explain work.
- **Capability plane** exposes bounded ways to read data or affect the world.
- **Assurance plane** measures, audits, and safely improves the system.

The model is not a privileged service. It is an untrusted reasoning component
inside the execution plane. It may propose actions; trusted code authorizes
and fulfills them.

## Component inventory

| Component | Responsibility | Important boundary |
| --- | --- | --- |
| Interface gateway | Accept web, CLI, API, messaging, webhook, and agent-to-agent traffic | Normalize input without granting authority |
| Identity and tenancy | Authenticate users, workloads, agents, and service accounts | Bind every operation to a principal and tenant |
| Authorization service | Enforce roles, scopes, resource ownership, and delegation | Authentication alone is not authorization |
| Agent registry | Version agent instructions, model policy, tools, budgets, and release state | Runs reference an immutable released version |
| Model gateway | Select providers/models, enforce budgets, retry, and meter usage | Only receives privacy-approved context |
| Session service | Maintain conversational continuity and channel bindings | A session is not a durable unit of work |
| Context builder | Assemble the minimum authorized prompt for a model call | Applies ordering, size, trust, and provenance rules |
| Memory service | Store and retrieve durable learned facts or procedures | Writes are candidates until policy accepts them |
| Task service | Represent user or system work and its lifecycle | Owns deadlines, priority, status, and result references |
| Scheduler | Convert time-based definitions into due task instances | Does not execute agent code itself |
| Workflow engine | Coordinate explicit multi-step or multi-agent state machines | Checkpoint at stable boundaries |
| Queue and workers | Claim, lease, retry, and execute durable runs | Delivery must tolerate crashes and duplicates |
| Tool registry | Publish typed capability descriptions to agents | A tool schema is not permission to execute it |
| Policy and approval service | Decide whether a proposed action is allowed | Can require a human or a stronger identity proof |
| Privacy gateway | Minimize, redact, or tokenize data before model calls | Raw protected data stays outside model context |
| Token vault | Resolve opaque references inside trusted services | Mapping is encrypted, scoped, and never logged |
| Fulfillment executor | Perform authorized side effects using real credentials/data | The model never directly holds provider credentials |
| Knowledge service | Ingest, authorize, retrieve, rerank, and cite documents | Tenant and document ACLs apply before retrieval |
| Search adapters | Query web, enterprise, code, or structured sources | Return bounded, attributed, injection-scanned results |
| Sandbox service | Isolate code, browser, and untrusted artifact processing | Explicit network, filesystem, time, and resource limits |
| Artifact store | Persist files and large outputs outside prompts and events | Access-controlled references replace embedded content |
| Event bus | Connect lifecycle events to delivery and assurance services | Events are replayable and content-minimized |
| Observability | Record metrics, traces, costs, and operational health | Diagnostic telemetry is not the compliance audit log |
| Audit ledger | Record security decisions and side effects immutably | Answers who did what, when, why, and under which policy |
| Evaluation service | Score behavior against deterministic and model-based checks | Evaluation data is versioned and access-controlled |
| Learning service | Propose memory, skill, prompt, or harness improvements | Promotion requires offline evidence and review |
| Administration UI/API | Manage agents, runs, schedules, approvals, and incidents | Uses the same authorization path as other clients |

Not every component needs to be a separate process initially. The boundaries
should still exist as interfaces so high-risk services can be isolated later.

## Do not collapse these concepts

### Session, task, run, workflow, and schedule

- A **session** is a continuity container for conversation history, channel
  identity, and working context.
- A **task** is a durable request for an outcome. It can outlive a session.
- A **run** is one execution attempt of an agent or workflow for a task.
- A **workflow** is an explicit graph or state machine coordinating steps.
- A **schedule** is a trigger definition that creates tasks when it becomes
  due.

One session may create many tasks. One task may have several retry runs. A
schedule may create a new task for every occurrence. A workflow may pause for
hours awaiting approval while its session remains inactive.

### Scheduler and durable executor

A scheduler calculates what is due. It should enqueue a task and then return.
The durable executor owns claiming, leases, retries, checkpoints, cancellation,
and completion. Combining them makes missed or duplicated jobs much harder to
reason about after restarts.

Hermes provides a useful reference: due jobs run in fresh sessions; claims and
attempts are persisted; a lock prevents the same batch from running twice; and
an abandoned attempt becomes `unknown` instead of being blindly replayed.
Agno makes the same operational distinction: ordinary background tasks are
not durable merely because session state is stored in a database.

### Memory and RAG/search

Memory is agent- or user-specific state learned from interaction. RAG is an
authorized knowledge pipeline over documents and other sources. Search is a
query capability. They may share indexing infrastructure, but their ownership,
retention, trust, and write policies differ.

### Tool and fulfillment

A tool is the typed capability the agent can request. Fulfillment is trusted
code that resolves protected data and performs an approved side effect. For
example, `send_email(CONTACT_17, body)` may be visible to the model, while the
executor alone can resolve `CONTACT_17`, retrieve credentials, and call the
email provider.

### Trace, audit, evaluation, and analysis

- A **trace** explains runtime latency, model calls, and execution paths.
- An **audit event** proves a security or business action and its authorization.
- An **evaluation** scores behavior against a declared criterion and dataset.
- **Analysis** aggregates those records to discover patterns and regressions.

They can consume a common event stream, but have different retention,
integrity, privacy, and access requirements.

## Canonical task lifecycle

```text
created -> queued -> claimed -> running -----------------> completed
                         |          |  |  |                    |
                         |          |  |  +-> waiting_input ---+
                         |          |  +----> waiting_approval -+
                         |          +-------> retry_scheduled -> queued
                         |
                         +------------------> unknown

created/queued/running/waiting/retry_scheduled -> cancelled
running/retry_scheduled ----------------------> failed
```

`unknown` is important: after a crash, an external side effect might have
succeeded even if the worker did not persist completion. Automatic replay can
duplicate a payment, message, or deployment. Recovery must inspect the
idempotency key or provider result before retrying.

Each task should carry at least:

- principal, tenant, agent version, and policy version;
- trigger and parent task, if any;
- requested outcome, priority, deadline, and resource budget;
- status, attempt count, lease owner, and lease expiry;
- idempotency key and external correlation identifiers;
- session, workflow, checkpoint, result, and artifact references;
- timestamps and content-minimized provenance.

## Scheduling architecture

```text
schedule definition
  cron / once / event / webhook
          |
     trigger service -- records occurrence and idempotency key
          |
       task queue
          |
   durable worker pool
          |
 workflow or agent run
          |
 result store -> policy-aware delivery adapter
```

Recommended rules:

1. Persist schedules separately from their occurrences.
2. Evaluate time zones and daylight-saving behavior explicitly.
3. Give every occurrence a stable idempotency key.
4. Use leases rather than process-local locks for distributed workers.
5. Record the attempt before dispatching work.
6. Bound retries with exponential backoff and a dead-letter path.
7. Prevent recursive schedule creation unless policy explicitly allows it.
8. Start scheduled work in a fresh execution context, then load only the
   authorized memory and knowledge it needs.
9. Separate execution from result delivery; delivery has its own retries and
   policy checks.

## Memory architecture

Memory should be separated into types because each needs different read,
write, retention, and trust rules:

| Memory type | Examples | Normal lifetime |
| --- | --- | --- |
| Working context | Current plan, recent tool results | One run |
| Session history | Conversation turns and summaries | One session or retention window |
| Episodic memory | Prior outcomes and interactions | Days to months |
| Semantic memory | Stable user facts and domain facts | Until invalidated or deleted |
| Procedural memory | Skills, recipes, and tool-use patterns | Versioned releases |
| User profile | Preferences and accessibility settings | User-controlled |
| Operational state | Checkpoints, leases, task state | Until workflow and audit retention end |

A memory record should contain its source, author, tenant, confidence, trust
class, creation time, expiry, supersession chain, access policy, and deletion
state. Retrieval should consider relevance, recency, authority, and conflict;
similarity alone is insufficient.

OpenClaw's documented approach—plain inspectable files plus a searchable
SQLite index—shows the value of transparent storage and provenance. Its
background "dreaming" process is a useful pattern for consolidation: promote
strong short-term signals, merge duplicates, retire stale records, and retain
source anchors. Consolidation must not silently convert untrusted retrieved
content into trusted long-term instructions.

Memory writes should follow this path:

```text
run evidence -> candidate memory -> privacy and poisoning checks
             -> conflict/retention policy -> accepted versioned record
```

Users need the ability to inspect, correct, export, and delete personal
memory. Deletion must propagate to indexes, caches, summaries, and derived
records.

## Request and run lifecycle

```text
1. Interface authenticates the principal and normalizes the request.
2. Privacy Gateway classifies and tokenizes protected values.
3. Session service appends the safe input; task service creates durable work.
4. Context builder loads the released agent version, authorized memory,
   required policy, and minimal relevant knowledge.
5. Model gateway invokes the selected model within cost and data policy.
6. Agent proposes a typed tool call or a final response.
7. Policy engine validates identity, scopes, arguments, risk, and approvals.
8. Sandbox or Fulfillment Executor performs the permitted operation.
9. Worker persists the result and a checkpoint before the next model step.
10. Output DLP checks the response; a delivery adapter sends it.
11. Traces, audit events, costs, and evaluation inputs are emitted separately.
12. Memory or skill updates enter a candidate queue; they are not directly
    promoted by the production run.
```

LangGraph's node-boundary checkpoint model is a strong reference for steps
that must pause and resume. Expected failures should be classified: transient
errors retry, model-correctable errors return structured feedback, user-fixable
conditions pause, and unexpected defects surface rather than looping.

## Suggested data contracts

The first implementation should define versioned contracts for:

| Record | Purpose |
| --- | --- |
| `AgentDefinition` | Released model, instructions, tools, policies, and budgets |
| `Session` | Conversation continuity and channel bindings |
| `Task` | Durable request and lifecycle |
| `Run` | One execution attempt with an agent/workflow version |
| `Step` | Checkpointable unit within a run |
| `ToolCall` | Proposed capability, arguments, decision, and result reference |
| `Schedule` | Trigger rule, owner, time zone, and activation state |
| `MemoryRecord` | Versioned learned state with provenance and access policy |
| `KnowledgeDocument` | Source, revision, ACL, classification, and index state |
| `Approval` | Human or policy decision bound to the exact proposed action |
| `CredentialRef` | Opaque, scoped reference to a secret outside agent state |
| `Artifact` | Access-controlled reference to a file or large result |
| `EvalResult` | Versioned scorer, dataset item, score, and evidence references |
| `AuditEvent` | Append-only security or side-effect record |

IDs should be opaque. Events and logs should use references rather than raw
prompt, secret, user, or artifact content by default.

## Production deployment topology

```text
                         Admin/API clients
                                |
                Gateway + identity + rate limits
                                |
             Privacy Gateway + authorization service
                     |                    |
            session/task database     token vault
                     |
     scheduler -> durable queue -> isolated worker pools
                                      |       |
                               model gateway  policy engine
                                      |       |
                                 model APIs   tools/sandboxes
                                              |
                                      fulfillment adapters

Supporting stores: checkpoint DB, object/artifact store, knowledge indexes,
memory index, event bus, telemetry backend, audit ledger, evaluation store.
```

The API layer should be horizontally scalable and keep process-local state
non-authoritative. The database, queue, vault, and artifact store provide the
durable backbone. Worker pools should be isolated by risk and, where required,
tenant. High-risk fulfillment can run in a separate network and identity
boundary from general agent execution.

## What to adopt and what to own

| Area | Strong current reference | Recommendation |
| --- | --- | --- |
| Gateway, channels, sessions, plugins | OpenClaw | Adopt or integrate without a core fork first |
| Personal memory and learned skills | Hermes and OpenClaw | Reuse patterns; own promotion and privacy policy |
| Scheduled personal-agent jobs | Hermes | Reuse its lifecycle lessons, not necessarily its storage |
| Runtime API and resource taxonomy | Agno AgentOS | Use as a completeness checklist |
| Durable graphs and human interrupts | LangGraph | Adopt if workflows need explicit resumability |
| Offline harness optimization | Google Research RRSI | Keep outside production and gate every promotion |
| Privacy, authorization, fulfillment | No general harness is sufficient | Own these contracts and trust boundaries |
| Product data and tenant model | Project-specific | Own and version from the beginning |

This keeps OpenClaw or another harness replaceable. The project can substitute
a runtime without migrating its identity, privacy, task, memory, or audit
semantics at the same time.

## Delivery sequence

### Minimum viable Agent OS

- one authenticated interface and one released agent definition;
- sessions, tasks, runs, and checkpoint persistence;
- one model adapter behind the Privacy Gateway;
- typed tools, policy decisions, and one low-risk fulfillment adapter;
- durable queue with bounded retries and idempotency;
- content-minimized traces and an audit record for every side effect;
- a deterministic evaluation suite.

### Operational platform

- schedules, event triggers, cancellation, and result delivery;
- authorization-aware RAG/search and artifact storage;
- memory candidates, user correction/deletion, and consolidation;
- approval inbox, incident controls, budgets, and tenant isolation;
- sampled production evaluations and regression dashboards.

### Controlled learning

- versioned skills and memory promotion workflows;
- held-out security, privacy, quality, latency, and cost gates;
- isolated RRSI or other optimization runs;
- staged releases, rollback, and explicit human ownership.

## Open design decisions

Before implementation, record decisions for:

- Python, TypeScript, or mixed service boundaries;
- the initial harness and whether it runs embedded or as a separate gateway;
- relational database, durable queue, object store, and search/index choices;
- local, hosted, or hybrid model processing and its data residency policy;
- single-user, workspace, or multi-tenant isolation requirements;
- workflow semantics: at-least-once execution and idempotency expectations;
- memory retention, user controls, and acceptable automated consolidation;
- which actions always require human approval;
- telemetry content policy and audit retention;
- the versioning and rollback unit for agents, skills, prompts, and tools.

These decisions should be ADRs or design documents before production code
depends on them.

## Primary sources

- [Agno AgentOS overview](https://docs.agno.com/agent-os/overview)
- [Agno AgentOS API resources](https://docs.agno.com/reference-api/overview)
- [Agno AgentOS examples](https://docs.agno.com/examples/agent-os/overview)
- [OpenClaw architecture](https://docs.openclaw.ai/concepts/architecture)
- [OpenClaw memory architecture](https://docs.openclaw.ai/concepts/memory-architecture)
- [OpenClaw dreaming and consolidation](https://docs.openclaw.ai/concepts/dreaming)
- [Hermes scheduled tasks](https://hermes-agent.nousresearch.com/docs/user-guide/features/cron/)
- [Hermes configuration and data layout](https://hermes-agent.nousresearch.com/docs/user-guide/configuration/)
- [Hermes tool system](https://hermes-agent.nousresearch.com/docs/user-guide/features/tools/)
- [LangGraph design guidance](https://docs.langchain.com/oss/javascript/langgraph/thinking-in-langgraph)
- [Google Research RRSI](https://github.com/google-research/rrsi)
