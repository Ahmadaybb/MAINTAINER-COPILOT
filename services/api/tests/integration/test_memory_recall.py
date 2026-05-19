from __future__ import annotations

import asyncio
from types import SimpleNamespace
from uuid import uuid4

from app.domain.errors import ToolFailure
from app.domain.memory import MemorySource
from app.services.chat_service import ChatService


class FakeShortTermMemory:
    def __init__(self) -> None:
        self.messages: dict[str, list[dict]] = {}

    def load(self, session_id):
        return self.messages.get(str(session_id), [])

    def append(self, session_id, message: dict) -> list[dict]:
        messages = self.messages.setdefault(str(session_id), [])
        messages.append(message)
        return messages


class FakeLongTermMemory:
    def __init__(self) -> None:
        self.stored: list[str] = []
        self.conflict = False

    def write(self, *, owner_id, content: str, source: MemorySource = MemorySource.INFERRED, superseded_by=None):
        self.stored.append(content)
        return SimpleNamespace(content=content)

    def recall(self, *, owner_id, query: str, limit: int = 5):
        memories = [SimpleNamespace(content=item, superseded_by=None) for item in self.stored]
        if self.conflict:
            memories.append(SimpleNamespace(content="older package manager was npm", superseded_by=uuid4()))
        return SimpleNamespace(
            memories=memories[:limit],
            conflict_note="Older remembered facts may have been superseded; prefer the newest active fact."
            if self.conflict
            else None,
        )


class FakeTriage:
    async def triage(self, request, request_id: str):
        raise ToolFailure("Classifier failed during test.")


class FakeRag:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail

    async def answer(self, query):
        if self.fail:
            raise ToolFailure("RAG failed during test.")
        return SimpleNamespace(grounded=False, answer="", citations=[])


class FakeAnthropic:
    async def complete(self, *, system_prompt: str, user_prompt: str, max_tokens: int = 500) -> str:
        return f"Echo: {user_prompt}"


class FakeChatService(ChatService):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.persisted: list[dict] = []

    def create_session(self, user_id):
        return SimpleNamespace(session_id=uuid4())

    def _persist_message(self, *, session_id, role, content: str, tool_calls=None) -> None:
        self.persisted.append(
            {
                "session_id": session_id,
                "role": getattr(role, "value", str(role)),
                "content": content,
                "tool_calls": tool_calls or [],
            }
        )


def test_short_term_memory_recalls_within_session() -> None:
    asyncio.run(_assert_short_term_memory())


async def _assert_short_term_memory() -> None:
    stm = FakeShortTermMemory()
    service = FakeChatService(
        short_term_memory=stm,
        long_term_memory=FakeLongTermMemory(),
        triage=FakeTriage(),
        rag=FakeRag(),
        anthropic=FakeAnthropic(),
    )
    user_id = uuid4()
    session_id = uuid4()

    await service.send_message(session_id=session_id, user_id=user_id, content="hello", request_id="req-1")
    await service.send_message(session_id=session_id, user_id=user_id, content="continue", request_id="req-2")

    messages = stm.load(session_id)
    assert any(message["role"] == "user" and message["content"] == "hello" for message in messages)
    assert len(messages) == 4


def test_long_term_memory_recalls_across_sessions_and_surfaces_conflict() -> None:
    asyncio.run(_assert_long_term_memory())


async def _assert_long_term_memory() -> None:
    ltm = FakeLongTermMemory()
    service = FakeChatService(
        short_term_memory=FakeShortTermMemory(),
        long_term_memory=ltm,
        triage=FakeTriage(),
        rag=FakeRag(),
        anthropic=FakeAnthropic(),
    )
    user_id = uuid4()

    first = await service.send_message(
        session_id=uuid4(),
        user_id=user_id,
        content="remember preferred package manager is uv",
        request_id="req-1",
    )
    assert "remember" in first.message.content.lower()

    ltm.conflict = True
    second = await service.send_message(
        session_id=uuid4(),
        user_id=user_id,
        content="what package manager do I prefer?",
        request_id="req-2",
    )
    assert "preferred package manager is uv" in second.message.content
    assert "superseded" in second.message.content


def test_tool_failure_recovers_in_conversation_without_stack_trace() -> None:
    asyncio.run(_assert_tool_failure_recovery())


async def _assert_tool_failure_recovery() -> None:
    service = FakeChatService(
        short_term_memory=FakeShortTermMemory(),
        long_term_memory=FakeLongTermMemory(),
        triage=FakeTriage(),
        rag=FakeRag(fail=True),
        anthropic=FakeAnthropic(),
    )

    response = await service.send_message(
        session_id=uuid4(),
        user_id=uuid4(),
        content="I see an error in parser.py",
        request_id="req-1",
    )

    assert "failed" in response.message.content.lower() or "continue" in response.message.content.lower()
    assert any(call.ok is False for call in response.message.tool_calls)
    assert "Traceback" not in response.model_dump_json()
