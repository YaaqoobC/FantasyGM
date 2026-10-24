"""Create a self-contained visual report from validation predictions."""

import json
import logging
from pathlib import Path

from plotly.offline import get_plotlyjs

LOGGER = logging.getLogger(__name__)

def write_validation_report(summary, metadata, actual, predicted, output_dir):
    """Embed all eligible validation rows and Plotly for offline exploration."""
    LOGGER.info("Preparing visual report for %s validation appearances", f"{len(metadata):,}")
    if (
        not actual.index.is_unique
        or not actual.index.equals(predicted.index)
        or not actual.index.equals(metadata.index)
    ):
        raise ValueError("Report metadata, actuals, and predictions must align")
    if not metadata["season"].eq(summary["validation_season"]).all():
        raise ValueError("Visual reports must contain validation rows only")
    statistics = list(summary["validation_metrics"])
    details = metadata[["player_id", "player_name", "game_id", "game_date"]].copy()
    details["player_id"] = details["player_id"].astype(str)
    details["game_date"] = details["game_date"].dt.strftime("%Y-%m-%d")
    rows = []
    for game, observed, forecast in zip(
        details.to_dict(orient="records"),
        actual[statistics].to_dict(orient="records"),
        predicted[statistics].to_dict(orient="records"),
    ):
        rows.append({**game, "actual": observed, "predicted": forecast})
    payload = {"summary": summary, "statistics": statistics, "rows": rows}
    # Player names are embedded as data, never interpreted as HTML or scripts.
    serialized = json.dumps(payload, allow_nan=False).replace("<", "\\u003c")
    template_dir = Path(__file__).with_name("templates")
    LOGGER.info("Embedding charts and validation data for offline viewing")
    html = (template_dir / "validation.html").read_text()
    html = html.replace("__PLOTLY_JS__", get_plotlyjs())
    html = html.replace("__REPORT_JS__", (template_dir / "validation.js").read_text())
    html = html.replace("__REPORT_DATA__", serialized)
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "metrics.json").write_text(json.dumps(summary, indent=2, allow_nan=False))
    report_path = output_dir / "index.html"
    report_path.write_text(html)
    LOGGER.info("Visual report saved: %s", report_path)
    return report_path
