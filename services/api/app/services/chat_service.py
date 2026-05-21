from __future__ import annotations

from pathlib import Path
from typing import Any, TYPE_CHECKING
from uuid import UUID

from app.domain.errors import NotFoundError, ToolFailure
from app.domain.memory import (
    ChatAssistantMessage,
    ChatMessageResponse,
    ChatSessionResponse,
    ChatToolCall,
    MessageRole,
)
from app.domain.triage import TriageRequest
from app.infra.groq import GroqClient
from app.infra.redaction import redact, redact_text

if TYPE_CHECKING:
    from app.repositories.models.memory import MessageRole as OrmMessageRole
    from app.services.long_term_memory import LongTermMemoryService
    from app.services.rag_service import RagService
    from app.services.short_term_memory import ShortTermMemory
    from app.services.triage_service import TriageService

CHAT_SYSTEM_PROMPT = Path(__file__).resolve().parents[4] / "prompts" / "chat_system.md"


class ChatService:
    def __init__(
        self,
        *,
        short_term_memory: ShortTermMemory | None = None,
        long_term_memory: LongTermMemoryService | None = None,
        triage: TriageService | None = None,
        rag: RagService | None = None,
        llm: GroqClient | None = None,
    ) -> None:
        if short_term_memory is None:
            from app.services.short_term_memory import ShortTermMemory

            short_term_memory = ShortTermMemory()
        if long_term_memory is None:
            from app.services.long_term_memory import LongTermMemoryService

            long_term_memory = LongTermMemoryService()
        if triage is None:
            from app.services.triage_service import TriageService

            triage = TriageService()
        if rag is None:
            from app.services.rag_service import RagService

            rag = RagService()
        self.short_term_memory = short_term_memory
        self.long_term_memory = long_term_memory
        self.triage = triage
        self.rag = rag
        self.llm = llm or GroqClient()

    def create_session(self, user_id: UUID) -> ChatSessionResponse:
        from app.repositories.db import get_sessionmaker
        from app.repositories.memory import ConversationRepository

        with get_sessionmaker()() as session:
            conversation = ConversationRepository(session).create_session(user_id=user_id)
            session.commit()
            return ChatSessionResponse(session_id=conversation.id)

    async def send_message(
        self,
        *,
        session_id: UUID,
        user_id: UUID,
        content: str,
        request_id: str,
    ) -> ChatMessageResponse:
        redacted_content = redact_text(content)
        self._persist_message(session_id=session_id, role="user", content=redacted_content)
        self.short_term_memory.append(session_id, {"role": "user", "content": redacted_content})

        tool_calls: list[ChatToolCall] = []
        notes: list[str] = []

        recalled = self.long_term_memory.recall(owner_id=user_id, query=redacted_content)
        if recalled.memories:
            notes.append("I found related remembered context: " + "; ".join(memory.content for memory in recalled.memories[:2]))
        if recalled.conflict_note:
            notes.append(recalled.conflict_note)

        if _should_remember(redacted_content):
            try:
                memory_text = _memory_content(redacted_content)
                result = self.long_term_memory.write_memory_tool(
                    owner_id=user_id,
                    content=memory_text,
                )
                tool_calls.append(ChatToolCall(name="write_memory", ok=result.status == "stored"))
                notes.append(result.clarifying_question or "I will remember that.")
            except ToolFailure as exc:
                tool_calls.append(ChatToolCall(name="write_memory", ok=False, note=exc.message))
                notes.append("I could not store that memory, but we can keep going.")

        if _looks_like_issue(redacted_content):
            try:
                triage = await self.triage.triage(
                    TriageRequest(issue_text=redacted_content),
                    request_id=request_id,
                )
                tool_calls.extend(
                    [
                        ChatToolCall(name="classify_issue", ok=triage.classification is not None),
                        ChatToolCall(name="extract_entities", ok=True),
                        ChatToolCall(name="summarize_issue", ok=triage.summary is not None),
                    ]
                )
                if triage.classification:
                    notes.append(f"Classification: {triage.classification.label}.")
                if triage.summary:
                    notes.append(triage.summary)
            except ToolFailure as exc:
                tool_calls.append(ChatToolCall(name="classify_issue", ok=False, note=exc.message))
                notes.append("One triage tool failed, but I can still continue the conversation.")

        should_use_rag = _should_use_rag(redacted_content)
        try:
            from app.domain.knowledge import RagQuery

            rag_answer = await self.rag.answer(RagQuery(question=redacted_content))
            if should_use_rag or rag_answer.grounded:
                tool_calls.append(ChatToolCall(name="rag_search", ok=rag_answer.grounded))
            if rag_answer.grounded:
                notes.append(rag_answer.answer)
        except (NotFoundError, ToolFailure) as exc:
            if should_use_rag:
                tool_calls.append(ChatToolCall(name="rag_search", ok=False, note=getattr(exc, "message", str(exc))))
                notes.append("I do not have grounded repository context for that yet.")

        if not notes:
            notes.append(await self._plain_response(redacted_content))

        response_text = "\n\n".join(notes)
        safe_tool_calls = [call.model_dump() for call in tool_calls]
        self._persist_message(
            session_id=session_id,
            role="assistant",
            content=response_text,
            tool_calls=safe_tool_calls,
        )
        self.short_term_memory.append(
            session_id,
            {"role": "assistant", "content": response_text, "tool_calls": redact(safe_tool_calls)},
        )
        return ChatMessageResponse(
            message=ChatAssistantMessage(content=response_text, tool_calls=tool_calls),
        )

    def _persist_message(
        self,
        *,
        session_id: UUID,
        role,
        content: str,
        tool_calls: list[dict[str, Any]] | None = None,
    ) -> None:
        from app.repositories.db import get_sessionmaker
        from app.repositories.memory import ConversationRepository
        from app.repositories.models.memory import MessageRole as OrmMessageRole

        with get_sessionmaker()() as session:
            repo = ConversationRepository(session)
            if not repo.get_session(session_id):
                raise NotFoundError("Conversation session was not found.")
            repo.add_message(
                session_id=session_id,
                role=OrmMessageRole(getattr(role, "value", role)),
                content=redact_text(content),
                tool_calls=redact(tool_calls) if tool_calls else None,
            )
            session.commit()

    async def _plain_response(self, content: str) -> str:
        prompt = CHAT_SYSTEM_PROMPT.read_text(encoding="utf-8")
        try:
            return await self.llm.complete(
                system_prompt=prompt,
                user_prompt=content,
                max_tokens=500,
            )
        except ToolFailure:
            return "I can keep helping, but the language model is temporarily unavailable."


def _should_remember(content: str) -> bool:
    lowered = content.strip().lower()
    explicit_prefixes = (
        "remember:",
        "remember ",
        "please remember",
        "save this:",
        "save this ",
        "store this:",
        "store this ",
        "note that",
    )
    return any(lowered.startswith(prefix) for prefix in explicit_prefixes)


def _memory_content(content: str) -> str:
    stripped = content.strip()
    lowered = stripped.lower()
    prefixes = (
        "please remember",
        "remember",
        "save this",
        "store this",
        "note that",
    )
    for prefix in prefixes:
        if lowered.startswith(prefix):
            return stripped[len(prefix) :].strip(" :,-")
    return stripped


def _looks_like_issue(content: str) -> bool:
    markers = ("error", "bug", "traceback", "exception", "feature", "docs", "issue")
    return any(marker in content.lower() for marker in markers)


def _should_use_rag(content: str) -> bool:
    lowered = content.lower()
    knowledge_markers = (
        "project",
        "repo",
        "repository",
        "docs",
        "documentation",
        "readme",
        "rag",
        "knowledge",
        "retry policy",
        "widget",
        "api",
        "service",
        "architecture",
        "how does",
        "how do",
        "what does",
        "what are the main",
        "explain",
        "use project knowledge",
    )
    return any(marker in lowered for marker in knowledge_markers)
