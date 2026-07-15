"""Lint the hook scripts for portability: they run under whatever python3
the user's machine ships, so syntax that crashes older interpreters at
import time must not sneak in — a crashed hook is a silently dead guard."""
import ast
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def annotations(tree):
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.returns:
            yield node.returns
        if isinstance(node, ast.arg) and node.annotation:
            yield node.annotation
        if isinstance(node, ast.AnnAssign):
            yield node.annotation


def test_pep604_annotations_need_future_import():
    """`X | None` annotations raise TypeError at import on Python 3.8/3.9
    unless `from __future__ import annotations` defers their evaluation."""
    for p in SCRIPTS.glob("*.py"):
        tree = ast.parse(p.read_text())
        if any(isinstance(n, ast.ImportFrom) and n.module == "__future__"
               for n in tree.body):
            continue
        for ann in annotations(tree):
            for sub in ast.walk(ann):
                assert not isinstance(sub, ast.BinOp), (
                    f"{p.name}: PEP-604 annotation without "
                    "`from __future__ import annotations`")
