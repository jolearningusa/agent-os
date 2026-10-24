# Agent OS engineering guide

## Source of truth

- Product and architecture direction:
  `docs/research/agent-os-landscape.md` until superseded by accepted design
  documents.
- Development and pull-request process: `docs/development-workflow.md`.
- Executable checks: repository-root build configuration and CI workflows as
  they are added.

When documentation and implementation disagree, reconcile them in the same
change. For intentional product, architecture, API, privacy, or persistent-data
changes, update the design first and then implement it.

## Architecture boundaries

- Keep project-owned interfaces around runtimes, models, tools, policy,
  privacy, retrieval, memory, telemetry, evaluation, and persistence.
- Treat external harnesses as replaceable adapters, not as the public contract
  of Agent OS.
- Keep private user data behind the Privacy Gateway and Token Vault. Models
  receive the minimum necessary data and opaque references where possible.
- The model may propose actions; trusted policy and fulfillment code must
  authorize and execute side effects.
- Enforce retrieval authorization before content enters agent context.
- Keep production self-improvement offline and gated by held-out evaluation,
  security checks, human review, staged deployment, and rollback.
- Never place secrets or real personal data in source, fixtures, prompts,
  transcripts, logs, or evaluation datasets.

## Workflow

Use trunk-based development. `main` is the only long-lived branch and must
remain releasable.

1. Fetch `origin/main` and fast-forward a clean local `main`.
2. Create one short-lived branch from that verified revision, using
   `feature/*`, `fix/*`, `hotfix/*`, `refactor/*`, `test/*`, `docs/*`, or
   `chore/*`.
3. Keep one cohesive product or engineering intent per branch and pull
   request. Split large work with compatible slices or feature flags.
4. For behavior, contract, architecture, privacy, or persistent-data changes,
   update the relevant design and engineering documentation before code.
5. Add tests at the lowest useful layer, including failure, authorization,
   privacy, retry, and rollback paths relevant to the change.
6. Run all repository checks locally before pushing. Do not skip, mute, or
   weaken checks to make a change pass.
7. Rebase the branch on the latest `origin/main`, rerun affected checks, then
   push and open a labeled Draft PR.
8. Resolve review conversations and CI failures. Mark the PR ready only after
   required checks are green.
9. Squash-merge only with current user authorization. Never push or
   force-push directly to `main`, and never merge a failing PR.
10. After merge, fast-forward local `main` and delete the merged topic branch.

Do not open a second implementation PR for a later dependent task while the
current PR remains open. Complete tasks sequentially unless the work is truly
independent and the user explicitly requests parallel delivery.

## Pull requests

- Prefer Draft PRs while work or validation is incomplete.
- Use a clear title and include scope, design decisions, privacy/security
  impact, tests run, operational impact, and rollback notes.
- Apply labels matching the content, such as `enhancement`, `bug`,
  `documentation`, `security`, `privacy`, and the implementation language.
- Keep commits focused and reviewable; the final integration method is squash
  merge.
- Do not merge automatically unless the user explicitly authorizes it.

## Definition of done

- Documentation, implementation, configuration, and examples agree.
- Formatting, lint, types, unit tests, integration tests, and builds relevant
  to the change pass without ignored failures.
- New behavior has deterministic regression coverage and meaningful negative
  cases.
- Privacy, authorization, tenant isolation, secret handling, logging, and
  fulfillment boundaries are tested when affected.
- Persistent changes include compatible migration and rollback plans.
- Telemetry is content-free by default and does not expose secrets or PII.
- The PR is focused, labeled, reviewable, and green in CI.
