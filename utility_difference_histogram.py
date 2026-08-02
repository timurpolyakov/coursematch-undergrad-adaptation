"""Plot the distribution of per-student utility differences between policies.

The expected input is the JSON report produced by enrollment_simulator.py with
--report. A positive difference means the priority market gave the student
higher modeled utility; a negative difference means senior-first did better.
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

PROJECT_DIR = Path(__file__).resolve().parent


def load_utility_differences(report_path: Path) -> list[float]:
    """Read a simulator report and return market minus senior-first utility."""
    try:
        report: Any = json.loads(report_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(
            f"Report not found: {report_path}\n"
            "Generate it first with enrollment_simulator.py --report ..."
        ) from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"The report is not valid JSON: {report_path}\n{exc}") from exc

    if not isinstance(report, list) or not report:
        raise SystemExit("The allocation report must be a non-empty JSON list.")

    differences: list[float] = []
    for index, student in enumerate(report):
        if not isinstance(student, dict):
            raise SystemExit(f"Report entry {index} is not a JSON object.")

        # Newer reports already contain the paired difference.
        if "market_minus_senior_first_utility" in student:
            difference = student["market_minus_senior_first_utility"]
        else:
            # Fallback for reports that only contain the two utility values.
            try:
                difference = (
                    student["market"]["utility"]
                    - student["senior_first"]["utility"]
                )
            except (KeyError, TypeError) as exc:
                raise SystemExit(
                    f"Report entry {index} does not contain the required utility fields."
                ) from exc

        try:
            differences.append(float(difference))
        except (TypeError, ValueError) as exc:
            raise SystemExit(
                f"Report entry {index} has a nonnumeric utility difference: {difference!r}"
            ) from exc

    return differences


def percentage(count: int, total: int) -> float:
    return 100.0 * count / total if total else 0.0


def make_histogram(
    differences: list[float],
    output_path: Path,
    bins: int = 41,
    exclude_unchanged: bool = False,
    show: bool = False,
) -> None:
    """Create and save a poster-ready histogram."""
    tolerance = 1e-9

    improved = sum(value > tolerance for value in differences)
    harmed = sum(value < -tolerance for value in differences)
    unchanged = len(differences) - improved - harmed

    values_to_plot = (
        [value for value in differences if abs(value) > tolerance]
        if exclude_unchanged
        else differences
    )
    if not values_to_plot:
        raise SystemExit(
            "No values remain to plot. Remove --exclude-unchanged or use a report "
            "containing nonzero policy differences."
        )

    mean_difference = statistics.mean(differences)
    median_difference = statistics.median(differences)

    # Use a symmetric x-axis so gains and losses receive equal visual weight.
    max_abs = max(abs(value) for value in values_to_plot)
    x_limit = max(1.0, max_abs * 1.05)

    figure, axis = plt.subplots(figsize=(10, 6.5))

    counts, bin_edges, patches = axis.hist(
        values_to_plot,
        bins=bins,
        range=(-x_limit, x_limit),
        edgecolor="black",
        linewidth=0.7,
    )

    # Match the policy colors already used in data_analysis_graphs.py:
    # red for students better off under senior-first, blue for students better
    # off under the priority market, and gray for the bin containing zero.
    negative_color = "#E7180B"
    positive_color = "#34A6F4"
    neutral_color = "#8A8A8A"

    for left_edge, right_edge, patch in zip(bin_edges[:-1], bin_edges[1:], patches):
        center = (left_edge + right_edge) / 2
        if center < -tolerance:
            patch.set_facecolor(negative_color)
        elif center > tolerance:
            patch.set_facecolor(positive_color)
        else:
            patch.set_facecolor(neutral_color)

    axis.axvline(0, color="black", linewidth=1.8, label="No utility difference")
    axis.axvline(
        mean_difference,
        color="black",
        linestyle="--",
        linewidth=1.5,
        label=f"Mean difference = {mean_difference:+.2f}",
    )
    axis.axvline(
        median_difference,
        color="black",
        linestyle=":",
        linewidth=1.5,
        label=f"Median difference = {median_difference:+.2f}",
    )

    axis.set_title("Distribution of Student-level Utility Differences", fontsize=16, pad=12)
    axis.set_xlabel("Utility Difference (priority market - senior-first)", fontsize=12)
    axis.set_ylabel("Number of Students", fontsize=12)
    axis.grid(axis="y", linestyle="--", alpha=0.35)
    axis.set_axisbelow(True)

    summary = (
        f"Priority market higher: {improved:,} ({percentage(improved, len(differences)):.1f}%)\n"
        f"Senior-first higher: {harmed:,} ({percentage(harmed, len(differences)):.1f}%)\n"
        f"Unchanged: {unchanged:,} ({percentage(unchanged, len(differences)):.1f}%)"
    )
    axis.text(
        0.98,
        0.97,
        summary,
        transform=axis.transAxes,
        ha="right",
        va="top",
        fontsize=10,
        bbox={"boxstyle": "round,pad=0.45", "facecolor": "white", "alpha": 0.9},
    )

    axis.legend(loc="upper left", frameon=True)
    figure.tight_layout()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=300, bbox_inches="tight")
    print(f"Saved histogram to: {output_path.resolve()}")
    print(f"Students analyzed: {len(differences):,}")
    print(f"Mean utility difference: {mean_difference:+.2f}")
    print(f"Median utility difference: {median_difference:+.2f}")
    print(f"Priority market higher: {improved:,} ({percentage(improved, len(differences)):.1f}%)")
    print(f"Senior-first higher: {harmed:,} ({percentage(harmed, len(differences)):.1f}%)")
    print(f"Unchanged: {unchanged:,} ({percentage(unchanged, len(differences)):.1f}%)")

    if show:
        plt.show()
    else:
        plt.close(figure)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create a histogram of priority-market utility minus senior-first utility "
            "for every student in an allocation report."
        )
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=PROJECT_DIR / "allocation_report.json",
        help="Path to the JSON report produced by enrollment_simulator.py.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_DIR / "utility_difference_histogram.png",
        help="Path for the saved PNG file.",
    )
    parser.add_argument(
        "--bins",
        type=int,
        default=41,
        help="Number of histogram bins. An odd number keeps zero in a central bin.",
    )
    parser.add_argument(
        "--exclude-unchanged",
        action="store_true",
        help="Exclude zero-difference students from the bars while retaining them in the summary.",
    )
    parser.add_argument(
        "--show",
        action="store_true",
        help="Open the plot window after saving the PNG.",
    )
    args = parser.parse_args()

    if args.bins < 3:
        parser.error("--bins must be at least 3.")
    if args.bins % 2 == 0:
        parser.error("Use an odd number of bins so zero is centered in a bin.")

    return args


def main() -> None:
    args = parse_arguments()
    differences = load_utility_differences(args.report)
    make_histogram(
        differences=differences,
        output_path=args.output,
        bins=args.bins,
        exclude_unchanged=args.exclude_unchanged,
        show=args.show,
    )


if __name__ == "__main__":
    main()
