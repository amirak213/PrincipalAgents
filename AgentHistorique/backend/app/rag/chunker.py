from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass
class GeneratedDocument:
    """Structured RAG document produced by the document builder."""

    source_type: str
    source_id: Decimal
    title: str
    language: str
    text: str
    metadata: dict[str, Any]


@dataclass
class ChunkDraft:
    """Chunk ready to be persisted in document_chunks."""

    source_type: str
    source_id: Decimal
    title: str
    language: str
    chunk_text: str
    metadata_json: dict[str, Any]


class DocumentChunker:
    """Split generated documents into sized chunks while preserving metadata."""

    def __init__(self, chunk_size: int = 1500, overlap: int = 150) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if overlap < 0:
            raise ValueError("overlap must be non-negative")
        if overlap >= chunk_size:
            raise ValueError("overlap must be smaller than chunk_size")

        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, document: GeneratedDocument) -> list[ChunkDraft]:
        text = document.text.strip()
        if not text:
            return []

        segments = self._split_text(text)
        chunk_count = len(segments)
        chunks: list[ChunkDraft] = []

        for index, segment in enumerate(segments):
            metadata = deepcopy(document.metadata)
            metadata.update(
                {
                    "source_type": document.source_type,
                    "source_id": float(document.source_id),
                    "title": document.title,
                    "language": document.language,
                    "chunk_index": index,
                    "chunk_count": chunk_count,
                    "chunk_role": (
                        "full"
                        if chunk_count == 1
                        else ("header" if index == 0 else "body")
                    ),
                }
            )
            chunks.append(
                ChunkDraft(
                    source_type=document.source_type,
                    source_id=document.source_id,
                    title=document.title,
                    language=document.language,
                    chunk_text=segment,
                    metadata_json=metadata,
                )
            )

        return chunks

    def chunk_many(self, documents: list[GeneratedDocument]) -> list[ChunkDraft]:
        all_chunks: list[ChunkDraft] = []
        for document in documents:
            all_chunks.extend(self.chunk(document))
        return all_chunks

    def _split_text(self, text: str) -> list[str]:
        if len(text) <= self.chunk_size:
            return [text]

        segments: list[str] = []
        start = 0
        text_length = len(text)

        while start < text_length:
            end = min(start + self.chunk_size, text_length)
            if end == text_length:
                segment = text[start:end].strip()
                if segment:
                    segments.append(segment)
                break

            split_at = self._find_split_point(text, start, end)
            segment = text[start:split_at].strip()
            if segment:
                segments.append(segment)

            if split_at >= text_length:
                break

            next_start = split_at - self.overlap if self.overlap else split_at
            if next_start <= start:
                next_start = split_at
            start = next_start

        return segments

    _HEADING_BREAK = re.compile(r"\n\n(?=[A-ZÀ-Ü][^\n]{0,80}\n)")

    def _find_split_point(self, text: str, start: int, end: int) -> int:
        window = text[start:end]
        min_split = max(int(len(window) * 0.5), 1)

        # Priorité : rupture de section/titre d'abord (pour ne pas couper un
        # chunk en plein milieu d'une section historique), puis paragraphe,
        # puis phrase, puis clause. Le premier séparateur trouvé dans la
        # bonne moitié de la fenêtre est utilisé.
        for separator in (
            self._HEADING_BREAK,
            "\n\n",
            "\n",
            ". ",
            "? ",
            "! ",
            "; ",
        ):
            position = self._rfind_separator(window, separator, min_split)
            if position is not None:
                return start + position

        return end

    def _rfind_separator(
        self, window: str, separator: str | re.Pattern[str], min_split: int
    ) -> int | None:
        if isinstance(separator, re.Pattern):
            matches = list(separator.finditer(window))
            for match in reversed(matches):
                if match.start() >= min_split:
                    return match.end()
            return None

        position = window.rfind(separator)
        if position >= min_split:
            return position + len(separator)
        return None
