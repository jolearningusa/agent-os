# Trunk-Based Development Workflow

## Goals

Agent OS uses trunk-based development. `main` is the only long-lived branch
and must always be buildable, testable, and releasable. Do not create a
`develop`, `staging`, or long-lived release branch.

```text
main ──┬──────────────── squash merge ────────────────>
       └─ feature/privacy-gateway ─ commits ─ Draft PR
                                      |          |
                                 local checks   CI
```

This workflow keeps integration continuous, limits merge conflicts, makes
rollback straightforward, and prevents an unreviewed branch from becoming an
alternative source of truth.

## Standard workflow

1. Start from the latest verified `origin/main`.
2. Create a short-lived branch with an intent-based prefix:
   - `feature/*` for new behavior;
   - `fix/*` for defects;
   - `hotfix/*` for urgent production defects;
   - `refactor/*` for behavior-preserving structural work;
   - `test/*` for test-only work;
   - `docs/*` for documentation-only work;
   - `chore/*` for maintenance and dependency work.
3. Keep the branch small enough to merge within one or two working days when
   practical.
4. Use feature flags, additive APIs, and compatible migrations to split large
   capabilities into releasable slices.
5. Run all relevant local checks and inspect the resulting diff.
6. Rebase onto the latest `origin/main` and rerun affected checks.
7. Push the topic branch and open a Draft PR against `main`.
8. Apply content-based labels and complete the PR description.
9. Fix CI and review findings on the same branch. Do not open replacement PRs
   to bypass failing checks or unresolved review.
10. When CI is green and review is complete, mark the PR ready and squash-merge
    it with explicit authorization.
11. Delete the merged branch and fast-forward local `main`.

Never commit feature work directly on `main`. Urgent fixes still use a short
`hotfix/*` branch and the same PR and CI path. Do not force-push `main` or
rewrite shared history.

## One task, one PR

Each PR should express one cohesive product or engineering intent. Avoid
combining unrelated fixes, cleanup, dependency updates, and feature work.

When a request contains multiple dependent tasks:

1. implement the first task;
2. open its Draft PR and make CI green;
3. merge it;
4. update local `main`;
5. create the next branch from the new `main`.

Independent work may proceed in parallel only when explicitly requested and
when the branches do not share an unstable contract or migration sequence.

## Design before implementation

Update documentation before implementation when a change affects:

- product-visible behavior;
- public APIs or tool contracts;
- agent/runtime ownership or orchestration;
- authentication, authorization, privacy, or tenant isolation;
- memory, RAG, search, evaluation, or self-learning behavior;
- persistent schemas, migrations, or retention;
- side effects and fulfillment;
- deployment topology or operational controls.

The design should state behavior, boundaries, data flow, threat assumptions,
failure modes, compatibility, rollout, and what is out of scope. The
engineering section should identify modules, interfaces, storage, migrations,
tests, observability, and rollback.

Typos and explanatory wording that do not change a promise or contract do not
require a new design document. They still must not leave documentation and
implementation in conflict.

## Commits and branch hygiene

- Keep each commit focused, understandable, and testable where practical.
- Do not mix generated artifacts or broad formatting changes with functional
  edits unless required by the change.
- Preserve unrelated local changes and never discard another contributor's
  work to obtain a clean diff.
- Rebase topic branches; do not merge `main` into them merely to resolve
  routine drift.
- Never commit credentials, tokens, production data, personal information,
  local environment files, or unredacted traces.

For a confirmed bug, prefer a deterministic regression test that fails before
the fix and passes afterward. Keep the proof visible in the PR history or PR
description even though the final merge is squashed.

## Local validation

As the implementation stack is added, the repository must expose one canonical
root command for the full local quality gate, preferably `make check`. It
should eventually cover:

- formatting checks;
- linting;
- static types;
- unit and integration tests;
- builds or package validation;
- documentation and generated-contract synchronization;
- security and dependency checks appropriate to the stack.

Until that command exists, run every relevant check provided by the affected
package and report anything that could not run with its concrete prerequisite.
Do not skip tests because the change appears small.

User-visible critical paths, authorization boundaries, privacy transformations,
tool approvals, and fulfillment side effects require integration or end-to-end
coverage in addition to unit tests.

## Pull-request requirements

Open PRs as Drafts until implementation and required validation are complete.
Every PR description should include:

- purpose and bounded scope;
- design or architecture links;
- important implementation decisions;
- privacy and security impact;
- persistent-data or migration impact;
- tests and checks run;
- deployment, compatibility, and rollback notes;
- known limitations or deferred work.

Use labels that match the actual change, including combinations such as:

- `enhancement`, `bug`, `documentation`, `refactor`, or `dependencies`;
- `security` or `privacy` when those boundaries change;
- relevant language or platform labels.

Required CI must be green, branches must be current, and review conversations
must be resolved before merge. Use squash merge so `main` retains a linear,
intent-oriented history.

## Recommended repository protection

Configure a ruleset for `main` that:

- requires a pull request before merging;
- requires relevant status checks;
- requires branches to be up to date;
- requires conversation resolution;
- blocks force pushes and branch deletion;
- requires linear history;
- allows squash merge as the normal merge strategy;
- deletes merged head branches automatically.

CI runners should not hold production credentials by default. Production
deployment should use a separate protected environment, exact commit SHA,
least-privilege credentials, and explicit approval where appropriate.

## Definition of done

A change is done when:

- its documentation, code, configuration, and examples agree;
- relevant formatting, lint, type, test, and build checks pass;
- new behavior has deterministic tests at the lowest useful layer;
- affected failure, privacy, authorization, and rollback paths are covered;
- migrations are compatible and have a rollback or recovery plan;
- telemetry remains content-free by default;
- secrets and personal data are absent from code, fixtures, logs, and PR text;
- the focused PR is labeled, reviewed, and green;
- merge and deployment occur only through the authorized workflow.
