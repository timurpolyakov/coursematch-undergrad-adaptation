import json
import statistics
import subprocess
import sys
from pathlib import Path

import matplotlib.pyplot as plt


profiles = json.loads(
    Path(__file__).with_name("cornell_fa25_synthetic_profiles.json").read_text(encoding="utf-8")
)

# Graphs should represent the complete synthetic population. Refresh a missing
# or sampled report automatically before reading it.
report_path = Path(__file__).with_name("allocation_report.json")
if not report_path.exists() or len(json.loads(report_path.read_text(encoding="utf-8"))) != len(profiles):
    print(f"Generating a full-population report for {len(profiles):,} profiles…")
    subprocess.run(
        [
            sys.executable,
            "enrollment_simulator.py",
            "--students",
            "0",
            "--trials",
            "1",
            "--seed",
            "2025",
            "--report",
            report_path.name,
        ],
        check=True,
        cwd=Path(__file__).parent,
    )
report = json.loads(report_path.read_text(encoding="utf-8"))

catalog = json.loads(
    Path(__file__).with_name("cornell_courses_FA25_all.json").read_text(encoding="utf-8")
)

profiles_by_id = {
    profile["id"]: profile
    for profile in profiles
}

years = ["Freshman", "Sophomore", "Junior", "Senior"]
policies = ["senior_first", "market"]
policy_labels = ["Senior-first", "Priority market"]
# GRAPH 1: paired change in utility by class year. Plotting the change directly
# avoids hiding a policy effect behind the much larger variation in individual
# utility levels.
utility_deltas = {
    year: [
        student["market"]["utility"] - student["senior_first"]["utility"]
        for student in report
        if student["year"] == year
    ]
    for year in years
}
average_deltas = [statistics.mean(utility_deltas[year]) for year in years]
ci95 = [
    1.96 * statistics.stdev(utility_deltas[year]) / len(utility_deltas[year]) ** 0.5
    for year in years
]
colors = ["#2E8B57" if delta >= 0 else "#C23B22" for delta in average_deltas]

figure, axis = plt.subplots(figsize=(10, 6))
bars = axis.bar(years, average_deltas, yerr=ci95, capsize=6, color=colors, edgecolor="black")
axis.axhline(0, color="black", linewidth=1)
axis.set_ylabel("Market − senior-first utility")
axis.set_title("Change in average utility by class year (95% CI)")
axis.grid(axis="y", linestyle="--", alpha=0.4)
for bar, delta in zip(bars, average_deltas):
    vertical_alignment = "bottom" if delta >= 0 else "top"
    offset = 4 if delta >= 0 else -4
    axis.annotate(f"{delta:+.1f}", (bar.get_x() + bar.get_width() / 2, delta),
                  xytext=(0, offset), textcoords="offset points", ha="center", va=vertical_alignment)
figure.tight_layout()
figure.savefig("utility_delta_by_year.png", dpi=300)
plt.show()

# Graph 2; utility, average credits, major-course share, and senior
# major-course access for the senior-first vs the priority market method

metrics = {
    "Senior-first": {},
    "Priority market": {}
}

for policy, label in zip(policies, policy_labels):

    # Average utility across all students
    average_utility = sum(
        student[policy]["utility"]
        for student in report
    ) / len(report)

    # Average credits across all students
    average_credits = sum(
        student[policy]["credits"]
        for student in report
    ) / len(report)

    # Major-course share:
    # Count major-related course assignments divided by all course assignments
    major_course_count = 0
    total_course_count = 0

    # Senior major-course access:
    # Count whether each eligible senior receives their top upper-level major course
    eligible_seniors = 0
    seniors_with_top_major_course = 0

    for student in report:
        student_id = student["student_id"]
        profile = profiles_by_id[student_id]
        major_subjects = profile["major_subjects"]

        assigned_courses = student[policy]["courses"]

        for course_name in assigned_courses:
            course = catalog[course_name]

            total_course_count += 1

            if course["department"] in major_subjects:
                major_course_count += 1

        # Only calculate senior course access for seniors
        if student["year"] == "Senior":

            # ranked_preferences is already arranged from highest utility to lowest
            # Find senior's highest-ranked upper-level major course
            top_major_course = None

            for preference in student["ranked_preferences"]:
                course_name = preference["course"]
                course = catalog[course_name]

                is_major_course = course["department"] in major_subjects
                is_upper_level = course["level"] >= 3000

                if is_major_course and is_upper_level:
                    top_major_course = course_name
                    break

            # Some seniors may have no upper-level major course in their ranking
            if top_major_course is not None:
                eligible_seniors += 1

                if top_major_course in assigned_courses:
                    seniors_with_top_major_course += 1

    metrics[label]["Average utility"] = average_utility
    metrics[label]["Average credits"] = average_credits
    metrics[label]["Major-course share (%)"] = (
        major_course_count / total_course_count * 100
    )
    metrics[label]["Senior major-course access (%)"] = (
        seniors_with_top_major_course / eligible_seniors * 100
    )


# Print metrics in terminal

print("\nPolicy-comparison metrics")
print("-" * 70)

for metric_name in metrics["Senior-first"]:
    senior_first_value = metrics["Senior-first"][metric_name]
    market_value = metrics["Priority market"][metric_name]

    print(
        f"{metric_name:<32} "
        f"Senior-first: {senior_first_value:>10.2f}   "
        f"Priority market: {market_value:>10.2f}"
    )


# Graph 2: direct policy changes, retaining each metric's natural unit.
metric_names = list(metrics["Senior-first"].keys())

fig, axes = plt.subplots(2, 2, figsize=(12, 8))
axes = axes.flatten()

for axis, metric_name in zip(axes, metric_names):
    delta = metrics["Priority market"][metric_name] - metrics["Senior-first"][metric_name]
    color = "#2E8B57" if delta >= 0 else "#C23B22"
    bar = axis.bar(["Market change"], [delta], color=color, edgecolor="black")[0]
    axis.axhline(0, color="black", linewidth=1)
    axis.set_title(metric_name)
    axis.set_ylabel("Market − senior-first")
    axis.grid(axis="y", linestyle="--", alpha=0.4)
    axis.annotate(f"{delta:+.2f}", (bar.get_x() + bar.get_width() / 2, delta),
                  xytext=(0, 4 if delta >= 0 else -4), textcoords="offset points",
                  ha="center", va="bottom" if delta >= 0 else "top")

fig.suptitle("Market change relative to senior-first", fontsize=16)
plt.tight_layout()

# Save the second graph in project folder
plt.savefig("policy_metric_comparison.png", dpi=300)

plt.show()
