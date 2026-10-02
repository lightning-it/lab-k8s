# Engineering agent contract

This repository contains public Kubernetes laboratory manifests and runbooks. Treat
`.lit/repository.yml`, `RELEASE.md`, `TESTING.md`, `SECURITY.md`, and the accepted
Lightning IT Engineering ADRs as the governing repository contract.

- Work through a pull request into `develop`; promote reviewed `develop` to `main`.
- Never commit kubeconfigs, tokens, private keys, credentials, or production data.
- Validate YAML structure, Kubernetes manifests, and documented smoke tests.
- Keep external GitHub Actions pinned to full commit SHAs and permissions
  least-privilege.
- Preserve managed-file headers and change shared policy at
  `lightning-it/shared-assets-lit`.
- Run `python3 scripts/lit-push-ready.py push-ready` before pushing.
- Required remote checks and branch protection must not be bypassed.
- ADR 70 temporarily allows zero human/CODEOWNER approvals and separately
  documented protected-environment self-approval for immutable exact-SHA
  plan/apply evidence; it does not allow PR self-review or check bypass.

<!-- LIT REP-40 delivery efficiency: start -->

## AI delivery efficiency contract (mandatory)

- Optimize every task for the smallest safe, usable live result. Keep optional
  hardening, penetration tests, migrations, and documentation perfection out of
  the critical path and track them as separate work items.
- Before editing, state the bounded deliverable, real blockers, stop conditions,
  and time budget. After 90 minutes without a new usable verified state, stop
  before creating more work and simplify, split, or escalate the blocker.
- Collect and deduplicate every known finding for the current head into one
  correction set. A finding does not automatically justify its own commit,
  pull request, successor, agent, or full validation run.
- Run the directly affected suite and workflow first. Run exactly one complete
  push-ready validation only after those targeted checks pass. Repeat the full
  validation only after it found a concrete defect, that defect was corrected,
  and the correction was reproduced by the targeted check.
- Re-read mutable state exactly once at the final mutation boundary. Remove
  duplicate full validation that does not add an independent security property.
- A stale head or run must stop immediately as `stale / not applicable`; it must
  not continue polling, request another review, publish evidence, or consume
  runner time for an obsolete revision.
- Move large inline workflow programs into small separately linted and tested
  scripts when a linter exceeds 60 seconds, exhibits path explosion, or the
  security boundary can no longer be tested locally.
- Keep at most one active implementation pull request per goal. Where the
  governing workflow permits successor heads, two consecutive reviewed heads
  with new correction findings exhaust the normal correction budget; do not
  create another equivalent successor without simplifying or splitting the
  design and recording the new bounded work item.
- Deterministic checks, formatting, inventory, and polling must not invoke AI.
  Use the least expensive model and reasoning level that is sufficient; reserve
  higher reasoning for new architecture, security, or root-cause decisions.
- Measure success by lead time to a usable merge, runner minutes, AI/token cost,
  number of reviewed heads, and new verified state—not by turns, artifacts, or
  apparent activity.
- This contract never permits bypass, force/direct push, manual rerun, fabricated
  evidence, or weaker required checks. The Exact-Revision textual review-unit
  boundary remains `1..199999` bytes unless a separate benchmarked ADR changes it.

Authority: [LIT-ENG-ADR-REP-40](https://wiki.cloud.l-it.io/wiki/spaces/LIT/pages/2878440201),
Amendment 2026-09-12. Delivery and fleet rollout are tracked in LI-206; stale-run
termination is tracked in LI-204.

<!-- LIT REP-40 delivery efficiency: end -->

<!-- LIT REP-60 review governance: start -->
<!-- cspell:ignore litroc -->

## REP-60 current-revision review governance

- Local validation is deterministic only. It must never invoke Codex, GitHub
  Copilot, another model, or an external AI endpoint. Authoritative AI review
  runs only in the protected GitHub pipeline and binds the exact PR head.
- Lightning IT automation may request and fund one GitHub Copilot review only
  when the exact PR author is `litroc`, and only at the finalization boundary;
  intermediate `synchronize` pushes must not trigger AI review. Any finding
  requires correction and a final current-head re-review. The request is
  consumed once per head; unavailable or quota-blocked reviews fail closed
  without an automatic retry. Organization-funded Codex remediation and its
  single re-review are likewise restricted to `litroc`.
- Every other human or external contributor supplies any required current-head
  Copilot review under their own entitlement and cost. Lightning IT verifies
  valid evidence but never requests or funds that review, and personal tokens or
  provider keys never enter Actions.
- A same-repository PR authored exactly by
  `lightning-it-release-automation[bot]` uses only the protected MLX-90 §7.2
  Exact-Revision Codex check. It must never request Copilot or synthesize a
  Copilot success.
- A proven ancestry-only main-to-develop backmerge uses the deterministic
  evidence-bound exemption and performs zero AI calls. Unknown automation
  identities fail closed.
- The only neutral merge-gate result is `Current revision review`. Missing,
  stale, ambiguous, or unresolved review evidence blocks the merge.

<!-- LIT REP-60 review governance: end -->

<!-- LIT REP-60 evidence lifecycle: start -->

### REP-60 evidence lifecycle (mandatory)

- Every pull request into `develop` retains its exact-final-head native GitHub
  CI, required-check, and review history as the authoritative evidence for
  acceptance into `develop`.
- A pull request into `develop` MUST NOT create or retain an additional durable
  release-evidence package, duplicate WORM artifact, or second AI-review
  evidence outside that native GitHub history.
- Only the protected `develop` to `main` promotion creates exactly one durable,
  complete release-evidence package. It binds the full integrated promotion
  diff, base, head, merge base, integration tree, policy, the exact native
  acceptance evidence of every post-baseline ingress PR, and all release and
  audit checks. It MUST NOT request a second AI review of the cumulative
  promotion diff or apply the per-review-unit byte limit to that cumulative
  diff; the limit remains mandatory for each new ingress review unit.
- After a Release-App `release/vX.Y.Z` merge to `main`, its protected
  release-published back-sync is the sole owner of `main` to `develop`
  convergence. The generic ancestry synchronizer MUST detect that exact
  Release-App source and exit without creating a competing PR. This single
  ownership rule prevents base drift, conflicting duplicate back-syncs, and
  human successor branches.
- Agents, workflows, and repository-local rules MUST NOT duplicate that durable
  evidence per `develop` pull request or invoke local AI to create evidence.
  Repository-local rules may only make this lifecycle stricter.

<!-- LIT REP-60 evidence lifecycle: end -->

<!-- LIT Devtools container governance: start -->

## Devtools container execution boundary

- Every deterministic lint, format, type-check, test, build, packaging,
  policy, and validation workload runs in the digest-pinned Lightning IT
  Devtools image, locally and in CI. Host-language runtimes never provide
  acceptance evidence.
- The host boundary is limited to Git, the supported container engine, and the
  centrally managed Devtools, push-ready, and pre-commit dispatchers. A
  dispatcher may inspect Git state and start the pinned container, but it must
  not execute a repository validator through host Python, Node.js, Ansible,
  Ruff, a Python type checker, markdownlint, Renovate, or a comparable host
  runtime.
- If a required command or compatible version is absent, fail closed. Add and
  pin it in `container-ee-wunder-devtools-ubi9`, release that image normally,
  update the centrally managed digest, and rerun the gate. Host fallbacks,
  ad-hoc virtual environments, and unpinned helper images are forbidden.
- Repository-owned tests derive the exact full Devtools image reference from
  the centrally managed push-ready engine when checking the installed wrapper;
  they never hard-code an independent release tag that can drift during a
  normal image rollout.
- A target-specific regression test that asserts managed Devtools-wrapper
  arguments is the same atomic managed unit as the wrapper. Both synchronize
  through an exact source binding, and only an explicitly digest-allowlisted
  predecessor may be replaced; unknown target test content fails closed.
- Defaults stay read-only, offline, socket-free, capability-dropped, and
  non-privileged. A gate may opt into only its explicit tested minimum. Linked
  Git metadata remains read-only and container Git may trust only
  `/workspace`, never `*`. Executable temporary fixtures use the isolated
  container home while generic `/tmp` remains non-executable.
- The Devtools boundary never makes local Codex, Copilot, or other model calls
  and never receives personal AI credentials.

<!-- LIT Devtools container governance: end -->

<!-- LIT AI task governance: start -->

## AI model and token governance

Apply `LIT-GEN-GDR-GOV-30-Budget-Conscious-AI-Model-Selection` to every
substantive Codex or ChatGPT-assisted task. Before investigation, planning, tool
use, implementation, or delegation, record a compact task profile in the task
chat: work item, risk (`low`, `normal`, or `high`), smallest sufficient
model/reasoning choice, rationale, and a concrete escalation condition.

- Use the balanced, lowest reliable capability by default. Escalate to a
  premium/frontier model or higher reasoning only for a high-risk decision,
  complex architecture/debugging/dependencies, or a documented focused failure
  of the standard approach. Restrict that escalation to the difficult subtask.
- Never use Speed Mode. Do not replace verification with a more expensive model
  or sacrifice quality to reduce elapsed time.
- Retrieve only relevant issue, files, logs, and source records; avoid broad
  repository or chat-history loading, speculative analysis, and unbounded retry
  loops. Delegate only independent, bounded work that reduces total effort.
- For GitHub or Jira work, include the task profile in the issue/task record
  when AI assistance materially affects execution. Close with verification and
  remaining risks; preserve durable decisions in Confluence, Jira, or GitHub.

<!-- LIT AI task governance: end -->
