import json
import statistics
from pathlib import Path

#Retrieves simulation data
report_path = Path("student_allocation_comparison.json")
report = json.loads(report_path.read_text(encoding="utf-8"))

# Gets utilities separately for each class year
utilities = {
    "Freshman": {"senior_first": [], "market": []},
    "Sophomore": {"senior_first": [], "market": []},
    "Junior": {"senior_first": [], "market": []},
    "Senior": {"senior_first": [], "market": []},
}

for student in report:
    year = student["year"]

    senior_first_utility = student["senior_first"]["utility"]
    market_utility = student["market"]["utility"]

    utilities[year]["senior_first"].append(senior_first_utility)
    utilities[year]["market"].append(market_utility)

print("Standard deviation of student utility by class year")
print("-" * 62)
print(f"{'Class year':<12} {'Students':>10} {'Senior-first':>18} {'Priority market':>18}")
print("-" * 62)

for year in ("Freshman", "Sophomore", "Junior", "Senior"):
    senior_first_scores = utilities[year]["senior_first"]
    market_scores = utilities[year]["market"]


    senior_first_stddev = statistics.stdev(senior_first_scores)
    market_stddev = statistics.stdev(market_scores)

    print(
        f"{year:<12} "
        f"{len(senior_first_scores):>10,} "
        f"{senior_first_stddev:>18.2f} "
        f"{market_stddev:>18.2f}"
    )
