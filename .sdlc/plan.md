<!-- sarathi:artifact-format version="3" -->

## Implementation Approach

The integrated local support-chatbot MVP in [spec.md](./spec.md) and
[design.md](./design.md) is implemented in one cohesive PR. UI, orchestration, memory,
agents, and search form one user-facing flow and are tested together. The implementation
has 25 passing tests; two live-boundary tests were skipped because provider keys were
unavailable. The Streamlit UI was smoke-checked in a browser with dummy keys. This plan
does not authorize deployment or shared-host use.

## Impact Map

| Area | Change and extent | Consumer / owner | Allocation |
| --- | --- | --- | --- |
| `app.py` | Add chat, customer selection, source/agent badges, token display, refresh and human controls | Local customer / app | PR-SUPPORT-BOTMVP |
| `support_bot/config.py`, `search.py`, `memory.py`, `agents.py`, `service.py` | Add settings, SerpAPI adapter, customer files, AutoGen team and orchestration | App / support modules | PR-SUPPORT-BOTMVP |
| `data/memory/`, `data/escalations.txt` | Runtime-created local transcripts, indices, and tickets; no migration | Local app operator | PR-SUPPORT-BOTMVP |
| `.env.example`, `.gitignore`, tests | Placeholder credentials, secret exclusion, pytest and optional live smoke | Developers / app | PR-SUPPORT-BOTMVP |
| Deployment, authentication, remote storage | Deliberately unchanged; trusted-local MVP only | None in this increment | Excluded |

## Baseline Reuse

Greenfield MVP: no verified prior product behavior or application modules exist to
reuse. Use accepted AutoGen, Streamlit, OpenAI, and SerpAPI libraries directly; do not
create a separate framework. Local data files are new state, not a migration.
Deployment hardening, authenticated multi-tenant isolation, automated retention, and
ticket workflow are deferred.

## Overview

Plan Type: Implementation
Work Scope: product/system
Ready To Implement: Yes
Review Level: Standard
Extra Checks: security, privacy

The one-node PR graph is `PR-SUPPORT-BOTMVP`. The target is the trusted-local
application and the supplied module layout. A shared or internet-facing deployment
needs revised security/privacy requirements and design.

## Strategy

Implemented verification is in `tests/test_search.py`, `test_memory.py`,
`test_agents.py`, `test_service.py`, and `test_live.py`. The first four use deterministic
fixtures and AutoGen `ReplayChatCompletionClient` where relevant. Result: 25 tests
passed; two live tests in `test_live.py` were skipped because `OPENAI_API_KEY` and
`SERPAPI_API_KEY` were unavailable. These skips leave real provider authentication,
quota, transport, and response compatibility unverified. The Streamlit UI was
smoke-checked in a browser with dummy keys; this does not establish live provider
integration. No production deployment was performed.

Security/privacy checks cover secret-free diagnostics, placeholder-only `.env.example`,
customer-ID sanitization, per-customer isolation, and local data scope. Run only in a
developer/local environment; no live deployment is authorized. Keep completion tokens
bounded and show actual provider usage. Pause and revise the spec/design if shared
hosting, sensitive data, or a multi-user trust boundary is introduced.

## Milestones

### Deliver the local chatbot MVP
<!-- sarathi:milestone id="MILE-SUPPORT-MVP" -->
The supported-topic, customer-memory, UI, and human-help paths are implemented in one
cohesive change. Verification result: 25 tests passed and two live tests were skipped
because provider keys were unavailable; the browser UI smoke check used dummy keys.

## Pull Requests

### Deliver the integrated local support chatbot
<!-- sarathi:delivery id="PR-SUPPORT-BOTMVP" -->
Work Classification: new behavior

- **Outcome:** a local customer can ask a question, receive a fresh specialist or
  customer-memory answer, continue a conversation, and request clarification or human
  escalation.
- **Implemented files:** `app.py`; `support_bot/config.py`, `search.py`, `memory.py`,
  `agents.py`, `service.py`; `tests/test_search.py`, `test_memory.py`, `test_agents.py`,
  `test_service.py`, and `test_live.py`; `.env.example`; and secret-exclusion config.
  Runtime `data/` files are created by the app, not committed as fixtures.
- **Use cases:** UC-SUPPORT-ASK, UC-SUPPORT-RECALL, UC-SUPPORT-ESCALATE.
- **Requirements:** FR-CHAT-CONTEXT, FR-CHAT-ROUTING, FR-SEARCH-REQUIRED,
  FR-MEMORY-REUSE, FR-MEMORY-PERSIST, FR-HUMAN-ESCALATION, FR-UI-CHATSTATE,
  FR-SECURITY-BOUNDARY, FR-COST-BOUNDS, NFR-PRIVACY-LOCAL,
  NFR-RELIABILITY-ERRORS, NFR-COST-LIMITS, NFR-UI-USABILITY.
- **Acceptance and journeys:** AT-SUPPORT-LIVE, AT-SUPPORT-MEMORY,
  AT-SUPPORT-HUMAN, AT-SUPPORT-UISECURITY, AT-SUPPORT-BOUNDS,
  JT-SUPPORT-FOLLOWUP, JT-SUPPORT-HUMANPATH.
- **Components and design tests:** COMP-UI, COMP-SERVICE, COMP-MEMORY,
  COMP-AGENTS, COMP-SEARCH, COMP-CONFIG, TEST-MEMORY-COSINE,
  TEST-AGENT-ROUTES, TEST-SEARCH-REAL, TEST-PRIVACY-BOUND, TEST-UI-ESCALATE.
- **Verification result:** the recorded suite result is 25 passed and two skipped.
  The two skipped cases are the live SerpAPI and OpenAI-plus-search tests in
  `tests/test_live.py`, skipped because no provider keys were available. Replay and
  deterministic tests do not count as live provider evidence.
- **UI and boundary evidence:** Streamlit was smoke-checked in a browser with dummy
  keys. This verifies the local UI path only, not real OpenAI or SerpAPI integration.
  Security/privacy tests are included in the passing suite; no production or live
  deployment check was performed.
- **Rollback:** revert this cohesive PR. Runtime memory/ticket files are not
  source-controlled; do not delete them as an automatic rollback action.
- **Feedback and cohesion:** observed feedback is 25 passing tests, two skipped live
  tests (missing keys), and a browser UI smoke check with dummy keys. Replan if the
  installed AutoGen API changes, storage cannot maintain isolation, or the trust
  boundary expands. All modules are required for one working chat turn and were
  reviewed together.

## Coverage Map

| Parent obligation | Assigned owner | Evidence / pass condition |
| --- | --- | --- |
| FR-CHAT-CONTEXT, FR-CHAT-ROUTING, FR-SEARCH-REQUIRED, FR-MEMORY-REUSE, FR-MEMORY-PERSIST, FR-HUMAN-ESCALATION, FR-UI-CHATSTATE, FR-SECURITY-BOUNDARY, FR-COST-BOUNDS | PR-SUPPORT-BOTMVP | Focused pytest and end-to-end journey behavior pass |
| UC-SUPPORT-ASK, UC-SUPPORT-RECALL, UC-SUPPORT-ESCALATE | PR-SUPPORT-BOTMVP | All use cases are assigned to the integrated PR |
| NFR-PRIVACY-LOCAL, NFR-RELIABILITY-ERRORS, NFR-COST-LIMITS, NFR-UI-USABILITY | PR-SUPPORT-BOTMVP | Path/isolation/error/bounds tests pass; UI keyboard and narrow-width review passes |
| AT-SUPPORT-LIVE, AT-SUPPORT-MEMORY, AT-SUPPORT-HUMAN, AT-SUPPORT-UISECURITY, AT-SUPPORT-BOUNDS | PR-SUPPORT-BOTMVP | Black-box tests or explicit manual UI review pass |
| JT-SUPPORT-FOLLOWUP, JT-SUPPORT-HUMANPATH | PR-SUPPORT-BOTMVP | Ordered follow-up, memory, clarification, and escalation journey passes |
| COMP-UI, COMP-SERVICE, COMP-MEMORY, COMP-AGENTS, COMP-SEARCH, COMP-CONFIG | PR-SUPPORT-BOTMVP | Component tests and integrated `pytest -q` pass |
| TEST-MEMORY-COSINE, TEST-AGENT-ROUTES, TEST-SEARCH-REAL, TEST-PRIVACY-BOUND, TEST-UI-ESCALATE | PR-SUPPORT-BOTMVP | All obligations executed; live smoke passes or is explicitly recorded as skipped |

## Sequencing & Risks

This is a one-node graph: `PR-SUPPORT-BOTMVP`, with no predecessor or successor.
The PR integrates support modules, config, UI, local files, and tests before merge.
There are no parallel paths or external migrations. Risks include AutoGen API drift,
provider failures, unsafe filenames, local data exposure, and confusing UI states.
Stop and revise earlier documents if requirements change, shared hosting is added,
customer-data lifecycle needs change, or real API behavior invalidates the interfaces.
Do not deploy without explicit approval.

## Traceability

| Implementation item | Requirements | Acceptance / journey | Components | Design tests |
| --- | --- | --- | --- | --- |
| PR-SUPPORT-BOTMVP | FR-CHAT-CONTEXT, FR-CHAT-ROUTING, FR-SEARCH-REQUIRED, FR-MEMORY-REUSE, FR-MEMORY-PERSIST, FR-HUMAN-ESCALATION, FR-UI-CHATSTATE, FR-SECURITY-BOUNDARY, FR-COST-BOUNDS, NFR-PRIVACY-LOCAL, NFR-RELIABILITY-ERRORS, NFR-COST-LIMITS, NFR-UI-USABILITY | AT-SUPPORT-LIVE, AT-SUPPORT-MEMORY, AT-SUPPORT-HUMAN, AT-SUPPORT-UISECURITY, AT-SUPPORT-BOUNDS, JT-SUPPORT-FOLLOWUP, JT-SUPPORT-HUMANPATH | COMP-UI, COMP-SERVICE, COMP-MEMORY, COMP-AGENTS, COMP-SEARCH, COMP-CONFIG | TEST-MEMORY-COSINE, TEST-AGENT-ROUTES, TEST-SEARCH-REAL, TEST-PRIVACY-BOUND, TEST-UI-ESCALATE |