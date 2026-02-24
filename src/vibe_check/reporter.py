"""Generate reports in terminal, JSON, and HTML formats."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from vibe_check.analyzer import FileResult
from vibe_check.scoring import aggregate_repo_score, get_score_label

console = Console()


def _score_color(score: int) -> str:
    """Return a Rich color string for a given score."""
    if score >= 80:
        return "bold red"
    if score >= 60:
        return "red"
    if score >= 40:
        return "yellow"
    if score >= 20:
        return "dark_orange"
    return "green"


def _score_bar(score: int, width: int = 20) -> str:
    """Return an ASCII progress bar for a score."""
    filled = int(score / 100 * width)
    empty = width - filled
    bar = "[" + "#" * filled + "-" * empty + "]"
    return bar


def print_terminal_report(
    results: List[FileResult],
    scan_path: str,
    threshold: int = 0,
    show_findings: bool = False,
) -> None:
    """Print a rich terminal report of analysis results."""
    analyzed = [r for r in results if not r.skipped and not r.error]
    skipped = [r for r in results if r.skipped]
    errors = [r for r in results if r.error]

    # Header
    console.print()
    console.print(Panel.fit("[bold cyan]vibe-check[/bold cyan] — AI Vibe Code Detector", border_style="cyan"))
    console.print(f"[dim]Scan path:[/dim] {scan_path}")
    console.print(
        f"[dim]Files analyzed:[/dim] {len(analyzed)}   "
        f"[dim]Skipped:[/dim] {len(skipped)}   "
        f"[dim]Errors:[/dim] {len(errors)}"
    )
    console.print()

    if not analyzed:
        console.print("[yellow]No files were analyzed.[/yellow]")
        return

    # Main results table
    table = Table(
        title="File Vibe Scores",
        show_header=True,
        header_style="bold magenta",
        border_style="dim",
        expand=True,
    )
    table.add_column("File", style="cyan", no_wrap=False, ratio=50)
    table.add_column("Score", justify="center", width=8)
    table.add_column("Bar", justify="left", width=24)
    table.add_column("Label", justify="left", width=18)
    table.add_column("Top Finding", no_wrap=False, ratio=30)

    for result in analyzed:
        score = result.vibe_score
        color = _score_color(score)
        label, _ = get_score_label(score)
        bar = _score_bar(score)

        top_finding = ""
        if result.all_findings:
            top_finding = result.all_findings[0][:60]

        table.add_row(
            result.relative_path,
            Text(str(score), style=color),
            Text(bar, style=color),
            Text(label, style=color),
            top_finding,
        )

    console.print(table)
    console.print()

    # Aggregate stats
    scores = [r.vibe_score for r in analyzed]
    if scores:
        repo_score = aggregate_repo_score(scores)
        avg_score = sum(scores) // len(scores)
        max_score = max(scores)
        min_score = min(scores)

        repo_label, repo_color = get_score_label(repo_score)

        stats_table = Table(show_header=False, box=None, padding=(0, 2))
        stats_table.add_column("Metric", style="dim")
        stats_table.add_column("Value")

        stats_table.add_row("Repo Vibe Score", Text(f"{repo_score}/100 — {repo_label}", style=_score_color(repo_score)))
        stats_table.add_row("Average Score", Text(str(avg_score), style=_score_color(avg_score)))
        stats_table.add_row("Highest Score", Text(str(max_score), style=_score_color(max_score)))
        stats_table.add_row("Lowest Score", Text(str(min_score), style="green"))

        high_risk = sum(1 for s in scores if s >= 60)
        medium_risk = sum(1 for s in scores if 40 <= s < 60)
        stats_table.add_row(
            "High Risk Files (>=60)",
            Text(str(high_risk), style="red" if high_risk > 0 else "green"),
        )
        stats_table.add_row(
            "Medium Risk Files (40-59)",
            Text(str(medium_risk), style="yellow" if medium_risk > 0 else "green"),
        )

        console.print(Panel(stats_table, title="[bold]Repository Summary[/bold]", border_style="magenta"))
        console.print()

    # Detailed findings section
    if show_findings:
        high_risk_files = [r for r in analyzed if r.vibe_score >= 40 and r.all_findings]
        if high_risk_files:
            console.print("[bold]Detailed Findings for High-Risk Files:[/bold]")
            for result in high_risk_files[:10]:
                console.print(f"\n[cyan]{result.relative_path}[/cyan] (score: {result.vibe_score})")
                for finding in result.all_findings[:8]:
                    console.print(f"  [dim]•[/dim] {finding}")
            console.print()

    # Error summary
    if errors:
        console.print(f"[red]Errors analyzing {len(errors)} file(s):[/red]")
        for r in errors[:5]:
            console.print(f"  [dim]{r.relative_path}[/dim]: {r.error}")


def generate_json_report(
    results: List[FileResult],
    scan_path: str,
) -> str:
    """Generate a JSON report of analysis results."""
    analyzed = [r for r in results if not r.skipped and not r.error]
    scores = [r.vibe_score for r in analyzed]

    files_data = []
    for result in results:
        file_data: dict = {
            "path": result.relative_path,
            "vibe_score": result.vibe_score,
            "skipped": result.skipped,
            "skip_reason": result.skip_reason,
            "error": result.error,
        }
        if result.score_breakdown:
            file_data["score_label"] = result.score_breakdown.label
            file_data["detector_scores"] = {
                name: round(score, 3) for name, score in result.score_breakdown.raw_scores.items()
            }
        if result.all_findings:
            file_data["findings"] = result.all_findings

        files_data.append(file_data)

    report = {
        "scan_path": scan_path,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "summary": {
            "total_files": len(results),
            "analyzed_files": len(analyzed),
            "skipped_files": len([r for r in results if r.skipped]),
            "error_files": len([r for r in results if r.error]),
            "repo_vibe_score": aggregate_repo_score(scores) if scores else 0,
            "average_score": sum(scores) // len(scores) if scores else 0,
            "high_risk_files": sum(1 for s in scores if s >= 60),
            "medium_risk_files": sum(1 for s in scores if 40 <= s < 60),
        },
        "files": files_data,
    }

    return json.dumps(report, indent=2)


def generate_html_report(
    results: List[FileResult],
    scan_path: str,
) -> str:
    """Generate a self-contained single-file HTML report."""
    analyzed = [r for r in results if not r.skipped and not r.error]
    scores = [r.vibe_score for r in analyzed]
    repo_score = aggregate_repo_score(scores) if scores else 0
    avg_score = sum(scores) // len(scores) if scores else 0
    high_risk = sum(1 for s in scores if s >= 60)
    medium_risk = sum(1 for s in scores if 40 <= s < 60)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    repo_label, _ = get_score_label(repo_score)

    def score_color_hex(score: int) -> str:
        if score >= 80:
            return "#ef4444"
        if score >= 60:
            return "#f97316"
        if score >= 40:
            return "#eab308"
        if score >= 20:
            return "#84cc16"
        return "#22c55e"

    def score_badge(score: int) -> str:
        color = score_color_hex(score)
        label, _ = get_score_label(score)
        return f'<span class="badge" style="background:{color}">{score} — {label}</span>'

    rows = []
    for result in analyzed:
        score = result.vibe_score
        color = score_color_hex(score)
        label, _ = get_score_label(score)
        pct = score

        findings_html = ""
        if result.all_findings:
            items = "".join(f"<li>{f}</li>" for f in result.all_findings[:6])
            if len(result.all_findings) > 6:
                items += f"<li><em>...and {len(result.all_findings) - 6} more findings</em></li>"
            findings_html = f"<ul>{items}</ul>"

        detector_bars = ""
        if result.score_breakdown:
            for det_name, raw_score in sorted(result.score_breakdown.raw_scores.items()):
                det_pct = int(raw_score * 100)
                det_color = score_color_hex(det_pct)
                detector_bars += (
                    f'<div class="det-row">'
                    f'<span class="det-label">{det_name}</span>'
                    f'<div class="det-bar-bg">'
                    f'<div class="det-bar" style="width:{det_pct}%;background:{det_color}"></div>'
                    f"</div>"
                    f'<span class="det-val">{det_pct}</span>'
                    f"</div>"
                )

        rows.append(
            f"""
            <tr>
                <td class="file-path">{result.relative_path}</td>
                <td>
                    <div class="score-cell">
                        <div class="score-bar-bg">
                            <div class="score-bar" style="width:{pct}%;background:{color}"></div>
                        </div>
                        <span class="score-num" style="color:{color}">{score}</span>
                    </div>
                    <span class="label-badge" style="color:{color}">{label}</span>
                </td>
                <td>
                    <details>
                        <summary>{len(result.all_findings)} finding(s)</summary>
                        {findings_html}
                        <div class="detector-breakdown">{detector_bars}</div>
                    </details>
                </td>
            </tr>"""
        )

    rows_html = "\n".join(rows)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>vibe-check Report — {scan_path}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: #0f172a; color: #e2e8f0; padding: 2rem; }}
  h1 {{ font-size: 2rem; color: #7dd3fc; margin-bottom: 0.5rem; }}
  h2 {{ font-size: 1.2rem; color: #94a3b8; margin-bottom: 1.5rem; font-weight: normal; }}
  .meta {{ color: #64748b; font-size: 0.85rem; margin-bottom: 2rem; }}
  .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 1rem; margin-bottom: 2rem; }}
  .stat-card {{ background: #1e293b; border-radius: 10px; padding: 1.2rem;
    text-align: center; border: 1px solid #334155; }}
  .stat-val {{ font-size: 2rem; font-weight: bold; display: block; }}
  .stat-label {{ font-size: 0.8rem; color: #94a3b8; margin-top: 0.3rem; }}
  .badge {{ padding: 0.3rem 0.8rem; border-radius: 20px; font-size: 0.8rem; color: white; font-weight: bold; }}
  table {{ width: 100%; border-collapse: collapse; background: #1e293b; border-radius: 12px; overflow: hidden; }}
  thead tr {{ background: #0f172a; }}
  th {{ padding: 1rem; text-align: left; color: #7dd3fc; font-size: 0.9rem; border-bottom: 1px solid #334155; }}
  td {{ padding: 0.9rem 1rem; border-bottom: 1px solid #1e293b; vertical-align: top; }}
  tr:last-child td {{ border-bottom: none; }}
  tr:hover td {{ background: #0f172a; }}
  .file-path {{ font-family: monospace; font-size: 0.88rem; color: #93c5fd; word-break: break-all; }}
  .score-cell {{ display: flex; align-items: center; gap: 0.6rem; margin-bottom: 0.3rem; }}
  .score-bar-bg {{ flex: 1; height: 8px; background: #334155; border-radius: 4px; overflow: hidden; }}
  .score-bar {{ height: 100%; border-radius: 4px; transition: width 0.3s; }}
  .score-num {{ font-weight: bold; font-size: 1.1rem; min-width: 2.5rem; }}
  .label-badge {{ font-size: 0.75rem; font-weight: 600; }}
  details summary {{ cursor: pointer; color: #94a3b8; font-size: 0.85rem; user-select: none; }}
  details[open] summary {{ margin-bottom: 0.5rem; }}
  details ul {{ list-style: none; padding: 0; margin: 0; font-size: 0.8rem; color: #cbd5e1; }}
  details li {{ padding: 0.15rem 0; border-left: 2px solid #334155; padding-left: 0.5rem; margin-bottom: 0.2rem; }}
  .detector-breakdown {{ margin-top: 0.8rem; }}
  .det-row {{ display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.25rem; font-size: 0.75rem; }}
  .det-label {{ min-width: 90px; color: #94a3b8; }}
  .det-bar-bg {{ flex: 1; height: 6px; background: #334155; border-radius: 3px; overflow: hidden; }}
  .det-bar {{ height: 100%; border-radius: 3px; }}
  .det-val {{ min-width: 2rem; text-align: right; color: #94a3b8; }}
  footer {{ margin-top: 2rem; text-align: center; color: #475569; font-size: 0.8rem; }}
</style>
</head>
<body>
<h1>vibe-check Report</h1>
<h2>Detect how much of your codebase was vibe-coded by AI</h2>
<p class="meta">Scan path: <code>{scan_path}</code> &nbsp;|&nbsp; Generated: {timestamp}</p>

<div class="summary">
  <div class="stat-card">
    <span class="stat-val" style="color:{score_color_hex(repo_score)}">{repo_score}</span>
    <span class="stat-label">Repo Vibe Score<br><strong>{repo_label}</strong></span>
  </div>
  <div class="stat-card">
    <span class="stat-val">{len(analyzed)}</span>
    <span class="stat-label">Files Analyzed</span>
  </div>
  <div class="stat-card">
    <span class="stat-val" style="color:#eab308">{avg_score}</span>
    <span class="stat-label">Average Score</span>
  </div>
  <div class="stat-card">
    <span class="stat-val" style="color:#ef4444">{high_risk}</span>
    <span class="stat-label">High Risk Files (&ge;60)</span>
  </div>
  <div class="stat-card">
    <span class="stat-val" style="color:#f97316">{medium_risk}</span>
    <span class="stat-label">Medium Risk Files (40-59)</span>
  </div>
</div>

<table>
  <thead>
    <tr>
      <th>File</th>
      <th>Vibe Score</th>
      <th>Findings</th>
    </tr>
  </thead>
  <tbody>
    {rows_html}
  </tbody>
</table>

<footer>
  Generated by <strong>vibe-check</strong> v0.1.0 &nbsp;|&nbsp;
  <a href="https://github.com/sravyalu/vibe-check" style="color:#7dd3fc">GitHub</a>
</footer>
</body>
</html>"""

    return html


def write_html_report(
    results: List[FileResult],
    scan_path: str,
    output_path: str,
) -> None:
    """Write an HTML report to a file."""
    html = generate_html_report(results, scan_path)
    Path(output_path).write_text(html, encoding="utf-8")
