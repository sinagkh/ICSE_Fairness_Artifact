#!/usr/bin/env python3
"""Regenerate a dependency-free SVG version of the localization heatmap.

The submission PDF is included in generated/figures/localization_four_panel2.pdf.
This script uses only Python's standard library so availability reviewers can
confirm the plotted values without installing plotting packages.
"""

from __future__ import annotations

import csv
import html
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "results/localization/localization_four_panel.csv"
OUTPUT = ROOT / "generated/figures/localization_four_panel2_regenerated.svg"

CELL_W = 92
CELL_H = 24
LEFT = 150
TOP = 72
PANEL_GAP_X = 42
PANEL_GAP_Y = 60
TITLE_H = 22


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def shade(value: float, vmax: float) -> str:
    ratio = max(0.0, min(1.0, value / vmax if vmax else 0.0))
    level = int(round(255 - 210 * ratio))
    return f"rgb({level},{level},{level})"


def text(svg: list[str], x: float, y: float, value: object, size: int = 10, anchor: str = "start", weight: str = "normal") -> None:
    svg.append(
        f'<text x="{x:.1f}" y="{y:.1f}" font-family="Arial, sans-serif" '
        f'font-size="{size}" text-anchor="{anchor}" font-weight="{weight}">{esc(value)}</text>'
    )


def main() -> None:
    rows: list[dict[str, str]] = []
    with INPUT.open(newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise SystemExit(f"empty input: {INPUT}")

    panels: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        panels[row["panel"]].append(row)

    values = [float(r["mean"]) for r in rows]
    vmax = sorted(values)[int(0.95 * (len(values) - 1))]
    vmax = max(vmax, 0.01)

    panel_keys = list(panels)
    panel_shapes = []
    for key in panel_keys:
        part = panels[key]
        features = sorted(
            {(r["feature_label"], int(r["feature_order"])) for r in part},
            key=lambda x: x[1],
        )
        models = sorted(
            {(r["model_label"], int(r["model_order"])) for r in part},
            key=lambda x: x[1],
        )
        panel_shapes.append((features, models))

    panel_w = LEFT + max(len(models) for _, models in panel_shapes) * CELL_W + 12
    panel_h = TOP + max(len(features) for features, _ in panel_shapes) * CELL_H + 18
    width = 2 * panel_w + PANEL_GAP_X
    height = 2 * panel_h + PANEL_GAP_Y + 20

    svg: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
    ]

    for idx, key in enumerate(panel_keys):
        col = idx % 2
        row_idx = idx // 2
        origin_x = col * (panel_w + PANEL_GAP_X)
        origin_y = row_idx * (panel_h + PANEL_GAP_Y)
        part = panels[key]
        title = part[0]["panel_title"]
        features, models = panel_shapes[idx]
        feature_labels = [f for f, _ in features]
        model_labels = [m for m, _ in models]
        lookup = {
            (r["feature_label"], r["model_label"]): float(r["mean"])
            for r in part
        }

        text(svg, origin_x + panel_w / 2, origin_y + 24, title, size=15, anchor="middle", weight="bold")
        for j, model in enumerate(model_labels):
            x = origin_x + LEFT + j * CELL_W + CELL_W / 2
            text(svg, x, origin_y + TOP - 12, model.replace("\n", " "), size=9, anchor="middle")

        for i, feature in enumerate(feature_labels):
            y = origin_y + TOP + i * CELL_H
            text(svg, origin_x + LEFT - 8, y + 16, feature, size=9, anchor="end")
            for j, model in enumerate(model_labels):
                value = lookup[(feature, model)]
                x = origin_x + LEFT + j * CELL_W
                fill = shade(value, vmax)
                svg.append(
                    f'<rect x="{x}" y="{y}" width="{CELL_W}" height="{CELL_H}" '
                    f'fill="{fill}" stroke="rgb(180,180,180)" stroke-width="0.5"/>'
                )
                label = f"{value:.3f}" if 0 < value < 0.01 else f"{value:.2f}"
                text(svg, x + CELL_W / 2, y + 16, label, size=8, anchor="middle")

    svg.append("</svg>")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(svg) + "\n")
    print(f"wrote {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
