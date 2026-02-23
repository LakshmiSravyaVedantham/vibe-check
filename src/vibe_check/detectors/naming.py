"""Detector for generic AI-style naming patterns."""

import ast
import re
from dataclasses import dataclass, field
from typing import List, Optional, Set

GENERIC_VARIABLE_NAMES: Set[str] = {
    "data",
    "result",
    "results",
    "temp",
    "tmp",
    "output",
    "outputs",
    "response",
    "item",
    "items",
    "obj",
    "object",
    "val",
    "value",
    "values",
    "info",
    "stuff",
    "thing",
    "things",
    "x",
    "y",
    "z",
    "foo",
    "bar",
    "baz",
    "test",
    "flag",
    "ret",
    "res",
    "buf",
    "buffer",
    "payload",
    "content",
    "body",
    "node",
    "element",
    "entry",
    "record",
    "row",
    "col",
    "chunk",
    "part",
    "piece",
    "msg",
    "message",
}

GENERIC_FUNCTION_NAMES: Set[str] = {
    "process_data",
    "handle_request",
    "do_something",
    "process",
    "handle",
    "run",
    "execute",
    "perform",
    "do_stuff",
    "do_thing",
    "do_work",
    "process_input",
    "process_output",
    "handle_data",
    "handle_response",
    "process_request",
    "process_response",
    "get_data",
    "set_data",
    "update_data",
    "fetch_data",
    "load_data",
    "save_data",
    "parse_data",
    "validate_data",
    "transform_data",
    "format_data",
    "calculate_result",
    "compute_result",
    "get_result",
    "send_request",
    "make_request",
    "helper",
    "helper_function",
    "utility",
    "util_func",
    "main_function",
    "start",
    "init",
    "setup",
    "teardown",
    "cleanup",
}


@dataclass
class DetectorResult:
    """Result from a single detector run."""

    score: float
    findings: List[str] = field(default_factory=list)
    detector_name: str = "unknown"


def _extract_names_from_ast(tree: ast.AST):
    """Extract variable names, function names, and class names from the AST."""
    var_names: List[str] = []
    func_names: List[str] = []
    class_names: List[str] = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func_names.append(node.name)
            # Function arguments
            for arg in node.args.args:
                var_names.append(arg.arg)
        elif isinstance(node, ast.ClassDef):
            class_names.append(node.name)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            var_names.append(node.id)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    var_names.append(target.id)

    return var_names, func_names, class_names


def _check_text_names(content: str) -> List[str]:
    """Fallback text-based name checking for non-Python files."""
    findings = []
    # Look for common generic variable assignments in any language
    generic_patterns = [
        (r"\b(data|result|temp|output|response|item|obj|val|info|stuff)\s*=", "generic variable assignment"),
        (r"function\s+(processData|handleRequest|doSomething|getData|setData)\s*\(", "generic function name"),
        (r"def\s+(process_data|handle_request|do_something|get_data|set_data)\s*\(", "generic Python function name"),
    ]
    for pattern, label in generic_patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        if matches:
            findings.append(f"Found {label}: {', '.join(set(matches[:5]))}")
    return findings


def detect(filepath: str, content: str, ast_tree: Optional[ast.AST] = None) -> DetectorResult:
    """Detect generic AI-style naming in the code."""
    findings: List[str] = []

    if ast_tree is None:
        if filepath.endswith(".py"):
            try:
                ast_tree = ast.parse(content)
            except SyntaxError:
                text_findings = _check_text_names(content)
                score = min(1.0, len(text_findings) * 0.1)
                return DetectorResult(score=score, findings=text_findings, detector_name="naming")
        else:
            text_findings = _check_text_names(content)
            score = min(1.0, len(text_findings) * 0.1)
            return DetectorResult(score=score, findings=text_findings, detector_name="naming")

    var_names, func_names, class_names = _extract_names_from_ast(ast_tree)

    # Check variable names
    generic_vars = [name for name in var_names if name.lower() in GENERIC_VARIABLE_NAMES]
    unique_generic_vars = list(dict.fromkeys(generic_vars))  # preserve order, deduplicate
    if unique_generic_vars:
        findings.append(f"Generic variable names: {', '.join(unique_generic_vars[:10])}")

    # Check function names
    generic_funcs = [name for name in func_names if name.lower() in GENERIC_FUNCTION_NAMES]
    if generic_funcs:
        findings.append(f"Generic function names: {', '.join(generic_funcs)}")

    # Check for single-letter variables beyond i/j/k loop vars
    single_letter_vars = [name for name in set(var_names) if len(name) == 1 and name not in ("i", "j", "k", "n", "e")]
    if len(single_letter_vars) > 3:
        findings.append(f"Many single-letter variable names: {', '.join(sorted(single_letter_vars))}")

    # Score calculation
    total_names = len(set(var_names)) + len(set(func_names))
    if total_names == 0:
        return DetectorResult(score=0.0, findings=[], detector_name="naming")

    generic_count = len(unique_generic_vars) + len(generic_funcs)
    generic_ratio = generic_count / total_names
    single_letter_penalty = min(0.2, len(single_letter_vars) * 0.03)
    score = min(1.0, generic_ratio * 0.8 + single_letter_penalty)

    return DetectorResult(score=score, findings=findings, detector_name="naming")
