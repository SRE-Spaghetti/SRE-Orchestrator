"""Terminal UI components and formatting."""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.markdown import Markdown
from rich import box
from typing import Dict, Any
from datetime import datetime


console = Console()


def print_welcome():
    """Print welcome message."""
    welcome_text = """
# SRE Orchestrator CLI

Welcome to the interactive incident investigation interface.

Type your incident description in natural language, and the orchestrator will investigate it.

Commands:
- `exit` or `quit` - Exit the CLI
- `list` - List recent incidents
- `show <id>` - Show incident details
- `help` - Show this help message
"""
    console.print(Markdown(welcome_text))


def print_error(message: str):
    """Print an error message."""
    console.print(f"[bold red]Error:[/bold red] {message}")


def print_success(message: str):
    """Print a success message."""
    console.print(f"[bold green]✓[/bold green] {message}")


def print_info(message: str):
    """Print an info message."""
    console.print(f"[bold blue]ℹ[/bold blue] {message}")


def print_warning(message: str):
    """Print a warning message."""
    console.print(f"[bold yellow]⚠[/bold yellow] {message}")


def format_incident(incident: Dict[str, Any]) -> Panel:
    """
    Format incident data for display.

    Args:
        incident: Incident data dictionary

    Returns:
        Rich Panel with formatted incident
    """
    # Build incident details
    lines = []

    # Header
    lines.append(f"[bold]Incident ID:[/bold] {incident['id']}")
    lines.append(f"[bold]Status:[/bold] {format_status(incident['status'])}")
    lines.append(f"[bold]Created:[/bold] {format_timestamp(incident['created_at'])}")

    if incident.get("completed_at"):
        lines.append(
            f"[bold]Completed:[/bold] {format_timestamp(incident['completed_at'])}"
        )

    lines.append("")
    lines.append("[bold]Description:[/bold]")
    lines.append(incident["description"])

    # Extracted entities
    if incident.get("extracted_entities"):
        lines.append("")
        lines.append("[bold]Extracted Entities:[/bold]")
        for key, value in incident["extracted_entities"].items():
            if value:
                lines.append(f"  • {key}: {value}")

    # Root cause
    if incident.get("suggested_root_cause"):
        lines.append("")
        lines.append("[bold]Root Cause:[/bold]")
        lines.append(incident["suggested_root_cause"])

        if incident.get("confidence_score"):
            confidence = incident["confidence_score"]
            confidence_color = {"high": "green", "medium": "yellow", "low": "red"}.get(
                confidence, "white"
            )
            lines.append(
                f"[bold]Confidence:[/bold] [{confidence_color}]{confidence}[/{confidence_color}]"
            )

    # Evidence - show only collected evidence and recommendations, not raw tool calls
    if incident.get("evidence"):
        evidence = incident["evidence"]

        # Show collected evidence if available
        if evidence.get("collected_evidence"):
            lines.append("")
            lines.append("[bold]Evidence:[/bold]")
            for item in evidence["collected_evidence"]:
                source = item.get("source", "unknown")
                content_preview = str(item.get("content", ""))[:200]
                if len(str(item.get("content", ""))) > 200:
                    content_preview += "..."
                lines.append(f"  • {source}: {content_preview}")

        # Show recommendations if available
        if evidence.get("recommendations"):
            lines.append("")
            lines.append("[bold]Recommendations:[/bold]")
            for rec in evidence["recommendations"]:
                lines.append(f"  • {rec}")

    # Error message
    if incident.get("error_message"):
        lines.append("")
        lines.append(f"[bold red]Error:[/bold red] {incident['error_message']}")

    content = "\n".join(lines)

    return Panel(
        content,
        title=f"Incident {incident['id'][:8]}",
        border_style="blue",
        box=box.ROUNDED,
    )


def format_status(status: str) -> str:
    """Format status with color."""
    status_colors = {
        "pending": "yellow",
        "investigating": "blue",
        "completed": "green",
        "failed": "red",
    }
    color = status_colors.get(status, "white")
    return f"[{color}]{status}[/{color}]"


def format_timestamp(timestamp: str) -> str:
    """Format ISO timestamp to readable format."""
    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, AttributeError):
        return timestamp


def print_incident_table(incidents: list[Dict[str, Any]]):
    """
    Print a table of incidents.

    Args:
        incidents: List of incident dictionaries
    """
    if not incidents:
        print_info("No incidents found.")
        return

    table = Table(title="Recent Incidents", box=box.ROUNDED)

    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Status", style="magenta")
    table.add_column("Description", style="white")
    table.add_column("Created", style="green")

    for incident in incidents:
        incident_id = incident["id"][:8] + "..."
        status = incident["status"]
        description = (
            incident["description"][:50] + "..."
            if len(incident["description"]) > 50
            else incident["description"]
        )
        created = format_timestamp(incident["created_at"])

        table.add_row(incident_id, status, description, created)

    console.print(table)


def show_progress(message: str = "Investigating incident..."):
    """
    Create a progress indicator context manager.

    Args:
        message: Progress message to display

    Returns:
        Progress context manager
    """
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    )


def print_investigation_progress(step: str):
    """Print investigation step progress."""
    console.print(f"  [dim]→[/dim] {step}")
