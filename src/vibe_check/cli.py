"""Click CLI entry point for vibe-check."""

import sys
from pathlib import Path

import click
from rich.console import Console

from vibe_check import __version__
from vibe_check.analyzer import analyze_path
from vibe_check.reporter import generate_json_report, print_terminal_report, write_html_report
from vibe_check.scoring import aggregate_repo_score

console = Console()
err_console = Console(stderr=True)


@click.group()
@click.version_option(version=__version__, prog_name="vibe-check")
def main() -> None:
    """vibe-check: Detect how much of your codebase was vibe-coded by AI."""


@main.command("scan")
@click.argument("path", default=".", type=click.Path(exists=True), metavar="[PATH]")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["terminal", "json", "html"], case_sensitive=False),
    default="terminal",
    show_default=True,
    help="Output format.",
)
@click.option(
    "--threshold",
    type=click.IntRange(0, 100),
    default=0,
    show_default=True,
    help="Only show files with vibe score at or above this value.",
)
@click.option(
    "--ignore",
    "ignore_patterns",
    multiple=True,
    metavar="PATTERN",
    help="Additional glob patterns to ignore (can be specified multiple times).",
)
@click.option(
    "--no-gitignore",
    is_flag=True,
    default=False,
    help="Do not respect .gitignore files.",
)
@click.option(
    "--output",
    "-o",
    default=None,
    type=click.Path(),
    help="Write output to a file (required for --format html).",
)
@click.option(
    "--details",
    is_flag=True,
    default=False,
    help="Show detailed findings for high-risk files in terminal output.",
)
def scan(
    path: str,
    output_format: str,
    threshold: int,
    ignore_patterns: tuple,
    no_gitignore: bool,
    output: str,
    details: bool,
) -> None:
    """Scan a directory or file for vibe-coded patterns.

    PATH defaults to the current directory.
    """
    use_gitignore = not no_gitignore

    try:
        results = analyze_path(
            scan_path=path,
            threshold=threshold,
            ignore_patterns=list(ignore_patterns),
            use_gitignore=use_gitignore,
        )
    except ValueError as e:
        err_console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)
    except Exception as e:
        err_console.print(f"[red]Unexpected error:[/red] {e}")
        sys.exit(1)

    if output_format == "terminal":
        print_terminal_report(results, scan_path=path, threshold=threshold, show_findings=details)
        # Exit with non-zero code if any high-risk files found (useful for CI)
        high_risk_count = sum(1 for r in results if not r.skipped and not r.error and r.vibe_score >= 60)
        if high_risk_count > 0:
            sys.exit(2)

    elif output_format == "json":
        json_output = generate_json_report(results, scan_path=path)
        if output:
            Path(output).write_text(json_output, encoding="utf-8")
            console.print(f"[green]JSON report written to:[/green] {output}")
        else:
            click.echo(json_output)

    elif output_format == "html":
        if not output:
            output = "vibe-check-report.html"
        write_html_report(results, scan_path=path, output_path=output)
        console.print(f"[green]HTML report written to:[/green] {output}")

        # Also show brief summary in terminal
        analyzed = [r for r in results if not r.skipped and not r.error]
        scores = [r.vibe_score for r in analyzed]
        if scores:
            repo_score = aggregate_repo_score(scores)
            console.print(f"[cyan]Repo Vibe Score:[/cyan] {repo_score}/100")
            console.print(f"[cyan]Files analyzed:[/cyan] {len(analyzed)}")


@main.command("report")
@click.argument("path", default=".", type=click.Path(exists=True), metavar="[PATH]")
@click.option(
    "--output",
    "-o",
    default="vibe-check-report.html",
    show_default=True,
    type=click.Path(),
    help="Output file path for the HTML report.",
)
@click.option(
    "--ignore",
    "ignore_patterns",
    multiple=True,
    metavar="PATTERN",
    help="Additional glob patterns to ignore.",
)
@click.option(
    "--no-gitignore",
    is_flag=True,
    default=False,
    help="Do not respect .gitignore files.",
)
def report(path: str, output: str, ignore_patterns: tuple, no_gitignore: bool) -> None:
    """Generate a detailed HTML report for a directory or file.

    PATH defaults to the current directory.
    """
    use_gitignore = not no_gitignore

    console.print(f"[cyan]Scanning:[/cyan] {path}")

    try:
        results = analyze_path(
            scan_path=path,
            threshold=0,
            ignore_patterns=list(ignore_patterns),
            use_gitignore=use_gitignore,
        )
    except ValueError as e:
        err_console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    write_html_report(results, scan_path=path, output_path=output)

    analyzed = [r for r in results if not r.skipped and not r.error]
    scores = [r.vibe_score for r in analyzed]

    console.print(f"[green]HTML report written to:[/green] {output}")
    if scores:
        repo_score = aggregate_repo_score(scores)
        console.print(f"[cyan]Repo Vibe Score:[/cyan] {repo_score}/100  ({len(analyzed)} files analyzed)")


@main.command("version")
def version() -> None:
    """Show the vibe-check version."""
    console.print(f"vibe-check {__version__}")
