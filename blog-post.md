---
title: "I Built a CLI That Scores How Much of Your Code Was Written by AI"
published: false
description: "vibe-check scans your Python codebase and gives every file an AI Vibe Score from 0-100. Here's how I built it using AST analysis and 7 detection heuristics."
tags: vibecoding, python, ai, opensource
cover_image: ""
canonical_url:
series: "Building Developer Tools in 2026"
---

## The Problem: Nobody Knows How Much of Their Codebase Is AI-Generated

We're in February 2026 and vibe coding is everywhere. GitHub Copilot, ChatGPT, Claude — developers are shipping AI-generated code faster than ever. But there's a growing crisis nobody talks about:

- **AI-generated code has 2.74x more security vulnerabilities** than human-written code (Stanford, 2025)
- **Experienced developers are 19% slower** when using AI tools for complex tasks
- **Code reviews miss AI-specific patterns** like hallucinated imports and over-commented boilerplate

I wanted a tool that could answer one simple question: **"How much of this codebase was vibe-coded?"**

So I built `vibe-check`.

## 3 Lines to Get Started

```bash
pip install vibe-check
vibe-check scan .
vibe-check report . --output report.html
```

That's it. Every Python file gets a score from 0 to 100.

## What It Detects

`vibe-check` uses **7 weighted detectors** powered by Python's `ast` module:

| Detector | Weight | What It Catches |
|----------|--------|-----------------|
| **Security** | 25% | `eval()`, hardcoded secrets, SQL injection, `shell=True` |
| **Repetitive Code** | 15% | Copy-paste functions with identical AST fingerprints |
| **Generic Naming** | 15% | Variables named `data`, `result`, `temp`, `output` |
| **Hallucinated Imports** | 15% | Modules that don't exist in stdlib or known packages |
| **Over-Commenting** | 10% | Comments that restate the code (`# increment counter`) |
| **Placeholders** | 10% | `TODO`, `pass`-only bodies, `NotImplementedError` stubs |
| **Doc/Code Ratio** | 10% | Docstrings longer than the functions they describe |

Each detector returns a 0-100 score, and the weighted average becomes the file's **Vibe Score**.

## Example Output

```
╭──────────────────────────────────────────────╮
│         vibe-check — AI Vibe Code Detector   │
╰──────────────────────────────────────────────╯

                     File Vibe Scores
┏━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━━━━━┓
┃ File                     ┃ Score ┃ Label             ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━━━━━━┩
│ src/api/handler.py       │  78   │ HEAVILY VIBED     │
│ utils/helpers.py         │  65   │ HEAVILY VIBED     │
│ models/user.py           │  42   │ MODERATELY VIBED  │
│ core/processor.py        │   8   │ MOSTLY HUMAN      │
└──────────────────────────┴───────┴───────────────────┘

  Repo Vibe Score   54/100 — MODERATELY VIBED
```

## Architecture

```
src/vibe_check/
├── cli.py           # Click CLI: scan, report, version
├── analyzer.py      # Walks file tree, dispatches to detectors
├── scoring.py       # Weighted aggregation into 0-100
├── reporter.py      # Terminal (Rich), JSON, HTML output
└── detectors/
    ├── repetitive.py    # AST structural fingerprinting
    ├── naming.py        # Generic identifier detection
    ├── comments.py      # Over-commenting patterns
    ├── imports.py       # Hallucinated module detection
    ├── placeholders.py  # TODO/empty body detection
    ├── ratio.py         # Docstring-to-code ratio
    └── security.py      # Security anti-pattern detection
```

The key design decision was making each detector a standalone module with the same interface:

```python
def detect(filepath: str, content: str, ast_tree=None) -> DetectorResult
```

This makes it trivial to add new detectors without touching the rest of the codebase.

## The Hardest Part: AST Fingerprinting

The repetitive code detector was the most interesting challenge. AI tools love generating structurally identical functions — same pattern, different variable names. I needed to detect this without false-positiving on legitimate similar code.

The solution: **normalize the AST by replacing all identifiers with placeholders**, then hash the resulting structure. If two functions produce the same hash, they're structurally identical regardless of naming.

```python
# These two would produce the same AST fingerprint:
def process_users(users):
    results = []
    for user in users:
        results.append(user.name)
    return results

def handle_orders(orders):
    output = []
    for order in orders:
        output.append(order.id)
    return output
```

## CI Integration

`vibe-check` exits with code 2 when high-risk files are detected, so you can gate your CI pipeline:

```yaml
- name: Vibe Check
  run: vibe-check scan . --threshold 60 --format json
```

## Numbers

- **79 tests** passing
- **87% coverage**
- **Python 3.9-3.12** matrix CI
- **0 dependencies** beyond Click and Rich

## What I Learned

1. **AST analysis is incredibly powerful** for code quality tools — way more reliable than regex
2. **Weighted scoring systems** need careful calibration; security deserves the most weight
3. **The vibe coding problem is real** — I ran this on several popular repos and found scores of 60+ in utility files

## Try It

```bash
pip install vibe-check
vibe-check scan your-project/
```

Star it on GitHub: [github.com/LakshmiSravyaVedantham/vibe-check](https://github.com/LakshmiSravyaVedantham/vibe-check)

---

*What's your repo's Vibe Score? Run it and let me know in the comments.*
