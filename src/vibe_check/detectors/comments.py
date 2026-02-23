"""Detector for over-commenting patterns typical of AI-generated code."""

import ast
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

# Phrases that indicate comments restating obvious code
OBVIOUS_COMMENT_PATTERNS = [
    (r"#\s*increment\s+\w+", "increment counter comment"),
    (r"#\s*decrement\s+\w+", "decrement counter comment"),
    (r"#\s*return\s+the\s+result", "return the result comment"),
    (r"#\s*return\s+\w+", "trivial return comment"),
    (r"#\s*print\s+\w+", "trivial print comment"),
    (r"#\s*set\s+\w+\s+to\s+", "trivial assignment comment"),
    (r"#\s*create\s+(a|an)\s+\w+\s+(list|dict|set|object)", "trivial creation comment"),
    (r"#\s*initialize\s+\w+", "trivial initialization comment"),
    (r"#\s*define\s+(a|the)\s+function", "trivial function definition comment"),
    (r"#\s*define\s+(a|the)\s+class", "trivial class definition comment"),
    (r"#\s*import\s+\w+", "trivial import comment"),
    (r"#\s*call\s+the\s+function", "trivial function call comment"),
    (r"#\s*loop\s+(through|over|across)\s+", "trivial loop comment"),
    (r"#\s*iterate\s+(through|over)\s+", "trivial iteration comment"),
    (r"#\s*check\s+if\s+\w+\s+is\s+(true|false|none|not none|empty)", "trivial condition comment"),
    (r"#\s*add\s+\w+\s+to\s+(the\s+)?(list|dict|set)", "trivial collection add comment"),
    (r"#\s*append\s+\w+\s+to\s+", "trivial append comment"),
    (r"#\s*open\s+the\s+file", "trivial file open comment"),
    (r"#\s*close\s+the\s+file", "trivial file close comment"),
    (r"#\s*read\s+the\s+file", "trivial file read comment"),
    (r"#\s*write\s+to\s+the\s+file", "trivial file write comment"),
    (r"#\s*convert\s+\w+\s+to\s+\w+", "trivial conversion comment"),
    (r"#\s*calculate\s+the\s+\w+", "trivial calculation comment"),
    (r"#\s*get\s+the\s+\w+", "trivial getter comment"),
    (r"#\s*set\s+the\s+\w+", "trivial setter comment"),
]

# Patterns for "step" comments that narrate code like a tutorial
NARRATIVE_COMMENT_PATTERNS = [
    r"#\s*step\s+\d+",
    r"#\s*first[,\s]",
    r"#\s*second[,\s]",
    r"#\s*third[,\s]",
    r"#\s*finally[,\s]",
    r"#\s*next[,\s]",
    r"#\s*now\s+(we|let's|we'll)\s+",
    r"#\s*then\s+(we|let's)\s+",
]


@dataclass
class DetectorResult:
    """Result from a single detector run."""

    score: float
    findings: List[str] = field(default_factory=list)
    detector_name: str = "unknown"


def _get_comment_lines(content: str) -> List[Tuple[int, str]]:
    """Return list of (line_number, comment_text) for inline comments."""
    results = []
    for i, line in enumerate(content.splitlines(), start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            results.append((i, stripped))
        elif "#" in line:
            # Inline comment after code
            code_part, _, comment_part = line.partition("#")
            if code_part.strip():
                results.append((i, "# " + comment_part.strip()))
    return results


def _check_comment_restates_code(comment: str, next_line: str) -> bool:
    """Heuristic: does the comment basically say what the next line does?"""
    comment_lower = comment.lower().lstrip("# ").strip()
    next_stripped = next_line.strip().lower()

    # Very short comments that match code patterns
    if next_stripped.startswith("return") and "return" in comment_lower:
        return True
    if next_stripped.startswith("print") and "print" in comment_lower:
        return True
    if "+= 1" in next_stripped and ("increment" in comment_lower or "counter" in comment_lower):
        return True
    if "-= 1" in next_stripped and ("decrement" in comment_lower or "counter" in comment_lower):
        return True
    if next_stripped.startswith("for ") and ("loop" in comment_lower or "iterate" in comment_lower):
        return True
    if next_stripped.startswith("if ") and "check" in comment_lower and len(comment_lower) < 30:
        return True
    return False


def detect(filepath: str, content: str, ast_tree: Optional[ast.AST] = None) -> DetectorResult:
    """Detect over-commenting patterns in code."""
    findings: List[str] = []
    lines = content.splitlines()

    comment_lines = _get_comment_lines(content)
    total_lines = len([line for line in lines if line.strip()])
    comment_count = len(comment_lines)

    # Check for obvious/restating comments
    obvious_matches: List[str] = []
    for lineno, comment in comment_lines:
        for pattern, label in OBVIOUS_COMMENT_PATTERNS:
            if re.search(pattern, comment, re.IGNORECASE):
                obvious_matches.append(f"Line {lineno}: {label} ({comment[:60]})")
                break

    if obvious_matches:
        findings.append(f"Code-restating comments found ({len(obvious_matches)} instances):")
        for match in obvious_matches[:5]:
            findings.append(f"  {match}")
        if len(obvious_matches) > 5:
            findings.append(f"  ... and {len(obvious_matches) - 5} more")

    # Check for narrative "step-by-step" style comments
    narrative_count = 0
    for lineno, comment in comment_lines:
        for pattern in NARRATIVE_COMMENT_PATTERNS:
            if re.search(pattern, comment, re.IGNORECASE):
                narrative_count += 1
                break
    if narrative_count >= 3:
        findings.append(
            f"Narrative/tutorial-style comments: {narrative_count} instances " "(step-by-step narration detected)"
        )

    # Check for comment density: is every other line a comment?
    if total_lines > 10:
        comment_ratio = comment_count / total_lines
        if comment_ratio > 0.4:
            findings.append(
                f"Very high comment density: {comment_ratio:.1%} of non-empty lines are comments "
                f"({comment_count} comments / {total_lines} lines)"
            )

    # Check for consecutive comment blocks that are suspiciously long
    consecutive = 0
    max_consecutive = 0
    for line in lines:
        if line.strip().startswith("#"):
            consecutive += 1
            max_consecutive = max(max_consecutive, consecutive)
        else:
            consecutive = 0

    if max_consecutive > 8:
        findings.append(f"Large comment block found: {max_consecutive} consecutive comment lines")

    # Score calculation
    obvious_penalty = min(0.5, len(obvious_matches) * 0.05)
    narrative_penalty = min(0.2, narrative_count * 0.04)
    density_penalty = 0.0
    if total_lines > 10:
        ratio = comment_count / total_lines
        if ratio > 0.4:
            density_penalty = min(0.3, (ratio - 0.4) * 1.5)
    consecutive_penalty = min(0.1, max_consecutive * 0.005)

    score = min(1.0, obvious_penalty + narrative_penalty + density_penalty + consecutive_penalty)

    return DetectorResult(score=score, findings=findings, detector_name="comments")
