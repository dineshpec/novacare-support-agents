<!-- sarathi:artifact-format version="2" -->

## Technical Approach

The product is a local Streamlit support chatbot. A small service coordinates
customer-scoped memory, AutoGen Swarm runs, SerpAPI search, escalation, and token
accounting. The UI owns presentation and current chat state. Deterministic search
compaction, ID sanitization, and similarity decisions stay in ordinary Python
functions; network, model, clock, and file effects remain explicit at module
boundaries. No database or service framework is needed for this single-process MVP.

A non-memory question is embedded once and checked against that customer's JSONL
records, then either returns a memory hit without a completion or starts the team.
Triage transfers supported questions to a specialist and replies directly with plain
text when clarification is needed or a topic is off-topic. Those triage replies use
the `clarify` source; there is no handoff to a `user` agent. Each invoked specialist
searches SerpAPI before answering; no useful result or low confidence can create an
escalation ticket. Only real specialist answers are saved.
See the aligned [design.html](./design.html) component view.

## Overview

Work Scope: product/system
Ready To Implement: Yes
Review Level: Standard
Extra Checks: security, privacy

The system boundary is the local Python/Streamlit application and its local text files.
The parent agent is implementing application code in parallel; no earlier product
baseline or runtime behavior is claimed. Shared-host access controls, remote storage,
production operations, and automated transcript retention are out of scope.

## Tech Stack

- Python, Streamlit, and `python-dotenv` configuration.
- Microsoft AutoGen AgentChat Swarm through `autogen-agentchat` and
  `autogen-ext[openai]`, version 0.4+.
- OpenAI `gpt-4o-mini` for triage/specialist completions and
  `text-embedding-3-small` for question embeddings.
- SerpAPI Google Search JSON endpoint over HTTPS.
- Local UTF-8 text transcript, JSONL memory index, and escalation text file.

Pin the versions selected during implementation and verify the installed AutoGen APIs;
the minimum version is not a complete compatibility guarantee.

## Drivers & Constraints

- Specialist answers require live search; memory hits skip completion and search except
  explicit refresh. Default cosine threshold is 0.88 and remains configurable.
- The service includes at most three recent exchanges, clipping each message to about
  300 characters. Each agent context buffers six messages. Compact search output to
  at most five results and about 2,500 characters. Specialists use one tool iteration
  with reflection; the OpenAI client uses `max_tokens=600` and `temperature=0.3`.
- SerpAPI uses HTTPS and a 20-second timeout. Search errors return a clear value and do
  not throw into the agent.
- `.env` holds credentials and is never committed. Memory contains customer questions,
  answers, and embeddings; assume a trusted local operator and filesystem permissions,
  not authenticated tenant isolation.
- UI distinguishes sources, agents, clarification, and escalation; controls are
  keyboard usable and layout remains legible at narrow width.

## Layers

Keep three direct responsibility areas, not a generic framework: Streamlit calls
`SupportService`; the service and focused modules own memory and orchestration decisions;
thin adapters perform OpenAI, AutoGen, SerpAPI, and local-file effects. The service
keeps UI code independent of AutoGen message internals.

## Components

### Streamlit chat presentation
<!-- sarathi:component id="COMP-UI" -->
`app.py` collects the customer ID and question, displays chat bubbles, agent/source
badges, memory refresh, token totals, clear-chat, and human-help controls. It maps a
`BotReply` to UI states and does not route topics or access customer files directly.
It realizes FR-UI-CHATSTATE and NFR-UI-USABILITY.

### Turn orchestration service
<!-- sarathi:component id="COMP-SERVICE" -->
`support_bot/service.py` implements `SupportService.answer(customer_id, question,
force_web=False)` and `BotReply`. It checks memory before team execution, supplies
recent history, saves only specialist answers, and aggregates usage. It realizes
FR-CHAT-CONTEXT, FR-MEMORY-REUSE, FR-MEMORY-PERSIST, and FR-COST-BOUNDS.

### Customer memory store
<!-- sarathi:component id="COMP-MEMORY" -->
`support_bot/memory.py` sanitizes customer IDs; reads/writes that customer's transcript
and JSONL records; embeds and compares questions through the injected embed function;
and returns recent history. It owns the local memory files and never selects another
customer's records. It realizes FR-MEMORY-REUSE, FR-MEMORY-PERSIST, and
NFR-PRIVACY-LOCAL.

### AutoGen specialist team
<!-- sarathi:component id="COMP-AGENTS" -->
`support_bot/agents.py` builds triage and four specialists in an AutoGen Swarm. Triage
has transfer handoffs to the four specialists and returns plain text directly for
clarification and off-topic replies. Specialists have web-search and escalation tools,
`BufferedChatCompletionContext(buffer_size=6)`, `max_tool_iterations=1`, and
`reflect_on_tool_use=True`. The run terminates on `MaxMessageTermination(10)` OR a
`TextMessageTermination(source=<agent name>)` for triage or any specialist; the task
itself is a user `TextMessage`, so no user handoff termination is used. Prompts use the
current date. It realizes FR-CHAT-ROUTING, FR-SEARCH-REQUIRED, and
FR-HUMAN-ESCALATION.

### Search adapter
<!-- sarathi:component id="COMP-SEARCH" -->
`support_bot/search.py` separates pure `compact_results` from
`serpapi_search(query, api_key)`. The adapter issues HTTPS GET to
`https://serpapi.com/search.json` with `engine=google` and a 20-second timeout, and
returns compact text or a clear error string. It realizes FR-SEARCH-REQUIRED and
NFR-RELIABILITY-ERRORS.

### Local configuration
<!-- sarathi:component id="COMP-CONFIG" -->
`support_bot/config.py` loads typed settings from environment and `.env`: keys, models,
threshold, memory directory, and history limit. `.env.example` contains placeholders;
missing-key messages do not reveal secret values. It realizes FR-SECURITY-BOUNDARY
and FR-COST-BOUNDS.

## Interfaces

### Service answer boundary
<!-- sarathi:interface id="IFACE-ANSWER" -->
Owner: COMP-SERVICE. Accepts customer ID, question, and optional force-web flag;
returns text, agent, source (`memory`, `web`, `clarify`, `escalated`, or `error`),
prompt/completion/embedding usage, and optional similarity. Both triage clarification
and off-topic text use `clarify`; off-topic is not a separate source. The UI's
Talk-to-a-human ticket message has the UI-only `human` source and is not a `BotReply`.
Failures are explicit, not success-shaped answers.

### Customer memory boundary
<!-- sarathi:interface id="IFACE-MEMORY" -->
Owner: COMP-MEMORY. A sanitized customer ID addresses only its `.txt` transcript and
`.jsonl` index under configured memory storage. Records contain question, answer,
topic/agent, timestamp, and embedding. File errors are explicit; append only a completed
specialist answer and matching transcript entry.

### Search boundary
<!-- sarathi:interface id="IFACE-SEARCH" -->
Owner: COMP-SEARCH. A query and API key produce compact text or an error string.
HTTP/network failures and empty useful results are explicit; the adapter never raises
an unhandled exception into AutoGen. The external contract is SerpAPI Google Search
JSON.

### Team and escalation boundary
<!-- sarathi:interface id="IFACE-TEAM" -->
Owner: COMP-AGENTS. The service supplies the question and bounded recent context; the
team returns a specialist answer, plain-text clarification or off-topic reply,
escalation, or explicit error. Both plain-text triage replies map to `clarify` in
`BotReply`. Escalation appends a ticket to `data/escalations.txt`, not memory. The
separate UI button creates a ticket and renders a message with source `human`.

## Core vs. Shell

The deterministic core comprises `compact_results`, customer-ID sanitization,
threshold comparison, memory eligibility, recent-history truncation, and reply/source
classification. The imperative shell comprises Streamlit events, timestamp creation,
HTTP, OpenAI calls, AutoGen execution, and file reads/writes. Pure functions and
injected collaborators enable isolated tests; tests also exercise service/module
composition.

## Key Flows

1. **Question:** UI calls the service. It embeds once and searches only the customer's
   history. A qualifying hit returns memory; otherwise it supplies bounded context and
   runs the Swarm.
2. **Routing and research:** triage transfers a supported question to one specialist.
   The specialist searches before composing an answer. Empty/unusable results or
   unreliable answers escalate rather than produce unsupported factual claims.
3. **Clarification and off-topic:** triage directly emits a plain-text message, without
   a handoff, for ambiguity or unsupported topics. The run ends on the first triage or
   specialist text message, or after ten messages. Both triage reply types have source
   `clarify`; a new customer submission starts the next service turn with recent
   conversation history.
4. **Persistence:** only a completed specialist answer is appended to both customer
   files. Clear-chat resets visible conversation only, not persistent files.
5. **Failure:** missing keys, provider errors, and file errors are explicit and never
   expose credentials. SerpAPI is bounded by its timeout. Do not save errors or
   escalation as specialist answers.

## Data Model

- **Customer identity:** normalize via one sanitization function before filename use;
  reject empty/unsafe-only IDs and keep storage below `data/memory`.
- **Memory index:** append-only JSONL records with question, answer, topic/agent,
  timestamp, and embedding. Malformed records produce a diagnostic and cannot become
  memory hits. No cross-customer index or shared database exists.
- **Transcript:** append-only readable `.txt` paired with index entries. Save both for
  a specialist answer; partial-write errors are visible.
- **Escalations:** append-only `data/escalations.txt`, separate from memory. No ticket
  status workflow or automated retention is included.
- **Privacy lifecycle:** local operator owns access/removal. Data is not encrypted by
  this design. Resolve retention and access controls before shared hosting or sensitive
  data use.

## Design Decisions

### Use file-backed customer memory
<!-- sarathi:decision id="DEC-FILEMEMORY" -->
Paired text and JSONL files satisfy the accepted readable transcript and per-customer
search needs without a database. Consequence: writes, partial failures, corruption,
retention, and concurrent access need local checks. Revisit for multiple workers or
shared hosting.

### Use one AutoGen Swarm
<!-- sarathi:decision id="DEC-AUTOGENSWARM" -->
Use the accepted AgentChat Swarm for specialist transfer and plain-text triage replies;
avoid another router framework and a user-agent handoff. Verify the installed 0.4+ API
and pin compatible versions.

### Bound prompt and tool work
<!-- sarathi:decision id="DEC-BOUNDEDWORK" -->
Keep triage concise and tool-free except handoffs, bound history/search, limit specialists
to one tool round, and cap completion tokens. This trades long context and broad search
excerpts for predictable work and recent context.

## Test Strategy

The implemented suite is organized as `tests/test_search.py`, `test_memory.py`,
`test_agents.py`, `test_service.py`, and `test_live.py`. Search, memory, and service
coverage uses deterministic fixtures; agent routing uses AutoGen's
`ReplayChatCompletionClient`. The suite result is 25 passed and two live tests skipped
because provider keys were unavailable. The live tests are marked to skip without
`OPENAI_API_KEY` and `SERPAPI_API_KEY`; mocked/replay tests do not prove provider
behavior.

### Similarity and customer-file isolation
<!-- sarathi:test id="TEST-MEMORY-COSINE" -->
Test below/at/above threshold, one-embedding lookup, per-customer isolation, ID
sanitization, transcript/JSONL shape, and exclusion of clarification/escalation/error
replies. Pass when records cannot cross customers and only specialist answers persist.
Covers COMP-MEMORY, COMP-SERVICE, FR-MEMORY-REUSE, FR-MEMORY-PERSIST,
NFR-PRIVACY-LOCAL, and DEC-FILEMEMORY.

### AutoGen handoffs and specialist paths
<!-- sarathi:test id="TEST-AGENT-ROUTES" -->
`tests/test_agents.py` uses `ReplayChatCompletionClient` to verify four-topic routing,
plain-text clarification and off-topic replies, search-before-answer order, and
escalation. Clarify replies use source `clarify`; off-topic replies also map to
`clarify`. The full local suite passed; both live tests were skipped without keys.
Covers
COMP-AGENTS, COMP-SERVICE, FR-CHAT-ROUTING, FR-SEARCH-REQUIRED,
FR-HUMAN-ESCALATION, UC-SUPPORT-ASK, UC-SUPPORT-ESCALATE, and DEC-AUTOGENSWARM.

### Search compaction and real provider boundary
<!-- sarathi:test id="TEST-SEARCH-REAL" -->
`tests/test_search.py` covers compaction and error formatting; `tests/test_live.py`
contains two real-boundary tests for SerpAPI search and OpenAI/search plus memory flow.
Both live tests were skipped because keys were unavailable, so authentication, quotas,
transport, and provider compatibility remain unverified. Covers COMP-SEARCH, COMP-AGENTS,
FR-SEARCH-REQUIRED, NFR-RELIABILITY-ERRORS, and RISK-BOUNDARYDRIFT.

### Secret handling and unsafe customer identifiers
<!-- sarathi:test id="TEST-PRIVACY-BOUND" -->
Test missing-key messages, placeholder-only `.env.example`, secret-free diagnostics,
traversal/separator IDs, and attempts to read another customer's records. Pass when
no secret appears in output/files and all memory paths stay under the configured
folder. Covers COMP-CONFIG, COMP-MEMORY, FR-SECURITY-BOUNDARY,
NFR-PRIVACY-LOCAL, and RISK-PRIVACY.

### UI source, usage, and human-help states
<!-- sarathi:test id="TEST-UI-ESCALATE" -->
The Streamlit UI was smoke-checked in a browser with dummy keys. It includes customer selection, clear-chat, badges, memory refresh,
usage, clarification, escalation, and talk-to-human. Pass when statuses and controls
are legible and keyboard usable; clear-chat does not remove memory. Covers COMP-UI,
FR-UI-CHATSTATE, NFR-UI-USABILITY, UC-SUPPORT-RECALL, and RISK-PRIVACY.

## Risks & Trade-offs

### Local memory may expose conversation data
<!-- sarathi:risk id="RISK-PRIVACY" -->
Transcript, answer, and embedding files are readable local data. Limit use to a trusted
operator, sanitize filenames, rely on filesystem permissions, and test isolation.
Shared hosting, sensitive/regulated data, or multi-user access requires stronger review
and explicit lifecycle/access-control design.

### External behavior may drift beyond fake-client evidence
<!-- sarathi:risk id="RISK-BOUNDARYDRIFT" -->
Verification risk: AutoGen, OpenAI, and SerpAPI may differ from replay or local test doubles. Pin installed
dependencies and run the optional real-boundary smoke test when keys exist. Without
credentials, auth, quotas, live network, and provider schemas remain unverified; this is
accepted for local development, not a claim of live integration success.

### Live search and model use are unpredictable
<!-- sarathi:risk id="RISK-COST" -->
Latency, quotas, and completion usage depend on providers. Keep timeouts, context/output
limits, one tool round, completion caps, and visible usage. Do not claim a cost ceiling
until numeric limits and actual provider usage are verified.

## Traceability

| Requirement / behavior | Components | Interfaces / decisions | Test obligations |
| --- | --- | --- | --- |
| FR-CHAT-CONTEXT, FR-CHAT-ROUTING, FR-SEARCH-REQUIRED, FR-HUMAN-ESCALATION | COMP-AGENTS, COMP-SERVICE, COMP-SEARCH | IFACE-TEAM, IFACE-SEARCH, IFACE-ANSWER, DEC-AUTOGENSWARM | TEST-AGENT-ROUTES, TEST-SEARCH-REAL |
| FR-MEMORY-REUSE, FR-MEMORY-PERSIST, NFR-PRIVACY-LOCAL | COMP-MEMORY, COMP-SERVICE | IFACE-MEMORY, DEC-FILEMEMORY | TEST-MEMORY-COSINE, TEST-PRIVACY-BOUND |
| FR-UI-CHATSTATE, NFR-UI-USABILITY | COMP-UI | IFACE-ANSWER | TEST-UI-ESCALATE |
| FR-SECURITY-BOUNDARY | COMP-CONFIG, COMP-MEMORY | IFACE-MEMORY | TEST-PRIVACY-BOUND |
| FR-COST-BOUNDS, NFR-RELIABILITY-ERRORS, NFR-COST-LIMITS | COMP-SEARCH, COMP-SERVICE, COMP-AGENTS | IFACE-SEARCH, DEC-BOUNDEDWORK | TEST-SEARCH-REAL |
| Risks | COMP-MEMORY, COMP-SEARCH, COMP-AGENTS | DEC-FILEMEMORY, DEC-AUTOGENSWARM | TEST-PRIVACY-BOUND, TEST-SEARCH-REAL |