"""Markdown emitter for HMM analysis reports."""
from pathlib import Path

import numpy as np


def _format_pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def _format_signed(x: float) -> str:
    return f"{x:+.2f}"


def _markdown_table_header(cols: list[str]) -> str:
    sep = "|" + "|".join("---" for _ in cols) + "|"
    head = "| " + " | ".join(cols) + " |"
    return f"{head}\n{sep}"


def _summary_section(report: dict) -> str:
    return (
        "## Summary\n\n"
        f"- Symbol: `{report['symbol']}`\n"
        f"- Strategy: `{report['strategy']}`\n"
        f"- Bars analyzed: {report['n_bars']} (1H × 6m)\n"
        f"- Best K (via BIC): **{report['best_k']}**\n"
        f"- BIC: {report['bic']:.1f}\n"
        f"- Log-likelihood: {report['log_likelihood']:.1f}\n"
    )


def _distribution_section(report: dict) -> str:
    lines = ["## Regime Distribution\n",
             _markdown_table_header(["State", "Label", "% bars", "Mean return", "Mean vol", "Low sample"])]
    for sid in sorted(report["labels"].keys()):
        info = report["labels"][sid]
        flag = "⚠️ yes" if info["low_sample"] else "no"
        lines.append(f"| {sid} | {info['label']} | {_format_pct(info['pct_bars'])} | "
                     f"{info['mean_return']:+.4f} | {info['mean_vol']:.4f} | {flag} |")
    return "\n".join(lines) + "\n"


def _transition_section(report: dict) -> str:
    matrix = report["transition_matrix"]
    labels = [report["labels"][sid]["label"] for sid in sorted(report["labels"].keys())]
    k = len(labels)
    lines = ["## Transition Matrix\n",
             _markdown_table_header(["From \\ To", *labels])]
    for i in range(k):
        row = [labels[i]] + [f"{matrix[i, j]:.2f}" for j in range(k)]
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines) + "\n"


def _backtest_section(report: dict) -> str:
    lines = ["## Backtest per Regime\n",
             _markdown_table_header(["Regime", "% time", "Trades", "WR", "PF",
                                     "Net PnL%", "Max DD%", "Flag"])]
    for r in report["backtests"]:
        flag = "⚠️ low-trade" if r.low_trade_count else ""
        lines.append(f"| {r.regime_label} | {_format_pct(r.pct_time)} | {r.trades} | "
                     f"{r.wr:.1f}% | {r.pf:.2f} | {_format_signed(r.net_pnl_pct)} | "
                     f"{r.max_dd_pct:.1f} | {flag} |")
    return "\n".join(lines) + "\n"


def _recommendations_section(report: dict) -> str:
    note = report.get("current_mapping_note")
    if note is None:
        return "## Recommendations\n\nNo `regime_mapping.json` comparison requested.\n"
    return f"## Recommendations\n\n{note}\n"


def _caveats_section(report: dict) -> str:
    caveats = report.get("caveats") or []
    body = "\n".join(f"- {c}" for c in caveats) if caveats else "- None flagged."
    body += (
        "\n- HMM seed fixed for reproducibility; different seeds may yield slightly different labelings."
        "\n- Backtest uses TP1-or-SL resolution over max 24×15m bars (6h hold)."
        "\n- Regime assigned by **entry-bar 1H state**, not exit-bar state."
    )
    return f"## Caveats\n\n{body}\n"


def emit_markdown(report: dict, out_path: Path) -> None:
    """Write the full markdown report to out_path."""
    sections = [
        f"# HMM Analysis — {report['symbol']} × {report['strategy']} — {report['date']}\n",
        _summary_section(report),
        _distribution_section(report),
        _transition_section(report),
        _backtest_section(report),
        _recommendations_section(report),
        _caveats_section(report),
    ]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(sections))


def emit_html(report: dict, out_path: Path) -> None:
    """Emit interactive plotly HTML. Raises ImportError if plotly missing."""
    try:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
    except ImportError as exc:
        raise ImportError("plotly not installed; run pip install plotly to enable --html") from exc

    # V1: 2 panels — transition matrix heatmap + equity curve table
    fig = make_subplots(rows=2, cols=1,
                        subplot_titles=("Transition Matrix", "Backtest per Regime"),
                        specs=[[{"type": "heatmap"}], [{"type": "table"}]])

    matrix = report["transition_matrix"]
    labels = [report["labels"][sid]["label"] for sid in sorted(report["labels"].keys())]
    fig.add_trace(go.Heatmap(z=matrix, x=labels, y=labels, colorscale="Blues",
                             showscale=True, zmin=0, zmax=1), row=1, col=1)

    rows = report["backtests"]
    fig.add_trace(go.Table(
        header=dict(values=["Regime", "% time", "Trades", "WR", "PF", "Net%", "MaxDD%"]),
        cells=dict(values=[
            [r.regime_label for r in rows],
            [f"{r.pct_time * 100:.1f}%" for r in rows],
            [r.trades for r in rows],
            [f"{r.wr:.1f}%" for r in rows],
            [f"{r.pf:.2f}" for r in rows],
            [f"{r.net_pnl_pct:+.2f}" for r in rows],
            [f"{r.max_dd_pct:.1f}" for r in rows],
        ]),
    ), row=2, col=1)

    fig.update_layout(title=f"HMM Analysis — {report['symbol']} × {report['strategy']}",
                      height=800)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(out_path))
