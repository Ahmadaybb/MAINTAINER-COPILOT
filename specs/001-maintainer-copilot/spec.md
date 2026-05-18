# Feature Specification: Maintainer's Copilot

**Feature Branch**: `001-maintainer-copilot`

**Created**: 2026-05-18

**Status**: Draft

**Input**: User description: "Build the Maintainer's Copilot — an authenticated chatbot an open-source maintainer uses to triage GitHub issues. It classifies issues (bug/feature/docs/question) using three compared models, extracts code-shaped entities, summarizes threads, answers questions via RAG over docs and resolved issues, carries short- and long-term memory, and is embeddable as a single-script-tag widget. Maintainers triage; admins invite users, configure widgets, and inspect memory."

## Clarifications

### Session 2026-05-18

- Q: How does the project's documentation and resolved-issue history get into the copilot? → A: Admin connects one GitHub repository; the system ingests that repo's docs (e.g., `/docs`, README) and its closed/resolved issues, then re-syncs on a schedule.
- Q: How does a maintainer authenticate when using the copilot through an embedded widget? → A: Host-app signed identity handoff — the host (which already authenticates its users) passes a short-lived signed token that the copilot verifies against the widget configuration.
- Q: What control does a maintainer have over their own long-term memory? → A: View and delete their own long-term memory entries; updates occur via newer facts superseding older ones (FR-014), not in-place editing.
- Q: Should there be a per-maintainer request/usage limit on copilot interactions? → A: Yes — a configurable per-maintainer rate limit; exceeding it returns a graceful "try again shortly" message with no crash or stack trace.
- Q: What is the retention lifecycle for long-term memory entries? → A: Indefinite — entries persist until explicitly deleted by the owning maintainer or an admin; no automatic expiry.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - One-Shot Issue Triage (Priority: P1)

A maintainer pastes a GitHub issue URL or raw issue text into the copilot and, in a single
response, receives: a classification label (bug, feature, docs, or question), a list of
code-shaped entities extracted from the text, and a concise summary of the issue thread.

**Why this priority**: This is the core value proposition and the smallest slice that delivers
a usable product. A maintainer can adopt the copilot for triage even if nothing else exists.

**Independent Test**: Submit a known issue (URL and, separately, pasted text) and verify the
response contains a single classification label, an entity list, and a summary — all in one
turn, without follow-up prompts.

**Acceptance Scenarios**:

1. **Given** an authenticated maintainer, **When** they paste a valid public GitHub issue URL,
   **Then** the copilot returns one classification label, extracted entities, and a thread
   summary in a single response.
2. **Given** an authenticated maintainer, **When** they paste raw issue text instead of a URL,
   **Then** the copilot returns the same three outputs from the text alone.
3. **Given** an issue whose content is ambiguous between two labels, **When** it is classified,
   **Then** the copilot returns its single best label and indicates the classification is
   low-confidence.
4. **Given** an issue URL that is unreachable or points to a private/non-existent issue,
   **When** submitted, **Then** the copilot returns a clear, non-technical explanation and no
   stack trace, and invites the maintainer to paste the text instead.

---

### User Story 2 - Authenticated Access Only (Priority: P2)

Only authenticated users can interact with the copilot. Unauthenticated visitors cannot reach
triage, chat, or memory functionality. Maintainers and admins are distinct roles with
different permissions.

**Why this priority**: The product is explicitly not a public chatbot. Every other story
depends on a known, authenticated identity (for memory ownership, audit, and access control),
so this is foundational and high priority.

**Independent Test**: Attempt to use any copilot capability without authenticating and confirm
access is denied; authenticate as a maintainer and confirm access is granted; confirm admin-only
actions are denied to a maintainer.

**Acceptance Scenarios**:

1. **Given** an unauthenticated request to any copilot capability, **When** it is made,
   **Then** access is denied and no copilot functionality executes.
2. **Given** a maintainer attempting an admin-only action, **When** they invoke it, **Then**
   the action is refused with a clear permission message and no stack trace.
3. **Given** an authenticated maintainer, **When** they open the copilot, **Then** they can
   triage issues and chat.

---

### User Story 3 - Grounded Follow-Up Q&A (Priority: P2)

After triaging or at any point in a conversation, a maintainer asks follow-up questions about
the issue or the codebase, and the copilot answers using the project's documentation and its
resolved issues as grounding, citing the sources it used.

**Why this priority**: Grounded answers turn the copilot from a one-shot classifier into an
ongoing assistant. It depends on US1/US2 but delivers distinct standalone value.

**Independent Test**: Ask a question whose answer exists in the configured docs/resolved
issues and verify the answer references those sources; ask a question with no grounding and
verify the copilot declines to fabricate.

**Acceptance Scenarios**:

1. **Given** a question answerable from the project's docs, **When** asked, **Then** the
   copilot answers and cites at least one supporting source.
2. **Given** a question answerable from a resolved issue, **When** asked, **Then** the copilot
   answers and cites that resolved issue.
3. **Given** a question with no supporting material in the corpus, **When** asked, **Then** the
   copilot states it lacks grounding rather than inventing an answer.

---

### User Story 4 - Conversational Memory (Priority: P2)

The copilot remembers context within the current session (short-term) and recalls relevant
facts the maintainer shared in earlier sessions (long-term), so the maintainer does not repeat
themselves across conversations.

**Why this priority**: Memory is a defining feature that materially improves day-to-day use,
but the product is still usable for triage without it, so it ranks below the core triage and
access stories.

**Independent Test**: Within one session, reference something stated earlier and confirm
recall; start a new session and confirm a fact from a prior session is recalled when relevant.

**Acceptance Scenarios**:

1. **Given** a fact stated earlier in the same session, **When** the maintainer refers back to
   it, **Then** the copilot uses it without being re-told.
2. **Given** a fact established in a prior session, **When** it becomes relevant in a new
   session, **Then** the copilot recalls it.
3. **Given** two conflicting remembered facts, **When** the topic arises, **Then** the copilot
   surfaces the most recent and notes the conflict rather than silently picking one.

---

### User Story 5 - Explicit "Remember This" (Priority: P2)

A maintainer can explicitly instruct the copilot to remember a specific fact, and that fact is
durably written to long-term memory and recalled in future sessions.

**Why this priority**: Explicit memory writes give the maintainer direct control over what
persists. It is closely related to US4 but is independently testable and valuable.

**Independent Test**: Tell the copilot to remember a specific fact, end the session, start a
new session, and confirm the fact is recalled when relevant.

**Acceptance Scenarios**:

1. **Given** a maintainer explicitly says to remember a fact, **When** they do, **Then** the
   copilot confirms it has been stored to long-term memory.
2. **Given** a previously remembered explicit fact, **When** a later session touches that
   topic, **Then** the copilot recalls it and attributes it as something the maintainer asked
   it to remember.
3. **Given** an explicit remember request that is ambiguous about what to store, **When**
   issued, **Then** the copilot asks a single clarifying question before storing.
4. **Given** a maintainer with stored long-term memory entries, **When** they list and delete
   one of their own entries, **Then** it is removed and never recalled in any later session;
   in-place editing is not offered (a newer fact supersedes an older one instead).

---

### User Story 6 - Admin Widget Configuration & Embed Snippet (Priority: P2)

An admin creates a widget configuration — theme, allowed origins, greeting message, and which
copilot tools are enabled — and receives a ready-to-paste embed snippet.

**Why this priority**: This unlocks distribution of the copilot into host applications. It is
independent of the chat stories and testable on its own.

**Independent Test**: As an admin, create a widget config, save it, and confirm a single embed
snippet is generated that reflects the configured values.

**Acceptance Scenarios**:

1. **Given** an authenticated admin, **When** they create a widget config with theme, allowed
   origins, greeting, and enabled tools, **Then** the config is saved and a single embed
   snippet is produced.
2. **Given** a saved widget config, **When** the admin edits the greeting or enabled tools,
   **Then** the embed snippet continues to work and reflects the updated configuration.
3. **Given** a widget config with an empty allowed-origins list, **When** saved, **Then** the
   admin is warned that the widget will not load anywhere until at least one origin is added.

---

### User Story 7 - One-Script-Tag Embed Styled by Config (Priority: P3)

A host application developer adds a single script tag to their page and the copilot widget
appears, styled and behaving according to the admin's widget configuration.

**Why this priority**: Delivers the embeddable end-user experience. Depends on US6 and is the
visible payoff of the widget pipeline, but the copilot is fully usable internally before this.

**Independent Test**: Add only the provided script tag to a sample page hosted on an allowed
origin and confirm the widget renders with the configured theme and greeting and no extra code.

**Acceptance Scenarios**:

1. **Given** a host page on an allowed origin, **When** the developer adds only the single
   provided script tag, **Then** the copilot widget appears with the configured theme and
   greeting and requires no additional code.
2. **Given** a widget rendered in a host page, **When** an authenticated maintainer uses it,
   **Then** only the tools enabled in the widget config are available.
3. **Given** a host page that supplies a valid short-lived signed identity token, **When** the
   widget loads, **Then** the maintainer is authenticated without any copilot login UI; **and**
   if the token is missing, malformed, or expired, access is denied with a clear message and
   no diagnostics.

---

### User Story 8 - Origin Allowlist Enforced by the Browser (Priority: P2)

When a host page on an origin that is NOT in the widget's allowlist tries to load the widget,
the browser blocks it; the protection does not rely solely on server-side checks.

**Why this priority**: This is a security guarantee for the embeddable surface. Misconfigured
or malicious embedding is a real risk, so it is prioritized above the convenience embed story.

**Independent Test**: Attempt to load the widget from an origin not in the allowlist and
confirm the browser prevents it from loading; confirm an allowed origin still works.

**Acceptance Scenarios**:

1. **Given** a host page whose origin is not in the widget's allowlist, **When** it attempts
   to load the widget, **Then** the browser blocks the widget from loading.
2. **Given** a host page on an allowlisted origin, **When** it loads the widget, **Then** the
   widget loads normally.
3. **Given** an allowlist change by an admin, **When** an origin is removed, **Then** new
   loads from that origin are blocked.

---

### User Story 9 - Admin User & Memory Oversight (Priority: P3)

An admin can invite new users and inspect stored memory for oversight and support.

**Why this priority**: Operational administration matters for real deployments but is not
required to demonstrate core copilot value, so it is lower priority.

**Independent Test**: As an admin, invite a new user and confirm they can subsequently
authenticate; inspect a maintainer's stored memory entries and confirm they are visible.

**Acceptance Scenarios**:

1. **Given** an authenticated admin, **When** they invite a user, **Then** that user can
   subsequently authenticate and use the copilot as a maintainer.
2. **Given** an authenticated admin, **When** they inspect memory, **Then** they can view
   stored long-term memory entries and their owners.
3. **Given** a maintainer (non-admin), **When** they attempt to inspect another user's memory,
   **Then** the action is refused.

---

### Edge Cases

- Issue URL is malformed, unreachable, rate-limited, or points to a private/deleted issue.
- Pasted issue text is empty, whitespace-only, or extremely long (exceeds processing limits).
- An issue is genuinely ambiguous between two classification labels.
- A follow-up question has no supporting material in the docs or resolved issues.
- Two long-term memories conflict (the maintainer said X earlier and Y later).
- An explicit "remember this" instruction does not clearly state what to remember.
- A backing tool (classification, retrieval, summarization, memory store, or the LLM) fails or
  times out mid-conversation.
- A widget configuration has an empty allowed-origins list.
- The widget is embedded on an origin not in the allowlist.
- An unauthenticated user attempts any copilot capability.
- The corpus of docs/resolved issues is empty or not yet ingested.
- The connected GitHub repository becomes unreachable, is made private, or lacks a docs
  location during a scheduled re-sync.
- The host-supplied identity token is missing, malformed, or expired when the widget loads.
- A maintainer deletes a long-term memory entry that is referenced earlier in the active
  conversation.
- A maintainer exceeds their configured per-maintainer rate limit mid-triage.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept an issue as either a GitHub issue URL or raw pasted text.
- **FR-002**: System MUST, in a single response, return a classification label (exactly one of
  bug, feature, docs, question), a list of extracted code-shaped entities, and a summary of the
  issue thread.
- **FR-003**: System MUST classify issues using a model selected as the best performer on a
  shared, fixed test set, where three candidate approaches (a classical machine-learning
  model, a fine-tuned transformer, and an LLM baseline) are evaluated on the identical test set
  and their results recorded.
- **FR-004**: System MUST indicate when a classification is low-confidence rather than
  presenting an uncertain label as definitive.
- **FR-005**: System MUST extract code-shaped entities (e.g., identifiers, file paths,
  function/symbol names, error strings) from issue text.
- **FR-006**: System MUST produce a concise summary of an issue thread.
- **FR-007**: System MUST answer maintainer follow-up questions using the project's
  documentation and its resolved issues as grounding.
- **FR-008**: System MUST cite the source(s) used for any grounded answer.
- **FR-009**: System MUST decline to answer (state lack of grounding) when no supporting
  material exists, rather than fabricating an answer.
- **FR-010**: System MUST maintain short-term memory scoped to the current conversation
  session.
- **FR-011**: System MUST maintain long-term memory that persists across sessions and is
  recalled when relevant.
- **FR-012**: System MUST allow a maintainer to explicitly instruct the copilot to remember a
  specific fact, and MUST durably persist that fact to long-term memory.
- **FR-013**: System MUST confirm to the maintainer when an explicit fact has been stored.
- **FR-014**: System MUST, when remembered facts conflict, surface the most recent and note
  the conflict.
- **FR-015**: System MUST require authentication for every copilot capability; no capability is
  available to unauthenticated users.
- **FR-016**: System MUST distinguish at least two roles — maintainer and admin — and enforce
  that admin-only actions are unavailable to maintainers.
- **FR-017**: Admins MUST be able to invite users who can then authenticate as maintainers.
- **FR-018**: Admins MUST be able to inspect stored long-term memory entries and their owners.
- **FR-019**: Admins MUST be able to create and edit a widget configuration consisting of
  theme, allowed origins, greeting message, and the set of enabled tools.
- **FR-020**: System MUST generate a single embeddable snippet for a widget configuration that
  a host developer can add with no additional code.
- **FR-021**: The embedded widget MUST render according to its configuration (theme, greeting)
  and expose only the tools enabled in that configuration.
- **FR-022**: System MUST cause the browser to block the widget from loading on any origin not
  present in the widget's allowed-origins list; enforcement MUST NOT rely solely on
  server-side checks.
- **FR-023**: System MUST behave as a single assistant that selects among tools — it MUST NOT
  be a multi-agent system and MUST NOT function as a workflow engine.
- **FR-024**: System MUST catch tool failures and recover gracefully within the conversation;
  a tool failure MUST NOT surface to the user as an error page, crash, or stack trace.
- **FR-025**: System MUST present all error conditions to users as clear, non-technical
  messages without exposing internal diagnostics.
- **FR-026**: System MUST warn an admin when a widget configuration would prevent the widget
  from loading anywhere (e.g., empty allowed-origins list).
- **FR-027**: System MUST record evaluation results for the three compared classification
  approaches so the chosen model's superiority on the shared test set is auditable.
- **FR-028**: System MUST allow an admin to connect exactly one GitHub repository as the
  knowledge source, and MUST ingest that repository's documentation (e.g., `/docs`, README)
  and its closed/resolved issues into the grounding corpus.
- **FR-029**: System MUST re-synchronize the connected repository's documentation and resolved
  issues on a configurable schedule, and MUST answer follow-up questions against the most
  recently synced corpus.
- **FR-030**: When the copilot is accessed through the embedded widget, the system MUST
  authenticate the maintainer via a short-lived signed identity token issued by the host
  application and MUST verify that token against the widget configuration before granting
  access; a missing, malformed, or expired token MUST deny access without exposing diagnostics.
- **FR-031**: System MUST allow a maintainer to list and delete their own long-term memory
  entries. In-place editing is NOT provided — corrections occur by storing a newer fact that
  supersedes the older one per FR-014.
- **FR-032**: System MUST enforce a configurable per-maintainer rate limit on copilot
  interactions; when a maintainer exceeds it, the system MUST return a graceful "try again
  shortly" message with no crash or stack trace.
- **FR-033**: System MUST retain long-term memory entries indefinitely until they are
  explicitly deleted by the owning maintainer or an admin; there MUST be no automatic expiry.

### Key Entities *(include if feature involves data)*

- **Maintainer**: An authenticated user who triages issues and chats with the copilot. Owns
  their own conversational and long-term memory.
- **Admin**: An authenticated user with maintainer capabilities plus the ability to invite
  users, configure widgets, and inspect memory.
- **Issue Submission**: The input to triage — a GitHub issue URL or raw text — and its derived
  outputs: classification label, extracted entities, and summary.
- **Conversation Session**: A single chat session, holding short-term memory for its duration.
- **Long-Term Memory Entry**: A persisted fact associated with an owner, an origin
  (inferred vs. explicitly requested), and a timestamp; recalled across sessions. Retained
  indefinitely until deleted by the owning maintainer or an admin; the owner can list and
  delete their own entries but not edit them in place.
- **Knowledge Source**: Exactly one connected GitHub repository's documentation (e.g.,
  `/docs`, README) and closed/resolved issues, ingested on connection and re-synced on a
  configurable schedule; used as grounding with attributable citations.
- **Host Identity Handoff**: A short-lived signed token issued by the host application and
  verified against the widget configuration to authenticate a maintainer inside the embedded
  widget.
- **Classification Evaluation Result**: For each of the three candidate approaches, the metrics
  obtained on the shared fixed test set, used to select and justify the production model.
- **Widget Configuration**: Theme, allowed origins, greeting, enabled tools, and the trust
  material used to verify the host application's signed identity tokens; produces a single
  embed snippet.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a pasted issue (URL or text), a maintainer receives classification, entities,
  and summary together in a single response within 15 seconds for at least 95% of requests.
- **SC-002**: All three classification approaches are scored on the identical fixed test set,
  results are recorded, and the production classifier meets/exceeds its committed macro-F1
  threshold (accuracy and per-class F1 recorded for audit) on that test set; a regression below
  threshold is detectable and blocks release.
- **SC-003**: At least 90% of grounded answers include at least one citation to the project's
  docs or resolved issues, and answers lacking any supporting source are explicitly flagged as
  ungrounded rather than presented as fact.
- **SC-004**: When an explicitly remembered fact is relevant in a later session, the copilot
  recalls it in at least 95% of such cases.
- **SC-005**: An admin can create a widget configuration and obtain a working embed snippet in
  under 3 minutes without assistance.
- **SC-006**: A host developer can make the widget appear by adding exactly one script tag and
  no other code.
- **SC-007**: 100% of widget load attempts from origins not in the allowlist are blocked by the
  browser.
- **SC-008**: 0% of unauthenticated requests succeed in invoking any copilot capability.
- **SC-009**: 100% of backing-tool failures during a conversation result in a graceful recovery
  message to the user, with zero user-visible crashes or stack traces.
- **SC-010**: 100% of admin-only actions attempted by a non-admin are refused.
- **SC-011**: 100% of interactions exceeding a maintainer's configured rate limit return a
  graceful throttle message, with zero crashes or stack traces.
- **SC-012**: After an admin connects a repository, the grounding corpus reflects that
  repository's docs and resolved issues, and at least 99% of scheduled re-syncs complete so
  the corpus reflects upstream changes within one configured sync interval.
- **SC-013**: Once a maintainer deletes a long-term memory entry, it is never surfaced again
  in any subsequent session (0% recall of deleted entries).

## Assumptions

- **Single-project deployment**: One deployment serves one open-source project; "the project's
  docs" and "resolved issues" refer to that single project's corpus. Multi-project tenancy is
  out of scope for this version.
- **Long-term memory is per-maintainer and private**: A maintainer's remembered facts are
  scoped to that maintainer and not shared with other maintainers; admins may inspect for
  oversight. Entries are retained indefinitely until the owning maintainer or an admin deletes
  them; the owner can list and delete (but not edit in place) their own entries.
- **GitHub issue ingestion is for public issues fetched without the maintainer's GitHub
  credentials**; private repositories and authenticated GitHub access are out of scope for
  this version. Maintainers can always paste raw text as a fallback.
- **Invite-only accounts**: There is no public self-service signup; users exist only after an
  admin invites them. Direct (non-embedded) access uses standard token-based session security;
  access through the embedded widget is authenticated by a host-application signed identity
  token verified against the widget configuration (no copilot login UI inside the widget).
- **Single connected repository as the knowledge source**: An admin connects exactly one
  GitHub repository; the copilot ingests that repo's docs and closed/resolved issues on
  connection and re-syncs on a configurable schedule. The copilot answers against the most
  recently synced corpus and degrades gracefully when the corpus is empty or a sync fails.
- **Production classifier = best performer on the golden set**: The model used for live triage
  is whichever of the three candidates scores highest on the shared test set, consistent with
  the project's evidence-based decision principle.
- **Prescribed platform constraints (from stakeholder and project constitution)**: short-term
  memory is held in an in-memory store, long-term memory in a vector-capable relational store,
  the widget is delivered as a single-script-tag front-end component, and origin enforcement is
  implemented via browser-enforced content security policy. These are recorded here as given
  constraints; concrete technology selection is deferred to planning.
- **Embedding/retrieval/chunking choices are evaluation-gated**: Any such choice is decided by
  measured performance on the golden set, per the project constitution.

## Dependencies

- Access to the project's documentation and resolved-issue history for grounding.
- A hosted secrets store and object storage are available for the runtime (per the project
  constitution); their absence prevents the service from operating.
- A reachable large language model provider for classification baseline, summarization, and
  tool-using chat.
