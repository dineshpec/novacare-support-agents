# SDLC Work In Progress

## Product Snapshot

Goal: A local support chatbot for current answers about AI topics, movies, sports, and
jobs, with per-customer memory and human escalation.

Working Today: The trusted-local MVP is implemented in `app.py` and `support_bot\`.
The Streamlit UI was smoke-checked in a browser with dummy keys. This verifies the
local UI path, not live provider integration.

Reusable Today: Implemented customer memory, search compaction, AutoGen Swarm routing,
service orchestration, Streamlit presentation, and focused tests.

Current Increment: The one-PR support chatbot is implemented. The available suite has
26 tests pass tests and two live tests skipped because API keys were unavailable.

Remaining Shared Work: No implementation work is reported as remaining for this MVP.
Live OpenAI and SerpAPI behavior remains unverified until credentials are available.

Target-Owned Work: The local app and support modules own chat, memory, search, agent
routing, escalation tickets, and usage display.

Deferred: Authentication and shared-host isolation, production deployment, automated
retention/deletion, remote storage, and ticket workflow.

Before Coding: None for the trusted-local MVP. No production deployment is authorized.

Next Action: Obtain keys and run the two skipped live tests if real provider-boundary
evidence is required; otherwise proceed to human review of the documents and MVP.

## Process Snapshot

Last Updated: 2026-09-27T17:56:00Z
Updated By: agent
Current Stage: code-verify
Current Gate: none
Project Entry Mode: greenfield
Work Scope: product/system
Ready To Implement: Yes
Review Level: Standard
Extra Checks: security, privacy

## Current Artifacts

| Kind | Path | Status | Notes |
| --- | --- | --- | --- |
| Spec | [spec.md](./spec.md) | draft | Version 3; structural checker passed; not independently reviewed or approved. |
| Design | [design.md](./design.md) | draft | Aligned to code; design checker passed; view at [design.html](./design.html). |
| Plan | [plan.md](./plan.md) | draft | One-node plan aligned to completed implementation; checker passed. |

## Decisions And Assumptions

- Clarifications and off-topic replies are plain text from triage, both reported with
  source `clarify`; there is no user-agent handoff or HandoffTermination.
- `BotReply` uses `memory`, `web`, `clarify`, `escalated`, or `error`. The UI's direct
  human-ticket message uses UI-only source `human`.
- The implemented tests use AutoGen replay/fakes for local coverage. Two live tests are
  skipped when credentials are unavailable; this is not evidence of a live boundary.
- Trusted-local use remains the product boundary; shared-host controls and data
  lifecycle behavior remain deferred.

## Check And Review Evidence

- 2026-09-27: Product suite result reported: 26 tests pass, 2 live tests skipped because
  `OPENAI_API_KEY` and `SERPAPI_API_KEY` were unavailable.
- 2026-09-27: Streamlit UI smoke-checked in browser with dummy keys; live providers
  were not tested by that browser smoke.
- 2026-09-27: `check_spec.py .sdlc\spec.md` — 7/7 passed; 100% requirement/need
  acceptance coverage.
- 2026-09-27: `check_design.py .sdlc\design.md --spec .sdlc\spec.md` — 13/13
  passed; 100% component requirement/test coverage.
- 2026-09-27: `check_plan.py .sdlc\plan.md --spec .sdlc\spec.md --design
  .sdlc\design.md` — 21/21 passed; all listed obligations allocated.
- Checker results are structural. No independent semantic review is claimed.

## Results And Feedback

Expected Result: A usable trusted-local support chatbot with documented behavior,
architecture, and verification evidence.
Feedback From: Product test suite and browser UI smoke.
Feedback Status: received
Feedback Evidence: 26 tests pass, two credential-gated live tests skipped, and UI
smoke-checked in browser with dummy keys.
Current Work Group: none
Current Work: none
Parallel Limit: 1
What Changed: Code is implemented; design, HTML view, plan, and WIP now reflect the
observed module/API/source behavior and reported verification.
Documents To Update: Reopen spec/design/plan if live-boundary evidence or human review
changes accepted behavior, interfaces, or risk assumptions.
Stop Conditions: Pause before deployment, shared hosting, or sensitive/regulated data;
pause if provider behavior or per-customer persistence invalidates documented contracts.

## Open Questions And Blockers

- Live OpenAI and SerpAPI boundaries remain unverified until the two skipped tests can
  run with valid credentials.
- Memory retention and shared-host access controls must be decided before deployment
  outside the trusted-local scope.

## Bootstrap Status

Bootstrap File: none
Status: not-offered
Notes: No repository bootstrap instruction file was requested or created.

- Independent code review found one issue (customer-ID filename collisions could share memory); fixed with a hashed filename suffix and a regression test. Suite: 26 passed, 2 live tests skipped (no keys).

- Bug fix (user report, search not working): the configured key was a Serper.dev key, so SerpAPI returned 401. Added Serper.dev support with provider detected from the key (SEARCH_PROVIDER override). Failed searches are now escalated with a ticket and not saved to memory; the newest memory entry wins ties. Suite: 34 passed, including the live OpenAI and search tests with real keys. The design doc should mention the second search provider in its next revision.
