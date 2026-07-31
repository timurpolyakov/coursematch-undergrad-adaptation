import json
import statistics
from pathlib import Path

import matplotlib.pyplot as plt


# Gets simulation data

report = json.loads(
    Path("student_allocation_comparison.json").read_text(encoding="utf-8")
)

profiles = json.loads(
    Path("cornell_fa25_synthetic_profiles.json").read_text(encoding="utf-8")
)

catalog = json.loads(
    Path("cornell_courses_FA25_all.json").read_text(encoding="utf-8")
)

profiles_by_id = {
    profile["id"]: profile
    for profile in profiles
}

years = ["Freshman", "Sophomore", "Junior", "Senior"]
policies = ["senior_first", "market"]
policy_labels = ["Senior-first", "Priority market"]
colors = ["#4C78A8", "#F58518"]


# GRAPH 1 shows average utility, lines are standard deviation

utilities = {
    year: {
        "senior_first": [],
        "market": []
    }
    for year in years
}

for student in report:
    year = student["year"]

    utilities[year]["senior_first"].append(
        student["senior_first"]["utility"]
    )

    utilities[year]["market"].append(
        student["market"]["utility"]
    )

senior_first_averages = []
market_averages = []

senior_first_stddevs = []
market_stddevs = []

for year in years:
    senior_first_scores = utilities[year]["senior_first"]
    market_scores = utilities[year]["market"]

    # The average is height of each bar
    senior_first_averages.append(
        statistics.mean(senior_first_scores)
    )

    market_averages.append(
        statistics.mean(market_scores)
    )

    # The standard deviation is error bar
    senior_first_stddevs.append(
        statistics.stdev(senior_first_scores)
    )

    market_stddevs.append(
        statistics.stdev(market_scores)
    )


# Graph 1: average utility by year, with standard-deviation error bars

x_positions = list(range(len(years)))
bar_width = 0.35

plt.figure(figsize=(10, 6))

plt.bar(
    [x - bar_width / 2 for x in x_positions],
    senior_first_averages,
    width=bar_width,
    yerr=senior_first_stddevs,
    capsize=6,
    label="Senior-first",
    color=colors[0],
    edgecolor="black"
)

plt.bar(
    [x + bar_width / 2 for x in x_positions],
    market_averages,
    width=bar_width,
    yerr=market_stddevs,
    capsize=6,
    label="Priority market",
    color=colors[1],
    edgecolor="black"
)

plt.xticks(x_positions, years)
plt.ylabel("Average student utility")
plt.title("Average utility by class year, with standard deviation bars")
plt.legend()
plt.grid(axis="y", linestyle="--", alpha=0.4)
plt.tight_layout()

plt.savefig("average_utility_by_year_with_stddev.png", dpi=300)
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

print("\nOriginal policy-comparison metrics")
print("-" * 70)

for metric_name in metrics["Senior-first"]:
    senior_first_value = metrics["Senior-first"][metric_name]
    market_value = metrics["Priority market"][metric_name]

    print(
        f"{metric_name:<32} "
        f"Senior-first: {senior_first_value:>10.2f}   "
        f"Priority market: {market_value:>10.2f}"
    )


# Make Graph 2:

metric_names = list(metrics["Senior-first"].keys())

fig, axes = plt.subplots(2, 2, figsize=(12, 8))
axes = axes.flatten()

for axis, metric_name in zip(axes, metric_names):
    values = [
        metrics["Senior-first"][metric_name],
        metrics["Priority market"][metric_name]
    ]

    bars = axis.bar(
        policy_labels,
        values,
        color=colors
    )

    axis.set_title(metric_name)
    axis.set_ylabel(metric_name)
    axis.grid(axis="y", linestyle="--", alpha=0.4)

    # Write each exact value above its bar
    for bar, value in zip(bars, values):
        axis.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{value:.2f}",
            ha="center",
            va="bottom"
        )

fig.suptitle("Senior-first registration vs. priority market", fontsize=16)
plt.tight_layout()

# Save the second graph in project folder
plt.savefig("policy_metric_comparison.png", dpi=300)

plt.show()
