from __future__ import annotations

import re
from uuid import UUID

from app.domain.knowledge import DocumentChunk
from app.infra.github_ingest import IngestedDocument


class Chunker:
    def chunk(
        self,
        *,
        source_id: UUID,
        documents: list[IngestedDocument],
        embedding_model: str,
        max_chars: int = 1200,
        overlap_chars: int = 150,
    ) -> list[DocumentChunk]:
        chunks: list[DocumentChunk] = []
        for document in documents:
            sections = _split_markdown_sections(document.content)
            chunk_index = 0
            for section_title, content in sections:
                for text in _split_with_overlap(content, max_chars=max_chars, overlap_chars=overlap_chars):
                    if not text.strip():
                        continue
                    title = section_title or document.title
                    chunks.append(
                        DocumentChunk(
                            source_id=source_id,
                            kind=document.kind,
                            external_ref=document.external_ref,
                            title=title,
                            content=text.strip(),
                            chunk_index=chunk_index,
                            issue_type=document.issue_type,
                            issue_date=document.issue_date,
                            resolution_status=document.resolution_status,
                            embedding_model=embedding_model,
                        )
                    )
                    chunk_index += 1
        return chunks


def _split_markdown_sections(text: str) -> list[tuple[str | None, str]]:
    sections: list[tuple[str | None, str]] = []
    current_title: str | None = None
    current_lines: list[str] = []
    for line in text.splitlines():
        if line.startswith("#"):
            if current_lines:
                sections.append((current_title, "\n".join(current_lines)))
            current_title = line.strip("# ").strip() or current_title
            current_lines = []
        else:
            current_lines.append(line)
    if current_lines:
        sections.append((current_title, "\n".join(current_lines)))
    return sections or [(None, text)]


def _split_with_overlap(text: str, *, max_chars: int, overlap_chars: int) -> list[str]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(current) + len(paragraph) + 2 <= max_chars:
            current = f"{current}\n\n{paragraph}".strip()
            continue
        if current:
            chunks.append(current)
        while len(paragraph) > max_chars:
            chunks.append(paragraph[:max_chars])
            paragraph = paragraph[max_chars - overlap_chars :]
        current = paragraph
    if current:
        chunks.append(current)
    return chunks
