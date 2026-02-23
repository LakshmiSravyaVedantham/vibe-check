# vibe-check — Detect How Much of Your Codebase Was Vibe-Coded

[![CI](https://github.com/sravyalu/vibe-check/actions/workflows/ci.yml/badge.svg)](https://github.com/sravyalu/vibe-check/actions/workflows/ci.yml)
[![Python Versions](https://img.shields.io/pypi/pyversions/vibe-check)](https://pypi.org/project/vibe-check/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**A Python CLI that scans your git repo and scores how much of the code was written by AI assistants (Copilot, ChatGPT, Claude). Every file gets a Vibe Score from 0 to 100.**

---

## Quick Install

```bash
pip install vibe-check
```

## Quick Usage

```bash
# Scan the current directory
vibe-check scan .

# Scan with a threshold (only show files scoring 40+)
vibe-check scan . --threshold 40

# Generate a detailed HTML report
vibe-check report . --output report.html

# JSON output for CI pipelines
vibe-check scan . --format json

# Show detailed findings in terminal
vibe-check scan . --details
```

## Example Output

```
╭──────────────────────────────────────────────╮
│         vibe-check — AI Vibe Code Detector   │
╰──────────────────────────────────────────────╯
Scan path: /my-project
Files analyzed: 12   Skipped: 3   Errors: 0

                         File Vibe Scores
┏━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┓
┃ File                     ┃ Score ┃ Bar                   ┃ Label             ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━┩
│ src/api/handler.py       │  78   │ [###############-----] │ HEAVILY VIBED     │
│ utils/helpers.py         │  65   │ [#############-------] │ HEAVILY VIBED     │
│ models/user.py           │  42   │ [########------------] │ MODERATELY VIBED  │
│ tests/test_api.py        │  31   │ [######--------------] │ SLIGHTLY VIBED    │
│ core/processor.py        │   8   │ [##------------------] │ MOSTLY HUMAN      │
└──────────────────────────┴───────┴───────────────────────┴───────────────────┘

  Repository Summary
  Repo Vibe Score   54/100 — MODERATELY VIBED
  Average Score     45
  Highest Score     78
  High Risk Files   2
  Medium Risk       1
```

## How Scoring Works

Each file is scored 0–100 using a weighted average of 7 detector scores:

| Detector         | Weight | What It Catches |
|------------------|--------|-----------------|
| Security         | 25%    | Hardcoded secrets, `eval()`, `shell=True`, SQL injection |
| Repetitive Code  | 15%    | Copy-paste functions, structurally identical blocks |
| Generic Naming   | 15%    | Variables like `data`, `result`, `temp`; functions like `process_data` |
| Imports          | 15%    | Hallucinated/non-existent modules |
| Over-Commenting  | 10%    | Comments that restate the code |
| Placeholders     | 10%    | `TODO`, `FIXME`, `pass`-only bodies |
| Doc/Code Ratio   | 10%    | Docstrings longer than the functions they describe |

### Score Thresholds

| Score | Label            | Meaning |
|-------|------------------|---------|
| 80-100 | EXTREMELY VIBED | Heavy AI involvement, review carefully |
| 60-79  | HEAVILY VIBED   | Significant AI patterns detected |
| 40-59  | MODERATELY VIBED| Noticeable AI-style code |
| 20-39  | SLIGHTLY VIBED  | Minor AI patterns present |
| 0-19   | MOSTLY HUMAN    | Looks like human-written code |

## Detection Heuristics

### 1. Repetitive Structure
Detects functions with nearly identical AST structure — a classic sign of copy-paste AI generation. Also detects repeated 5-line blocks throughout the file.

### 2. Generic Naming
Flags variables named `data`, `result`, `temp`, `output`, `response`, `item`, `obj`, `val`, `info`, `stuff` and functions named `process_data`, `handle_request`, `do_something`, etc.

### 3. Over-Commenting
Catches comments that literally restate the code (`# increment counter` above `counter += 1`), narrative step-by-step comments, and suspiciously high comment density.

### 4. Hallucinated Imports
Identifies modules that don't exist in the Python stdlib or known third-party packages. Also flags suspiciously named modules like `advanced_utils`, `magic_helper`, `smart_processor`.

### 5. TODO / Placeholder
Counts `TODO`, `FIXME`, `HACK`, `XXX` comments, empty function bodies (`pass` only), and `raise NotImplementedError` stubs.

### 6. Docstring-to-Code Ratio
Flags files where docstrings and comments vastly outnumber actual logic lines. Also detects boilerplate docstrings like "This function handles the processing of data."

### 7. Security Anti-Patterns
Scans for hardcoded secrets (passwords, API keys, tokens), `eval()`, `exec()`, `subprocess.call(shell=True)`, SQL string concatenation, and unsafe deserialization.

## CLI Reference

```
vibe-check scan [PATH]
  --format      terminal|json|html   Output format (default: terminal)
  --threshold   0-100                Only show files at or above this score
  --ignore      PATTERN              Extra patterns to ignore (repeatable)
  --no-gitignore                     Ignore .gitignore files
  --output PATH                      Write output to file
  --details                          Show detailed findings in terminal

vibe-check report [PATH]
  --output PATH                      HTML output file (default: vibe-check-report.html)
  --ignore PATTERN                   Extra patterns to ignore
  --no-gitignore                     Ignore .gitignore files

vibe-check version                   Show version
```

## CI Integration

vibe-check exits with code `2` when high-risk files (score >= 60) are detected, making it easy to use in CI:

```yaml
- name: Check for vibe-coded files
  run: vibe-check scan . --threshold 60 --format json --output vibe-report.json
  continue-on-error: true

- name: Upload vibe report
  uses: actions/upload-artifact@v4
  with:
    name: vibe-check-report
    path: vibe-report.json
```

## Architecture

```
src/vibe_check/
├── cli.py          Click CLI with scan/report/version commands
├── analyzer.py     Walks the file tree; dispatches to detectors
├── scoring.py      Weighted aggregation into 0-100 score
├── reporter.py     Terminal (rich), JSON, and HTML output
└── detectors/
    ├── repetitive.py   AST structural fingerprinting
    ├── naming.py       Generic identifier detection
    ├── comments.py     Over-commenting patterns
    ├── imports.py      Hallucinated module detection
    ├── placeholders.py TODO/empty body detection
    ├── ratio.py        Docstring-to-code ratio
    └── security.py     Security anti-pattern detection
```

## Contributing

Contributions are welcome! To add a new detector:

1. Create `src/vibe_check/detectors/my_detector.py`
2. Implement `detect(filepath, content, ast_tree=None) -> DetectorResult`
3. Add it to `src/vibe_check/detectors/__init__.py`
4. Register it in `analyzer.py` and add a weight in `scoring.py`
5. Add tests in `tests/test_detectors.py`

```bash
# Development setup
git clone https://github.com/sravyalu/vibe-check
cd vibe-check
python -m venv venv && source venv/bin/activate
pip install -e ".[dev]"
pytest
```

## License

MIT — see [LICENSE](LICENSE)
