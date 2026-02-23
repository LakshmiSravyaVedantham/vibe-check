"""Detector for suspicious docstring-to-code ratio."""

import ast
import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class DetectorResult:
    """Result from a single detector run."""

    score: float
    findings: List[str] = field(default_factory=list)
    detector_name: str = "unknown"


def _count_lines(text: str) -> int:
    """Count non-empty lines in a string."""
    return len([line for line in text.splitlines() if line.strip()])


def _extract_docstrings(tree: ast.AST) -> List[str]:
    """Extract all docstring contents from the AST."""
    docstrings = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
            if (
                node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)
            ):
                docstrings.append(node.body[0].value.value)
    return docstrings


def _count_comment_lines(content: str) -> int:
    """Count lines that are purely comments."""
    count = 0
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            count += 1
    return count


def _count_code_lines(content: str) -> int:
    """Count lines that contain actual code (not blank, not pure comments, not pure docstrings)."""
    in_multiline_string = False
    multiline_delim = None
    code_lines = 0

    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue

        # Rough multi-line string tracking
        if not in_multiline_string:
            for delim in ('"""', "'''"):
                count = stripped.count(delim)
                if count == 1:
                    in_multiline_string = True
                    multiline_delim = delim
                    break
                elif count >= 2:
                    # Inline docstring, not a code line unless there's other content
                    break
            else:
                code_lines += 1
        else:
            if multiline_delim and multiline_delim in stripped:
                in_multiline_string = False
                multiline_delim = None

    return code_lines


def _is_docstring_boilerplate(docstring: str) -> bool:
    """Check if a docstring looks like boilerplate AI filler text."""
    filler_patterns = [
        r"this\s+(function|method|class|module)\s+(handles|processes|manages|provides|performs|does)",
        r"(handles|processes|manages)\s+the\s+\w+",
        r"a\s+(simple|basic|utility)\s+(function|class|method)\s+(to|that|for)\s+",
        r"this\s+is\s+(a|the)\s+(main|primary|core)\s+(function|class)",
        r"(initializes|sets\s+up)\s+the\s+(class|object|instance)",
        r"returns?\s+the\s+(result|output|value|data)",
        r"(takes|accepts)\s+(a|an|the)\s+\w+\s+as\s+(input|parameter|argument)",
    ]
    doc_lower = docstring.lower()
    return any(re.search(p, doc_lower) for p in filler_patterns)


def detect(filepath: str, content: str, ast_tree: Optional[ast.AST] = None) -> DetectorResult:
    """Detect suspicious docstring-to-code ratio."""
    findings: List[str] = []

    if not filepath.endswith(".py"):
        # For non-Python files, check comment density only
        comment_lines = _count_comment_lines(content)
        total_nonblank = sum(1 for ln in content.splitlines() if ln.strip())
        if total_nonblank == 0:
            return DetectorResult(score=0.0, findings=[], detector_name="ratio")
        comment_ratio = comment_lines / total_nonblank
        if comment_ratio > 0.5:
            findings.append(f"High comment ratio in non-Python file: {comment_ratio:.1%}")
        score = min(1.0, max(0.0, (comment_ratio - 0.3) * 1.5))
        return DetectorResult(score=score, findings=findings, detector_name="ratio")

    if ast_tree is None:
        try:
            ast_tree = ast.parse(content)
        except SyntaxError:
            return DetectorResult(score=0.0, findings=[], detector_name="ratio")

    docstrings = _extract_docstrings(ast_tree)
    docstring_lines = sum(_count_lines(d) for d in docstrings)
    comment_lines = _count_comment_lines(content)
    code_lines = _count_code_lines(content)
    total_nonblank = sum(1 for ln in content.splitlines() if ln.strip())

    if total_nonblank == 0:
        return DetectorResult(score=0.0, findings=[], detector_name="ratio")

    # Ratio of documentation (docstrings + comments) to total non-blank lines
    doc_and_comment_lines = docstring_lines + comment_lines
    doc_ratio = doc_and_comment_lines / total_nonblank if total_nonblank > 0 else 0.0

    if doc_ratio > 0.6:
        findings.append(
            f"Extremely high documentation ratio: {doc_ratio:.1%} "
            f"({doc_and_comment_lines} doc/comment lines vs {code_lines} code lines)"
        )
    elif doc_ratio > 0.4:
        findings.append(
            f"High documentation ratio: {doc_ratio:.1%} "
            f"({doc_and_comment_lines} doc/comment lines vs {code_lines} code lines)"
        )

    # Check for boilerplate docstrings
    boilerplate_count = sum(1 for d in docstrings if _is_docstring_boilerplate(d))
    if boilerplate_count > 0:
        findings.append(
            f"Boilerplate/filler docstrings detected: {boilerplate_count} out of {len(docstrings)} total docstrings"
        )

    # Docstrings that are longer than the function body they describe
    long_docstring_count = 0
    for node in ast.walk(ast_tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.body:
                continue
            first = node.body[0]
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                doc_len = _count_lines(first.value.value)
                body_len = len(node.body) - 1  # subtract the docstring stmt itself
                if doc_len > body_len * 2 and doc_len > 3:
                    long_docstring_count += 1

    if long_docstring_count > 0:
        findings.append(f"Functions where docstring is longer than body: {long_docstring_count}")

    # Score calculation
    ratio_penalty = max(0.0, (doc_ratio - 0.3) * 1.2)
    boilerplate_penalty = min(0.3, boilerplate_count * 0.08)
    long_doc_penalty = min(0.2, long_docstring_count * 0.07)

    score = min(1.0, ratio_penalty + boilerplate_penalty + long_doc_penalty)

    return DetectorResult(score=score, findings=findings, detector_name="ratio")
