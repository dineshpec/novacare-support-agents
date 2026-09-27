<!-- sarathi:artifact-format version="3" -->

## Product Overview

Customers need current, useful answers across AI topics, movie updates, sports, and
jobs. This local support chatbot combines live web results with recent conversation
context, remembers prior specialist answers separately for each customer, and offers
clarification or human escalation when automation is not enough. Success is a relevant,
clearly sourced answer or a clear next step; failures must not appear as verified facts.

The MVP is a Streamlit application for a trusted local operator, not an authenticated,
internet-facing multi-tenant service. OpenAI and SerpAPI credentials come from a local
`.env`; real credentials must never be committed.

Work Scope: product/system
Ready To Implement: Yes
Review Level: Standard
Extra Checks: security, privacy

## User Needs

### Get current answers in supported topics
<!-- sarathi:need id="UN-SUPPORT-CURRENTANSWERS" -->
Customers need useful, up-to-date answers about AI topics, movie updates, sports,
and jobs.

### Continue a conversation without repeating context
<!-- sarathi:need id="UN-SUPPORT-CONTINUITY" -->
Customers need follow-up questions to make sense and repeated questions to reuse
relevant prior answers for the same customer.

### Reach a person when automation is not enough
<!-- sarathi:need id="UN-SUPPORT-HUMANHELP" -->
Customers need clarification or human support when routing is unclear or an automated
answer cannot be established reliably.

## Non-Goals

- Supporting out-of-scope topics beyond a polite list of supported topics.
- Authentication, shared-host tenant isolation, production deployment, or live-agent
  messaging.
- Guaranteed accuracy of third-party web pages or an SLA for OpenAI or SerpAPI.
- Storing clarifications, escalations, off-topic replies, or errors as specialist answers.

## Features

### Current specialist answers
<!-- sarathi:feature id="FEAT-SUPPORT-ANSWERS" -->
Provides supported-topic answers based on specialist routing and current web research.
Derived from UN-SUPPORT-CURRENTANSWERS.

### Customer-scoped conversation memory
<!-- sarathi:feature id="FEAT-SUPPORT-MEMORY" -->
Provides recent context and reusable prior specialist answers for the selected customer.
Derived from UN-SUPPORT-CONTINUITY.

### Clarification and human escalation
<!-- sarathi:feature id="FEAT-SUPPORT-HELP" -->
Asks for clarification or records a support ticket when automation cannot proceed.
Derived from UN-SUPPORT-HUMANHELP.

## Use Cases

### Ask a supported-topic question
<!-- sarathi:use-case id="UC-SUPPORT-ASK" -->
A customer enters a name or ID and asks about a supported topic. The chatbot routes
the question, searches before a specialist answer, and uses recent context where
relevant. Unsupported topics receive a polite supported-topic list. If search fails,
the chatbot reports the failure or escalates rather than inventing current facts.

### Reuse or refresh a prior answer
<!-- sarathi:use-case id="UC-SUPPORT-RECALL" -->
A customer asks something similar to a question previously answered for that customer.
The saved answer is marked as memory and offers a web-refresh action. Another customer
cannot retrieve it. Refresh bypasses memory and performs a new specialist search.

### Clarify or request human help
<!-- sarathi:use-case id="UC-SUPPORT-ESCALATE" -->
When triage cannot choose a supported topic, it asks a clarifying question and ends
awaiting the reply. When a specialist cannot support a reliable answer, it records a
ticket and shows an escalation notice. A customer can also create a ticket directly.
None of these paths is stored as a specialist answer.

## Functional Requirements

### Use recent conversation context
<!-- sarathi:requirement id="FR-CHAT-CONTEXT" -->
For a non-memory turn, supply no more than the last three customer conversation
exchanges as context, truncating each exchange to approximately 300 characters.

### Route supported and unsupported topics
<!-- sarathi:requirement id="FR-CHAT-ROUTING" -->
Route supported questions to one of four specialists: AI topics, movie updates, sports,
or jobs. For unsupported topics, return a polite reply listing those topics without
claiming a specialist answer.

### Search before specialist answers
<!-- sarathi:requirement id="FR-SEARCH-REQUIRED" -->
Whenever a specialist is invoked for a non-memory answer, perform a live Google search
through SerpAPI before answering. Compact to at most five results and approximately
2,500 characters, retaining useful titles, snippets, links, and available answer-box,
sports, or top-stories highlights. A memory hit skips completion and search; explicit
refresh bypasses memory.

### Reuse customer-scoped answers and refresh on request
<!-- sarathi:requirement id="FR-MEMORY-REUSE" -->
Before running agents, embed the question with `text-embedding-3-small` and compare by
cosine similarity with that customer's saved questions. At or above the configurable
threshold (default 0.88), show the saved answer marked “From memory” and offer “Refresh
with web search.” A memory hit makes no chat-completion call; refresh forces a fresh
specialist answer.

### Persist only specialist answers
<!-- sarathi:requirement id="FR-MEMORY-PERSIST" -->
Append a readable transcript at `data/memory/<customer_id>.txt` and a JSONL index at
`data/memory/<customer_id>.jsonl`. Each index record contains question, answer,
topic/agent, timestamp, and embedding. Save only real specialist answers, not
clarifications, escalations, off-topic replies, or errors.

### Clarify and escalate when needed
<!-- sarathi:requirement id="FR-HUMAN-ESCALATION" -->
Unclear triage asks one clarifying question and ends awaiting the customer's reply. If
search has no useful result or the specialist cannot answer reliably, record a ticket
in `data/escalations.txt` and show an escalation notice. A “Talk to a human” control
also creates a ticket. Do not save these paths as specialist answers.

### Show chat state and token usage
<!-- sarathi:requirement id="FR-UI-CHATSTATE" -->
Let a customer enter a name or ID; show chat messages with agent and source labels,
clear-chat and human-help controls, and per-turn and session token usage. Clear-chat
resets visible chat only and does not delete persistent memory.

### Protect credentials and customer file paths
<!-- sarathi:requirement id="FR-SECURITY-BOUNDARY" -->
Read `OPENAI_API_KEY` and `SERPAPI_API_KEY` from local environment configuration;
provide placeholders only in `.env.example`; never log or persist secret values; and
sanitize customer IDs before using them in memory filenames.

### Bound model and search work
<!-- sarathi:requirement id="FR-COST-BOUNDS" -->
Keep triage short and tool-free except handoffs; limit specialists to one tool round;
cap completion tokens; and honor search limits above. A memory hit uses one embedding
call and skips chat completion and web search.

## Non-Functional Requirements

### Keep customer memory local and separated
<!-- sarathi:requirement id="NFR-PRIVACY-LOCAL" -->
Keep memory under local `data/memory` files. Customer IDs cannot escape that directory,
and lookups for one ID never return another customer's records. The MVP assumes a
trusted local operator and does not claim authenticated multi-tenant isolation or
encrypted-at-rest storage.

### Keep external failures visible and bounded
<!-- sarathi:requirement id="NFR-RELIABILITY-ERRORS" -->
Use HTTPS and a 20-second SerpAPI timeout. Transport, HTTP, or no-useful-results
failures produce a clear error or escalation, not an invented answer; search failures
do not escape as uncaught tool exceptions.

### Limit routine model and search usage
<!-- sarathi:requirement id="NFR-COST-LIMITS" -->
Apply context, result-count, result-text, tool-round, completion-token, and memory
short-circuit bounds on applicable turns. Show provider-reported usage; missing counts
must not be silently presented as measured zero usage.

### Keep the user interface usable
<!-- sarathi:requirement id="NFR-UI-USABILITY" -->
Clearly distinguish memory and web answers, clarification and escalation, and agent
ownership. Controls have readable labels and keyboard navigation; layout remains
legible at a narrow browser width.

## External Interfaces & Contracts

- **Microsoft AutoGen:** AgentChat and `autogen-ext[openai]` 0.4+ Swarm interfaces
  coordinate triage, specialist handoffs, user clarification, and termination. Verify
  installed versions against documented APIs and replay/client tests where feasible;
  an optional live OpenAI smoke test is the real provider check.
- **OpenAI:** `gpt-4o-mini` handles triage and specialist completions;
  `text-embedding-3-small` embeds questions. Credentials use `OPENAI_API_KEY`. A live
  smoke test is optional when configured; fakes do not prove authentication, quota, or
  response compatibility.
- **SerpAPI Google Search:** HTTPS GET to `https://serpapi.com/search.json` with
  `engine=google`, query, and API key; timeout 20 seconds. Return compact results or a
  clear error. An optional credentialed live test checks the boundary; local fake
  responses do not prove availability, quotas, or response drift.
- **Local files:** UTF-8 customer transcript and JSONL files plus escalation text are
  owned by the local process. Customer filename sanitization and lookup isolation are
  tested locally.

## Acceptance Tests

### A supported question gets a current, contextual answer
<!-- sarathi:acceptance id="AT-SUPPORT-LIVE" -->
Given a supported-topic question has no memory match, when the chatbot responds, then
the matching specialist searched live first, the answer is labeled web-sourced, and
context uses at most three bounded exchanges. Verify all four topics; an unsupported
topic instead gets the supported-topic list. Covers UC-SUPPORT-ASK, FR-CHAT-CONTEXT,
FR-CHAT-ROUTING, FR-SEARCH-REQUIRED, NFR-COST-LIMITS, and NFR-UI-USABILITY.

### A saved question is isolated and refreshable
<!-- sarathi:acceptance id="AT-SUPPORT-MEMORY" -->
Given a saved question meets the configured similarity threshold, when the same
customer asks again, then the answer is labeled “From memory,” no chat completion or
search runs, and refresh forces new web research. A second customer cannot retrieve
it. Check transcript/index fields and that only specialist answers are saved. Covers
UC-SUPPORT-RECALL, FR-MEMORY-REUSE, FR-MEMORY-PERSIST, and NFR-PRIVACY-LOCAL.

### Ambiguity and low confidence produce a human path
<!-- sarathi:acceptance id="AT-SUPPORT-HUMAN" -->
Given triage cannot choose a topic, then it asks for clarification and ends awaiting
reply. Given a specialist has no useful result or cannot answer reliably, then a
ticket is recorded and an escalation notice shown. The human-help control also creates
a ticket. None is saved as specialist memory. Covers UC-SUPPORT-ESCALATE,
FR-HUMAN-ESCALATION, FR-MEMORY-PERSIST, and NFR-RELIABILITY-ERRORS.

### Customer controls and credential handling are safe
<!-- sarathi:acceptance id="AT-SUPPORT-UISECURITY" -->
Given a customer uses the UI, selection, agent/source labels, clear-chat, human-help,
and per-turn/session usage are available with readable, keyboard-usable controls.
Unsafe filename characters cannot escape memory storage; missing credentials are
reported without exposing a secret. Covers FR-UI-CHATSTATE, FR-SECURITY-BOUNDARY,
NFR-PRIVACY-LOCAL, and NFR-UI-USABILITY.

### Search failures and resource limits are observable
<!-- sarathi:acceptance id="AT-SUPPORT-BOUNDS" -->
Given SerpAPI times out at its bound or returns no useful results, the request does not
hang beyond the timeout, tool exceptions do not escape into the agent, and the user
sees an error/escalation rather than fabricated facts. Verify result, tool-round,
completion-token, and memory-hit call bounds. Covers UC-SUPPORT-ASK,
FR-SEARCH-REQUIRED, FR-COST-BOUNDS, NFR-RELIABILITY-ERRORS, and NFR-COST-LIMITS.

## Journey Tests

### Continue a conversation and reuse an answer
<!-- sarathi:journey id="JT-SUPPORT-FOLLOWUP" -->
A customer selects an ID, gets a live-search answer, asks a context-dependent follow-up,
then repeats a similar question and sees a customer-scoped memory answer with refresh.
Compose AT-SUPPORT-LIVE and AT-SUPPORT-MEMORY.

### Clarify, research, and escalate
<!-- sarathi:journey id="JT-SUPPORT-HUMANPATH" -->
A customer asks an ambiguous question, responds to clarification with a supported topic,
then receives escalation when research is insufficient and can create a separate ticket.
Compose AT-SUPPORT-HUMAN and AT-SUPPORT-BOUNDS.

## Assumptions & Open Questions

- **Project entry:** greenfield MVP; no earlier product behavior is claimed. Code is
  being implemented in parallel by the parent agent.
- **Deployment:** trusted local operator. Before shared/internet-facing use, decide
  authentication, storage access controls, retention/deletion, and ticket operations.
- **Retention:** customer files persist until removed locally; automated deletion is not
  part of this MVP.
- **Low confidence:** specialists may escalate when results cannot support a reliable
  answer; make the decision explicit and testable without inventing a numeric threshold.
- **Review depth:** Standard suits a local MVP. Security and privacy checks apply because
  credentials and customer conversation data are handled. Shared hosting, authenticated
  access, regulated data, or destructive lifecycle changes require stronger review.
- **UI Mock Preference:** Optional. The design HTML is an architecture view, not an
  approved UI prototype.

## Traceability

| Need | Feature | Use case | Requirements | Acceptance / journey |
| --- | --- | --- | --- | --- |
| UN-SUPPORT-CURRENTANSWERS | FEAT-SUPPORT-ANSWERS | UC-SUPPORT-ASK | FR-CHAT-CONTEXT, FR-CHAT-ROUTING, FR-SEARCH-REQUIRED, FR-COST-BOUNDS | AT-SUPPORT-LIVE, AT-SUPPORT-BOUNDS, JT-SUPPORT-FOLLOWUP |
| UN-SUPPORT-CONTINUITY | FEAT-SUPPORT-MEMORY | UC-SUPPORT-RECALL | FR-MEMORY-REUSE, FR-MEMORY-PERSIST | AT-SUPPORT-MEMORY, JT-SUPPORT-FOLLOWUP |
| UN-SUPPORT-HUMANHELP | FEAT-SUPPORT-HELP | UC-SUPPORT-ESCALATE | FR-HUMAN-ESCALATION, FR-UI-CHATSTATE | AT-SUPPORT-HUMAN, AT-SUPPORT-UISECURITY, JT-SUPPORT-HUMANPATH |
| Cross-cutting | All | All | FR-SECURITY-BOUNDARY, NFR-PRIVACY-LOCAL, NFR-RELIABILITY-ERRORS, NFR-COST-LIMITS, NFR-UI-USABILITY | AT-SUPPORT-UISECURITY, AT-SUPPORT-BOUNDS |