"""Detector for TODO/FIXME/placeholder patterns and empty function bodies."""

import ast
import re
from dataclasses import dataclass, field
from typing import List, Optional

# Patterns that indicate incomplete or placeholder code
PLACEHOLDER_COMMENT_PATTERNS = [
    (r"#\s*TODO[:\s]", "TODO comment"),
    (r"#\s*FIXME[:\s]", "FIXME comment"),
    (r"#\s*HACK[:\s]", "HACK comment"),
    (r"#\s*XXX[:\s]", "XXX (needs attention) comment"),
    (r"#\s*NOQA", "NOQA suppression"),
    (r"#\s*type:\s*ignore", "type: ignore suppression"),
    (r"#\s*pragma:\s*no\s*cover", "coverage suppression"),
    (r"#\s*placeholder", "placeholder comment"),
    (r"#\s*stub", "stub comment"),
    (r"#\s*not\s+implemented", "not implemented comment"),
    (r"#\s*fill\s+(this\s+)?in", "fill-in comment"),
    (r"#\s*implement\s+(this|me|later)", "implement later comment"),
    (r"#\s*your\s+code\s+here", "your code here comment"),
    (r"#\s*add\s+your\s+", "add your X comment"),
    (r"#\s*coming\s+soon", "coming soon comment"),
    (r"#\s*to\s+be\s+implemented", "to be implemented comment"),
    (r"#\s*tbd\b", "TBD comment"),
]


@dataclass
class DetectorResult:
    """Result from a single detector run."""

    score: float
    findings: List[str] = field(default_factory=list)
    detector_name: str = "unknown"


def _has_only_pass_or_ellipsis(body: List[ast.stmt]) -> bool:
    """Return True if the function/class body is only `pass`, `...`, or docstring."""
    meaningful = []
    for stmt in body:
        if isinstance(stmt, ast.Pass):
            continue
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
            # Could be a docstring (str) or ellipsis
            if isinstance(stmt.value.value, str) or stmt.value.value is ...:
                continue
        meaningful.append(stmt)
    return len(meaningful) == 0


def _count_placeholder_comments(content: str) -> List[dict]:
    """Find all placeholder comments with their line numbers."""
    results = []
    for lineno, line in enumerate(content.splitlines(), start=1):
        stripped = line.strip()
        for pattern, label in PLACEHOLDER_COMMENT_PATTERNS:
            if re.search(pattern, stripped, re.IGNORECASE):
                results.append({"line": lineno, "label": label, "text": stripped[:80]})
                break  # only count once per line
    return results


def detect(filepath: str, content: str, ast_tree: Optional[ast.AST] = None) -> DetectorResult:
    """Detect TODO/placeholder patterns and empty function bodies."""
    findings: List[str] = []

    # Text-based placeholder detection (works for all file types)
    placeholder_hits = _count_placeholder_comments(content)
    if placeholder_hits:
        labels = [h["label"] for h in placeholder_hits]
        label_counts: dict = {}
        for label in labels:
            label_counts[label] = label_counts.get(label, 0) + 1

        summary = ", ".join(f"{count}x {label}" for label, count in label_counts.items())
        findings.append(f"Placeholder/incomplete markers: {summary}")
        for hit in placeholder_hits[:5]:
            findings.append(f"  Line {hit['line']}: {hit['text']}")
        if len(placeholder_hits) > 5:
            findings.append(f"  ... and {len(placeholder_hits) - 5} more")

    # AST-based detection for Python files
    empty_functions: List[str] = []
    pass_only_functions: List[str] = []
    raise_not_implemented: List[str] = []

    if filepath.endswith(".py"):
        if ast_tree is None:
            try:
                ast_tree = ast.parse(content)
            except SyntaxError:
                score = min(1.0, len(placeholder_hits) * 0.08)
                return DetectorResult(score=score, findings=findings, detector_name="placeholders")

        for node in ast.walk(ast_tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            func_name = node.name

            if _has_only_pass_or_ellipsis(node.body):
                # Check if it's truly empty vs. an abstract stub
                has_docstring = (
                    node.body
                    and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)
                )
                if has_docstring and len(node.body) == 1:
                    empty_functions.append(func_name)
                elif not has_docstring:
                    pass_only_functions.append(func_name)

            # Check for `raise NotImplementedError` as only meaningful statement
            raises_nie = False
            for stmt in node.body:
                if isinstance(stmt, ast.Raise) and stmt.exc is not None:
                    exc = stmt.exc
                    if isinstance(exc, ast.Call) and isinstance(exc.func, ast.Name):
                        if exc.func.id == "NotImplementedError":
                            raises_nie = True
                    elif isinstance(exc, ast.Name) and exc.id == "NotImplementedError":
                        raises_nie = True
            if raises_nie:
                raise_not_implemented.append(func_name)

    if empty_functions:
        findings.append(f"Empty functions (docstring only): {', '.join(empty_functions)}")

    if pass_only_functions:
        findings.append(f"Empty function bodies (pass/... only): {', '.join(pass_only_functions)}")

    if raise_not_implemented:
        findings.append(f"Stub functions (raise NotImplementedError): {', '.join(raise_not_implemented)}")

    # Score calculation
    placeholder_penalty = min(0.5, len(placeholder_hits) * 0.06)
    empty_func_penalty = min(0.3, len(empty_functions) * 0.08)
    pass_func_penalty = min(0.3, len(pass_only_functions) * 0.1)
    stub_penalty = min(0.2, len(raise_not_implemented) * 0.07)

    score = min(1.0, placeholder_penalty + empty_func_penalty + pass_func_penalty + stub_penalty)

    return DetectorResult(score=score, findings=findings, detector_name="placeholders")
