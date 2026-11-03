"""Markdown runbook loader and BM25 retrieval index."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from rank_bm25 import BM25L

DEFAULT_RUNBOOKS_DIR = Path(__file__).resolve().parent.parent / "data" / "runbooks"

_WORD_RE = re.compile(r"[a-z0-9]+")
_HYPHENATED_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)+")

_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "been",
        "but",
        "by",
        "can",
        "do",
        "does",
        "for",
        "from",
        "had",
        "has",
        "have",
        "he",
        "her",
        "here",
        "hi",
        "his",
        "how",
        "i",
        "if",
        "in",
        "into",
        "is",
        "it",
        "its",
        "me",
        "my",
        "of",
        "on",
        "or",
        "our",
        "out",
        "please",
        "she",
        "so",
        "than",
        "that",
        "the",
        "their",
        "them",
        "then",
        "there",
        "these",
        "they",
        "this",
        "to",
        "up",
        "us",
        "was",
        "we",
        "were",
        "what",
        "when",
        "where",
        "which",
        "who",
        "will",
        "with",
        "would",
        "you",
        "your",
    }
)


@dataclass(frozen=True)
class Runbook:
    """Parsed Markdown runbook with YAML front matter."""

    id: str
    title: str
    tags: list[str]
    body: str
    path: Path


@dataclass(frozen=True)
class ScoredRunbook:
    """A runbook paired with its BM25 relevance score."""

    runbook: Runbook
    score: float


def _strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1].strip()
    return value


def _parse_inline_list(raw: str) -> list[str]:
    inner = raw.strip()
    if inner.startswith("[") and inner.endswith("]"):
        inner = inner[1:-1].strip()
    if not inner:
        return []
    items = [_strip_quotes(part) for part in inner.split(",")]
    return [item for item in items if item]


def parse_runbook_markdown(content: str, source_path: Path | str = "<memory>") -> Runbook:
    """Parse a Markdown runbook containing front matter (id, title, tags) and body."""
    path_obj = Path(source_path)
    normalized = content.replace("\r\n", "\n").replace("\r", "\n").lstrip("\ufeff")
    lines = normalized.split("\n")

    if not lines or lines[0].strip() != "---":
        raise ValueError(f"Runbook '{path_obj}' is missing opening '---' front matter delimiter.")

    closing_idx: int | None = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            closing_idx = idx
            break

    if closing_idx is None:
        raise ValueError(f"Runbook '{path_obj}' is missing closing '---' front matter delimiter.")

    fm_lines = lines[1:closing_idx]
    body = "\n".join(lines[closing_idx + 1 :]).strip()
    if not body:
        raise ValueError(f"Runbook '{path_obj}' has an empty Markdown body.")

    metadata: dict[str, object] = {}
    current_list_key: str | None = None

    for raw_line in fm_lines:
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if stripped.startswith("- ") and current_list_key is not None:
            item_val = _strip_quotes(stripped[2:])
            if item_val:
                existing = metadata.setdefault(current_list_key, [])
                if isinstance(existing, list):
                    existing.append(item_val)
            continue

        current_list_key = None
        if ":" not in raw_line:
            raise ValueError(f"Malformed front matter line in '{path_obj}': {raw_line!r}")

        key, raw_val = raw_line.split(":", 1)
        key = key.strip()
        val = raw_val.strip()

        if key == "tags":
            if not val:
                metadata["tags"] = []
                current_list_key = "tags"
            else:
                metadata["tags"] = _parse_inline_list(val)
        else:
            metadata[key] = _strip_quotes(val)

    rb_id = metadata.get("id")
    title = metadata.get("title")
    tags = metadata.get("tags")

    if not isinstance(rb_id, str) or not rb_id:
        raise ValueError(f"Runbook '{path_obj}' is missing required front matter 'id'.")
    if not isinstance(title, str) or not title:
        raise ValueError(f"Runbook '{path_obj}' is missing required front matter 'title'.")
    if not isinstance(tags, list) or not tags:
        raise ValueError(f"Runbook '{path_obj}' must define a non-empty 'tags' list in front matter.")

    return Runbook(
        id=rb_id,
        title=title,
        tags=[str(tag) for tag in tags],
        body=body,
        path=path_obj,
    )


def load_runbooks(runbooks_dir: Path | str | None = None) -> list[Runbook]:
    """Load and validate all Markdown runbooks from a directory."""
    directory = Path(runbooks_dir) if runbooks_dir is not None else DEFAULT_RUNBOOKS_DIR
    if not directory.exists() or not directory.is_dir():
        raise FileNotFoundError(f"Runbooks directory does not exist: '{directory}'")

    md_files = sorted(directory.glob("*.md"))
    if not md_files:
        raise ValueError(f"No Markdown runbooks (*.md) found in '{directory}'.")

    runbooks: list[Runbook] = []
    seen_ids: set[str] = set()

    for md_path in md_files:
        text = md_path.read_text(encoding="utf-8")
        runbook = parse_runbook_markdown(text, source_path=md_path)
        if runbook.id in seen_ids:
            raise ValueError(f"Duplicate runbook id '{runbook.id}' found in '{md_path}'.")
        seen_ids.add(runbook.id)
        runbooks.append(runbook)

    return runbooks


def tokenize(text: str) -> list[str]:
    """Tokenize English IT ticket/runbook text for BM25 indexing and querying."""
    lowered = text.lower()
    raw_tokens = _WORD_RE.findall(lowered)
    if not raw_tokens:
        return []

    compound_tokens = [match.replace("-", "") for match in _HYPHENATED_RE.findall(lowered)]
    all_tokens = raw_tokens + compound_tokens
    filtered = [tok for tok in all_tokens if tok not in _STOPWORDS]
    return filtered if filtered else all_tokens


class RunbookIndex:
    """In-memory BM25 index over Markdown runbooks."""

    def __init__(self, runbooks: list[Runbook]) -> None:
        if not runbooks:
            raise ValueError("Cannot build RunbookIndex from an empty runbook list.")

        self.runbooks: list[Runbook] = list(runbooks)
        self.by_id: dict[str, Runbook] = {rb.id: rb for rb in self.runbooks}

        corpus: list[list[str]] = []
        for rb in self.runbooks:
            tags_text = " ".join(rb.tags)
            # Boost front-matter title and tags slightly over raw body text.
            combined = f"{rb.id} {rb.title} {rb.title} {tags_text} {tags_text}\n{rb.body}"
            tokens = tokenize(combined)
            if not tokens:
                raise ValueError(f"Runbook '{rb.id}' produced zero indexable tokens.")
            corpus.append(tokens)

        self._bm25 = BM25L(corpus)

    @classmethod
    def from_directory(cls, runbooks_dir: Path | str | None = None) -> RunbookIndex:
        """Load runbooks from disk and return a ready-to-query BM25 index."""
        return cls(load_runbooks(runbooks_dir))

    def search(self, query: str, top_k: int = 3) -> list[ScoredRunbook]:
        """Return top_k matching runbooks ordered by descending BM25 score."""
        if top_k <= 0:
            raise ValueError("top_k must be a positive integer.")

        limit = min(top_k, len(self.runbooks))
        query_tokens = tokenize(query)
        if not query_tokens:
            return [ScoredRunbook(runbook=rb, score=0.0) for rb in self.runbooks[:limit]]

        raw_scores = self._bm25.get_scores(query_tokens)
        scored = [
            ScoredRunbook(runbook=rb, score=float(score))
            for rb, score in zip(self.runbooks, raw_scores, strict=True)
        ]
        scored.sort(key=lambda item: (-item.score, item.runbook.id))
        return scored[:limit]
