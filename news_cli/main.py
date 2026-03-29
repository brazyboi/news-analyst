from __future__ import annotations

from datetime import datetime
from time import perf_counter

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .orchestrator import orchestrate_news_analysis

app = typer.Typer(help="Multi-Agent Tech News Analyst CLI")
console = Console()

AGENT_COLORS = {
    "news_agent": "cyan",
    "analyst_agent": "magenta",
}


@app.callback()
def cli() -> None:
    """CLI entry point."""
    return None


def _truncate(text: str, max_len: int = 48) -> str:
    if len(text) <= max_len:
        return text
    return f"{text[: max_len - 3]}..."


def _parse_companies(companies: str) -> list[str]:
    values = [value.strip() for value in companies.split(",")]
    parsed = [value for value in values if value]
    if not parsed:
        raise typer.BadParameter("Provide at least one company name.")
    return parsed


def _render_header(topic: str, companies: list[str]) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    body = (
        f"[bold]Topic:[/bold] {topic}\n"
        f"[bold]Companies:[/bold] {', '.join(companies)}\n"
        f"[bold]Started:[/bold] {timestamp}"
    )
    console.print(Panel(body, title="Multi-Agent Tech News Analyst", expand=False))


def _extract_bullets(section_text: str, limit: int = 3) -> list[str]:
    bullets: list[str] = []
    for line in section_text.splitlines():
        value = line.strip()
        if not value:
            continue
        if value[0].isdigit() and "." in value:
            bullets.append(value.split(".", 1)[1].strip())
        elif value.startswith("- "):
            bullets.append(value[2:].strip())
    return bullets[:limit]


def _parse_analysis_sections(text: str) -> tuple[list[str], str, str]:
    lowered = text.lower()

    trend_start = lowered.find("top 3 trend themes")
    comparison_start = lowered.find("company comparison")
    summary_start = lowered.find("executive summary")

    trend_text = text
    comparison_text = text
    summary_text = text

    if trend_start != -1 and comparison_start != -1:
        trend_text = text[trend_start:comparison_start]
    if comparison_start != -1 and summary_start != -1:
        comparison_text = text[comparison_start:summary_start]
    if summary_start != -1:
        summary_text = text[summary_start:]

    trends = _extract_bullets(trend_text, limit=3)
    return trends, comparison_text, summary_text


def _render_step(step: dict) -> None:
    if step.get("status") != "step":
        return

    if step.get("stage") == "analyst_agent":
        agent_name = step.get("agent", "analyst_agent")
        action = step.get("action", "unknown")
        tool_input = str(step.get("input", {}))
        status = "ok" if not str(step.get("observation", "")).lower().startswith("error") else "error"
        article_count = "-"
    else:
        agent_name = step.get("agent", "news_agent")
        action = step.get("action", "search_news")
        tool_input = str(step.get("input", {}))
        status = step.get("result_status", "ok")
        article_count = str(step.get("article_count", "-"))

    color = AGENT_COLORS.get(agent_name, "white")
    mark = "[green]✓[/green]" if status == "ok" else "[red]✗[/red]"
    console.print(
        f"[{color}]{agent_name}[/{color}] | "
        f"[bold]{action}[/bold] | "
        f"arg={_truncate(tool_input)} | "
        f"articles={article_count} | "
        f"{mark}"
    )


def _render_results(final_text: str, companies: list[str]) -> None:
    trends, comparison_text, summary_text = _parse_analysis_sections(final_text)

    console.print("\n[bold]Top Trend Themes[/bold]")
    if trends:
        for index, trend in enumerate(trends, 1):
            console.print(f"{index}. {trend}")
    else:
        console.print("1. No clear trend themes extracted.")

    table = Table(title="Company Comparison")
    table.add_column("Company", style="bold")
    table.add_column("Coverage Signal")

    comparison_lower = comparison_text.lower()
    for company in companies:
        if company.lower() in comparison_lower:
            signal = "Mentioned in model comparison output"
        else:
            signal = "No explicit mention found"
        table.add_row(company, signal)
    console.print()
    console.print(table)

    summary_body = summary_text.strip() or final_text.strip() or "No summary generated."
    console.print()
    console.print(Panel(summary_body, title="Executive Summary"))


@app.command()
def analyze(
    topic: str = typer.Option(..., "--topic", help="Research theme, e.g. 'AI chips'."),
    companies: str = typer.Option(
        ..., "--companies", help="Comma-separated company names, e.g. NVIDIA,AMD,Intel."
    ),
    days_back: int = typer.Option(7, "--days-back", min=1, help="Days back for news search."),
) -> None:
    company_list = _parse_companies(companies)

    _render_header(topic=topic, companies=company_list)
    console.print("\n[bold]Agent Step Log[/bold]")

    start = perf_counter()
    total_iterations = 0
    final_text = ""

    stream = orchestrate_news_analysis(
        query=topic,
        companies=company_list,
        days_back=days_back,
        limit=5,
    )
    while True:
        try:
            step = next(stream)
            _render_step(step)
            if step.get("status") == "step":
                total_iterations += 1
            if step.get("status") == "error":
                console.print(f"[red]Pipeline error:[/red] {step.get('error', 'Unknown error')}")
        except StopIteration as stop:
            final_text = stop.value or ""
            break

    _render_results(final_text=final_text, companies=company_list)

    elapsed = perf_counter() - start
    console.print(
        f"\n[dim]Elapsed: {elapsed:.2f}s | Total iterations: {total_iterations}[/dim]"
    )


if __name__ == "__main__":
    app()
