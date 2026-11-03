"""Tests for Markdown runbook loading and BM25 retrieval in app/retrieval.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.retrieval import RunbookIndex, load_runbooks, parse_runbook_markdown

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_parse_runbook_markdown_inline_and_multiline_tags() -> None:
    inline_md = (
        "---\n"
        "id: rb-test-inline\n"
        "title: Inline Tag Runbook\n"
        "tags: [dns, network, active-directory]\n"
        "---\n"
        "## Symptoms\nDNS lookup fails."
    )
    rb1 = parse_runbook_markdown(inline_md)
    assert rb1.id == "rb-test-inline"
    assert rb1.title == "Inline Tag Runbook"
    assert rb1.tags == ["dns", "network", "active-directory"]

    multiline_md = (
        "---\r\n"
        "id: 'rb-test-multi'\r\n"
        'title: "Multiline Tag Runbook"\r\n'
        "tags:\r\n"
        "  - hyper-v\r\n"
        "  - virtualization\r\n"
        "---\r\n"
        "## Symptoms\r\nVM fails to start."
    )
    rb2 = parse_runbook_markdown(multiline_md)
    assert rb2.id == "rb-test-multi"
    assert rb2.tags == ["hyper-v", "virtualization"]


@pytest.mark.parametrize(
    "bad_markdown",
    [
        "No front matter here",
        "---\nid: rb-1\ntitle: Missing closing delimiter\ntags: [a]\nBody",
        "---\ntitle: Missing ID\ntags: [a]\n---\nBody",
        "---\nid: rb-1\ntags: [a]\n---\nBody",
        "---\nid: rb-1\ntitle: Empty tags\ntags: []\n---\nBody",
        "---\nid: rb-1\ntitle: Empty body\ntags: [a]\n---\n   \n",
    ],
)
def test_parse_runbook_rejects_malformed_front_matter(bad_markdown: str) -> None:
    with pytest.raises(ValueError):
        parse_runbook_markdown(bad_markdown)


def test_load_runbooks_rejects_duplicate_ids(tmp_path: Path) -> None:
    content = "---\nid: rb-dup\ntitle: Duplicate\ntags: [test]\n---\nBody text"
    (tmp_path / "one.md").write_text(content, encoding="utf-8")
    (tmp_path / "two.md").write_text(content, encoding="utf-8")

    with pytest.raises(ValueError, match="Duplicate runbook id"):
        load_runbooks(tmp_path)


def test_bm25_returns_top_3_ordered_with_scores(tmp_path: Path) -> None:
    docs = [
        ("1.md", "rb-dns", "DNS Failure", "[dns, nslookup]", "Workstation cannot resolve hostname."),
        ("2.md", "rb-vpn", "VPN Drops", "[vpn, ikev2]", "Remote tunnel disconnects every 10 minutes."),
        ("3.md", "rb-hv", "Hyper-V VM Start Failure", "[hyper-v, vhdx]", "Virtual machine will not power on."),
        ("4.md", "rb-prn", "Printer Stuck", "[printer, spooler]", "Print queue jobs stuck deleting."),
    ]
    for filename, rb_id, title, tags, body in docs:
        (tmp_path / filename).write_text(
            f"---\nid: {rb_id}\ntitle: {title}\ntags: {tags}\n---\n{body}",
            encoding="utf-8",
        )

    index = RunbookIndex.from_directory(tmp_path)
    results = index.search("hyperv virtual machine will not power on", top_k=3)

    assert len(results) == 3
    assert results[0].runbook.id == "rb-hv"
    assert results[0].score > results[1].score >= results[2].score


def test_production_runbooks_achieve_high_eval_retrieval_recall() -> None:
    index = RunbookIndex.from_directory()
    assert len(index.runbooks) == 18

    eval_tickets = json.loads((REPO_ROOT / "data" / "tickets_eval.json").read_text(encoding="utf-8"))
    covered = [item for item in eval_tickets if item["expected_runbook_id"] is not None]
    assert len(covered) == 17

    hits = 0
    for item in covered:
        top_ids = [sr.runbook.id for sr in index.search(item["ticket"], top_k=3)]
        if item["expected_runbook_id"] in top_ids:
            hits += 1

    assert hits == 17
