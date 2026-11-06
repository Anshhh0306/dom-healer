"""Benchmark charts (static PNGs for the README, light + dark variants).

Palette and chrome follow a validated categorical palette (blue/orange slots,
checked for colour-vision-deficiency separation in both modes): thin bars with
a rounded data end, hairline solid gridlines, text in ink colours (never the
series colour), selective value labels, exact numbers in the README tables.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import PathPatch  # noqa: E402
from matplotlib.path import Path as MPath  # noqa: E402
from matplotlib.ticker import FixedLocator, FuncFormatter, NullLocator  # noqa: E402

THEMES = {
    "light": {
        "surface": "#fcfcfb",
        "ink": "#0b0b0b",
        "ink2": "#52514e",
        "muted": "#898781",
        "grid": "#e1e0d9",
        "axis": "#c3c2b7",
        "s1": "#2a78d6",
        "s2": "#eb6834",
    },
    "dark": {
        "surface": "#1a1a19",
        "ink": "#f0efec",
        "ink2": "#c3c2b7",
        "muted": "#898781",
        "grid": "#2c2c2a",
        "axis": "#383835",
        "s1": "#3987e5",
        "s2": "#d95926",
    },
}
FONT = ["system-ui", "Segoe UI", "Helvetica Neue", "Arial", "DejaVu Sans"]
ENGINE_PREFIX = "dom-healer"


def _setup(theme: dict, figsize: tuple[float, float]):
    plt.rcParams.update({"font.family": "sans-serif", "font.sans-serif": FONT, "font.size": 9})
    fig = plt.figure(figsize=figsize, dpi=200)
    fig.patch.set_facecolor(theme["surface"])
    return fig


def _style_axis(ax, theme: dict) -> None:
    ax.set_facecolor(theme["surface"])
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(theme["axis"])
    ax.spines["bottom"].set_linewidth(0.75)
    ax.tick_params(axis="x", colors=theme["muted"], labelsize=8, length=0, pad=4)
    ax.tick_params(axis="y", colors=theme["ink"], labelsize=8.5, length=0, pad=6)
    ax.grid(axis="x", color=theme["grid"], linewidth=0.6, linestyle="-")
    ax.set_axisbelow(True)


def _rounded_hbar(ax, y: float, width: float, height: float, color: str, radius_pt: float = 3.0, x0: float = 0.0,
                  log: bool = False) -> None:
    """Horizontal bar with a rounded data end (right) and a square baseline end."""
    if width <= 0:
        return
    fig = ax.figure
    bbox = ax.get_window_extent().transformed(fig.dpi_scale_trans.inverted())
    x_min, x_max = ax.get_xlim()
    y_min, y_max = ax.get_ylim()
    pts_per_x = bbox.width * 72 / (x_max - x_min)
    pts_per_y = bbox.height * 72 / abs(y_max - y_min)
    x1 = x0 + width
    rx = min(radius_pt / pts_per_x, width / 2)
    ry = min(radius_pt / pts_per_y, height / 2)
    y0, y1 = y - height / 2, y + height / 2
    k = 0.5523
    verts = [
        (x0, y0), (x1 - rx, y0),
        (x1 - rx + k * rx, y0), (x1, y0 + ry - k * ry), (x1, y0 + ry),
        (x1, y1 - ry),
        (x1, y1 - ry + k * ry), (x1 - rx + k * rx, y1), (x1 - rx, y1),
        (x0, y1), (x0, y0),
    ]
    codes = [MPath.MOVETO, MPath.LINETO, MPath.CURVE4, MPath.CURVE4, MPath.CURVE4, MPath.LINETO,
             MPath.CURVE4, MPath.CURVE4, MPath.CURVE4, MPath.LINETO, MPath.CLOSEPOLY]
    ax.add_patch(PathPatch(MPath(verts, codes), facecolor=color, edgecolor="none", zorder=3))


def _title(fig, theme: dict, title: str, subtitle: str, top: float = 0.965) -> None:
    fig.text(0.02, top, title, ha="left", va="top", fontsize=11.5, fontweight="semibold", color=theme["ink"])
    fig.text(0.02, top - 0.052, subtitle, ha="left", va="top", fontsize=8.2, color=theme["ink2"], linespacing=1.4)


def _legend(fig, theme: dict, items: list[tuple[str, str]], x: float, y: float) -> None:
    for label, color in items:
        fig.patches.append(plt.Rectangle((x, y - 0.012), 0.016, 0.024, transform=fig.transFigure, facecolor=color,
                                         edgecolor="none", figure=fig))
        fig.text(x + 0.022, y, label, ha="left", va="center", fontsize=8.5, color=theme["ink"])
        x += 0.022 + 0.0105 * len(label) + 0.03


def _method_order(results: dict) -> list[str]:
    overall = results["overall"]
    return sorted(overall, key=lambda m: (overall[m]["top1"], overall[m]["top3"]), reverse=True)


def accuracy_chart(results: dict, path: Path, mode: str) -> Path:
    theme = THEMES[mode]
    methods = _method_order(results)
    labels = [results["methods"][m] for m in methods]
    n = len(methods)
    fig = _setup(theme, (7.6, 0.42 * n + 1.65))
    ax = fig.add_axes([0.33, 0.1, 0.6, 0.66])
    _style_axis(ax, theme)
    ax.set_xlim(0, 1.0)
    ax.set_ylim(n - 0.5, -0.5)
    ax.xaxis.set_major_locator(FixedLocator([0, 0.2, 0.4, 0.6, 0.8, 1.0]))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v * 100:.0f}%"))
    ax.set_yticks(range(n))
    ax.set_yticklabels(labels)
    for tick, method in zip(ax.get_yticklabels(), methods):
        if results["methods"][method].startswith(ENGINE_PREFIX):
            tick.set_fontweight("semibold")
    fig.canvas.draw()
    bar_h, gap = 0.3, 0.035
    for i, m in enumerate(methods):
        o = results["overall"][m]
        y1 = i - (bar_h + gap) / 2
        y3 = i + (bar_h + gap) / 2
        _rounded_hbar(ax, y1, o["top1"], bar_h, theme["s1"])
        _rounded_hbar(ax, y3, o["top3"], bar_h, theme["s2"])
        for y, ci in ((y1, o["top1_ci"]), (y3, o["top3_ci"])):
            ax.plot([ci[0], ci[1]], [y, y], color=theme["ink2"], linewidth=0.8, alpha=0.75, zorder=4,
                    solid_capstyle="butt")
        label_x = max(o["top1_ci"][1], o["top3_ci"][1]) + 0.012
        ax.text(min(label_x, 0.985), y1, f"{o['top1'] * 100:.1f}%", va="center", ha="left" if label_x < 0.985 else "right",
                fontsize=8, color=theme["ink"], zorder=5)
    meta = results["meta"]
    _title(fig, theme, f"Selector recovery accuracy · {meta['n_suites']} mutated DOM suites, {meta['n_targets']} targets",
           "Share of targets whose true v2 element is ranked first (Top-1, labelled) or within the first three (Top-3). "
           "\nWhiskers: 95% Wilson interval. Learned rankers: "
           f"{meta['folds']}-fold cross-validation grouped by suite (no page in both train and test).")
    _legend(fig, theme, [("Top-1", theme["s1"]), ("Top-3", theme["s2"])], 0.33, 0.815)
    fig.savefig(path, facecolor=theme["surface"])
    plt.close(fig)
    return path


def latency_chart(results: dict, path: Path, mode: str) -> Path:
    theme = THEMES[mode]
    methods = _method_order(results)
    labels = [results["methods"][m] for m in methods]
    n = len(methods)
    fig = _setup(theme, (7.6, 0.36 * n + 2.1))
    ax = fig.add_axes([0.33, 0.11, 0.6, 0.58])
    _style_axis(ax, theme)
    ax.set_xscale("log")
    ax.set_xlim(0.005, 100)
    ax.set_ylim(n - 0.5, -0.5)
    ticks = [0.01, 0.1, 1, 10, 100]
    ax.xaxis.set_major_locator(FixedLocator(ticks))
    ax.xaxis.set_minor_locator(NullLocator())
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g} ms"))
    ax.set_yticks(range(n))
    ax.set_yticklabels(labels)
    for tick, method in zip(ax.get_yticklabels(), methods):
        if results["methods"][method].startswith(ENGINE_PREFIX):
            tick.set_fontweight("semibold")
    ax.axvline(5.0, color=theme["muted"], linewidth=0.9, zorder=2)
    ax.text(5.0 * 1.06, -0.62, "5 ms budget", fontsize=7.5, color=theme["ink2"], va="bottom", ha="left")
    for i, m in enumerate(methods):
        lat = results["latency_ms"][m]
        ax.plot([lat["p5"], lat["p95"]], [i, i], color=theme["s1"], linewidth=2, alpha=0.45, solid_capstyle="round",
                zorder=3)
        ax.scatter([lat["p50"]], [i], s=42, color=theme["s1"], edgecolors=theme["surface"], linewidths=1.5, zorder=4)
        ax.text(lat["p95"] * 1.18, i, f"{lat['p50']:.2f} ms", va="center", ha="left", fontsize=8, color=theme["ink"])
    meta = results["meta"]
    parse = results["parse_ms"]
    warm = results["latency_warm_ms"]["heuristic"]
    _title(fig, theme, "Latency per broken selector",
           f"Dot: median, line: p5–p95 over {meta['n_targets']} targets (median of {meta['repeats']} runs each). "
           f"v2 HTML parsing (p50 {parse['p50']:.2f} ms) is excluded everywhere.\n"
           "dom-healer is measured cold: fresh page index and cleared caches every run. Baselines only evaluate a selector.\n"
           f"Reusing the page index (warm), the heuristic's median is {warm['p50']:.2f} ms and its p95 {warm['p95']:.2f} ms.")
    fig.savefig(path, facecolor=theme["surface"])
    plt.close(fig)
    return path


def category_chart(results: dict, path: Path, mode: str) -> Path:
    theme = THEMES[mode]
    methods = _method_order(results)
    cats = list(results["by_category"])
    n = len(methods)
    fig = _setup(theme, (9.2, 0.25 * n * 2 + 2.1))
    cols = 2
    rows = (len(cats) + 1) // cols
    width, height = 0.26, 0.66 / rows
    for idx, cat in enumerate(cats):
        r, c = divmod(idx, cols)
        left = 0.27 + c * 0.40
        bottom = 0.08 + (rows - 1 - r) * (height + 0.075)
        ax = fig.add_axes([left, bottom, width, height])
        _style_axis(ax, theme)
        ax.set_xlim(0, 1.0)
        ax.set_ylim(n - 0.5, -0.5)
        ax.xaxis.set_major_locator(FixedLocator([0, 0.5, 1.0]))
        ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v * 100:.0f}%"))
        ax.set_yticks(range(n))
        if c == 0:
            ax.set_yticklabels([results["methods"][m] for m in methods], fontsize=7.5)
            for tick, method in zip(ax.get_yticklabels(), methods):
                if results["methods"][method].startswith(ENGINE_PREFIX):
                    tick.set_fontweight("semibold")
        else:
            ax.set_yticklabels([])
        fig.canvas.draw()
        row = results["by_category"][cat]
        for i, m in enumerate(methods):
            v = row[m]["top1"]
            _rounded_hbar(ax, i, v, 0.56, theme["s1"], radius_pt=2.5)
            inside = v >= 0.8
            ax.text(v - 0.025 if inside else v + 0.02, i, f"{v * 100:.0f}%", va="center",
                    ha="right" if inside else "left", fontsize=7, color="#ffffff" if inside else theme["ink"], zorder=5)
        n_targets = row[methods[0]]["n"]
        ax.set_title(f"{cat}  ·  {n_targets} targets", loc="left", fontsize=9, color=theme["ink"], fontweight="semibold",
                     pad=6)
    _title(fig, theme, "Top-1 selector recovery by page category",
           "Share of targets whose true v2 element is ranked first, per fixture category (10 suites each).",
           top=0.975)
    fig.savefig(path, facecolor=theme["surface"])
    plt.close(fig)
    return path


def render_all(results: dict, out_dir: Path) -> list[Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for mode in ("light", "dark"):
        suffix = "" if mode == "light" else "_dark"
        written.append(accuracy_chart(results, out_dir / f"recovery_accuracy{suffix}.png", mode))
        written.append(latency_chart(results, out_dir / f"latency{suffix}.png", mode))
        written.append(category_chart(results, out_dir / f"recovery_by_category{suffix}.png", mode))
    return written
