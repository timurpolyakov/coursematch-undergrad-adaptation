"""Search fair upper-level major-course price modifiers."""

import argparse
import json
import math
import random
from dataclasses import replace
from pathlib import Path
from statistics import mean, stdev

from enrollment_simulator import load_courses, load_profiles, market_allocation, students_from_profiles


def cohort_outcomes(students, courses, allocations):
    outcomes = {}
    for year in ("Senior", "Junior", "Sophomore", "Freshman"):
        cohort = [student for student in students if student.year == year]
        if not cohort:
            continue
        utility = credits = major_floor_met = senior_top_wins = senior_top_total = 0.0
        for student in cohort:
            bundle = allocations[student.name]
            utility += sum(student.utilities[name] for name in bundle)
            earned_credits = sum(courses[name].credits for name in bundle)
            credits += earned_credits
            major_subjects = student.major_subjects or {student.major}
            earned_major = sum(courses[name].credits for name in bundle if courses[name].department in major_subjects)
            major_floor_met += earned_major >= student.major_credit_minimum
            if year == "Senior":
                choices = [name for name in student.utilities if courses[name].department in major_subjects and courses[name].level >= 3000]
                if choices:
                    senior_top_total += 1
                    senior_top_wins += max(choices, key=student.utilities.get) in bundle
        outcomes[year] = {"average_utility": utility / len(cohort), "average_credits": credits / len(cohort), "major_floor_met": major_floor_met / len(cohort)}
        if year == "Senior":
            outcomes[year]["top_graduation_course_access"] = senior_top_wins / max(1, senior_top_total)
    return outcomes


def summarize(values):
    """Return a mean and an approximate 95% confidence interval."""
    average = mean(values)
    if len(values) < 2:
        return {"mean": average, "ci95": [average, average], "n": len(values)}
    margin = 1.96 * stdev(values) / math.sqrt(len(values))
    return {"mean": average, "ci95": [average - margin, average + margin], "n": len(values)}


def evaluate(policy, catalog, profiles, students_count, trials, seed):
    """Evaluate with common random numbers, retaining trial-level outcomes."""
    trial_results = []
    for trial in range(trials):
        rng = random.Random(seed + trial)
        students = students_from_profiles(profiles, catalog, rng, students_count)
        students = [replace(student, upper_major_price_modifier=policy[student.year]) for student in students]
        trial_results.append(cohort_outcomes(students, catalog, market_allocation(students, catalog)))
    outcomes = {
        year: {metric: mean(result[year][metric] for result in trial_results) for metric in trial_results[0][year]}
        for year in trial_results[0]
    }
    uncertainty = {
        year: {metric: summarize([result[year][metric] for result in trial_results]) for metric in trial_results[0][year]}
        for year in trial_results[0]
    }
    return outcomes, uncertainty


def score(outcomes, senior_access_floor):
    senior, junior = outcomes["Senior"], outcomes["Junior"]
    eligible = senior["top_graduation_course_access"] >= senior_access_floor
    value = junior["major_floor_met"] * 10_000 + junior["average_utility"] * 10 + junior["average_credits"] + senior["average_utility"] * 0.01
    return eligible, value


def main():
    parser = argparse.ArgumentParser(description="Find fair upper-level major-course price modifiers.")
    parser.add_argument("--catalog", default="cornell_courses_FA25_all.json")
    parser.add_argument("--profiles", default="cornell_fa25_synthetic_profiles.json")
    parser.add_argument("--students", type=int, default=4000)
    parser.add_argument("--trials", type=int, default=5)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--senior-access-floor", type=float, default=0.95)
    parser.add_argument("--output", default="weight_tuning_results.json")
    parser.add_argument("--senior-weights", default="0.30,0.35,0.40",
                        help="Comma-separated senior weights to evaluate.")
    parser.add_argument("--junior-weights", default="0.40,0.45,0.50",
                        help="Comma-separated junior weights to evaluate.")
    parser.add_argument("--sophomore-weights", default="0.60,0.70,0.80",
                        help="Comma-separated sophomore weights to evaluate.")
    args = parser.parse_args()
    catalog, profiles = load_courses(args.catalog), load_profiles(args.profiles)
    parse_weights = lambda raw: [float(value) for value in raw.split(",")]
    senior_weights = parse_weights(args.senior_weights)
    junior_weights = parse_weights(args.junior_weights)
    sophomore_weights = parse_weights(args.sophomore_weights)
    candidates = []
    for senior in senior_weights:
        for junior in junior_weights:
            for sophomore in sophomore_weights:
                if senior < junior < sophomore:
                    # Freshmen are not eligible for upper-level courses in the
                    # synthetic profiles, so this value is inert; retain the
                    # standard major-course rate for clarity.
                    policy = {"Senior": senior, "Junior": junior, "Sophomore": sophomore, "Freshman": 0.70}
                    outcomes, uncertainty = evaluate(policy, catalog, profiles, args.students, args.trials, args.seed)
                    eligible, value = score(outcomes, args.senior_access_floor)
                    candidates.append({"policy": policy, "outcomes": outcomes, "uncertainty": uncertainty,
                                       "eligible": eligible, "score": value})
    candidates.sort(key=lambda result: (result["eligible"], result["score"]), reverse=True)
    result = {
        "experiment": {
            "seed": args.seed, "trials": args.trials, "students_per_trial": args.students,
            "senior_access_floor": args.senior_access_floor,
            "weights": {"Senior": senior_weights, "Junior": junior_weights, "Sophomore": sophomore_weights},
            "pairing": "Each policy uses the same seed + trial preference draws.",
        },
        "candidates": candidates,
    }
    Path(args.output).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(candidates[0], indent=2))
    print(f"\nEvaluated {len(candidates)} ordered policies; full ranking and 95% CIs saved to {args.output}")


if __name__ == "__main__":
    main()
