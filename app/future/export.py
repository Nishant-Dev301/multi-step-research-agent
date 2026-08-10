"""
Report export — user-friendly enhancement (see ENHANCEMENTS.md).

Status: 🟢 runnable today. Wired into main.py as:
    GET /research/export/{format}?query=...

Converts a ResearchReport into Markdown or plain text so a user can
download/share a result without copy-pasting JSON.
"""

from __future__ import annotations

from app.orchestrator import ResearchReport


def to_markdown(report: ResearchReport) -> str:
    lines = [f"# Research Report: {report.query}", ""]
    lines.append(f"*Generated in {report.duration_seconds}s*")
    lines.append("")

    for section in report.sections:
        lines.append(f"## {section.task_type.replace('_', ' ').title()}")
        lines.append(section.content)
        if section.sources:
            lines.append("")
            lines.append("**Sources:**")
            for src in section.sources:
                lines.append(f"- {src}")
        lines.append("")
        lines.append(
            f"*Payment: {section.payment_status} (${section.payment_amount:.4f}) "
            f"· Confidence: {section.confidence:.2f}*"
        )
        lines.append("")

    lines.append("---")
    lines.append("## Payment Summary")
    summary = report.payment_summary
    lines.append(f"- Total spent: ${summary['total_spent']:.4f} / ${summary['budget']:.2f} budget")
    lines.append(f"- Calls: {summary['calls']} ({summary['settled']} settled, {summary['rejected']} rejected)")

    return "\n".join(lines)


def to_plaintext(report: ResearchReport) -> str:
    lines = [f"RESEARCH REPORT: {report.query}", "=" * 60, ""]
    for section in report.sections:
        lines.append(f"[{section.task_type.upper()}]")
        lines.append(section.content)
        if section.sources:
            lines.append("Sources: " + ", ".join(section.sources))
        lines.append("")
    return "\n".join(lines)


EXPORTERS = {
    "markdown": (to_markdown, "text/markdown"),
    "txt": (to_plaintext, "text/plain"),
}
