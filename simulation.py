"""Probabilistic comparison of Cornell enrollment policies.

Run ``python3 simulation.py`` after running ``python3 scrapper.py``.  Each
trial creates a new population and preference draw, then compares the current
senior-first process with a price-and-priority market allocation.
"""

import argparse
import json
import random
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Dict, Iterable, List, Set

from course import Course

YEAR_ORDER = {"Senior": 4, "Junior": 3, "Sophomore": 2, "Freshman": 1}
YEARS = list(YEAR_ORDER)


@dataclass
class Student:
    name: str
    major: str
    year: str
    utilities: Dict[str, float]
    major_subjects: Set[str] | None = None
    target_credits: float = 15.0
    budget: float = 100.0
    major_credit_minimum: float = 0.0

    def price_modifier(self, course: Course) -> float:
        is_major_course = course.department in (self.major_subjects or {self.major})
        if is_major_course:
            if self.year == "Senior":
                return 0.50 if course.level >= 3000 else 0.70
            return 0.70
        if self.year == "Senior" and 1000 <= course.level < 2000:
            return 2.50
        return 1.00


def load_courses(path: str | Path) -> Dict[str, Course]:
    with Path(path).open(encoding="utf-8") as file:
        return {name: Course.from_dict(data) for name, data in json.load(file).items()}


def load_profiles(path: str | Path) -> list[dict]:
    with Path(path).open(encoding="utf-8") as file:
        return json.load(file)


def students_from_profiles(profiles: List[dict], courses: Dict[str, Course], rng: random.Random, count: int = 0) -> List[Student]:
    """Turn saved synthetic profiles into one stochastic preference draw."""
    selected = profiles if count <= 0 or count >= len(profiles) else rng.sample(profiles, count)
    students = []
    for profile in selected:
        major_subjects = set(profile["major_subjects"])
        utilities = {}
        for name in profile["considered_courses"]:
            course = courses.get(name)
            if not course:
                continue
            major_bonus = 35 if course.department in major_subjects else 0
            senior_need = 20 if profile["year"] == "Senior" and course.level >= 3000 else 0
            first_year_fit = 15 if profile["year"] == "Freshman" and course.level < 2000 else 0
            utilities[name] = round(rng.uniform(35, 85) + major_bonus + senior_need + first_year_fit, 2)
        students.append(Student(
            name=profile["id"], major=profile["program_category"], year=profile["year"],
            utilities=utilities, major_subjects=major_subjects,
            target_credits=profile["target_credits"], major_credit_minimum=profile["major_credit_minimum"],
        ))
    return students


def choose_offerings(catalog: Dict[str, Course], count: int, rng: random.Random) -> Dict[str, Course]:
    """Choose a manageable, mixed-level term from the saved Cornell catalog."""
    candidates = [course for course in catalog.values() if 1000 <= course.level < 5000]
    by_department: Dict[str, List[Course]] = defaultdict(list)
    for course in candidates:
        by_department[course.department].append(course)

    chosen: List[Course] = []
    # Cover as many departments as the requested term size permits.
    departments = list(by_department.values())
    rng.shuffle(departments)
    for department_courses in departments[:count]:
        chosen.append(rng.choice(department_courses))
    remaining = [course for course in candidates if course not in chosen]
    chosen.extend(rng.sample(remaining, min(count - len(chosen), len(remaining))))
    return {course.name: course for course in chosen}


def generate_students(courses: Dict[str, Course], count: int, rng: random.Random) -> List[Student]:
    """Generate a stochastic population with major-focused and elective demand."""
    departments = sorted({course.department for course in courses.values()})
    by_department: Dict[str, List[Course]] = defaultdict(list)
    for course in courses.values():
        by_department[course.department].append(course)

    students = []
    for index in range(count):
        major = rng.choice(departments)
        year = rng.choice(YEARS)
        major_courses = by_department[major]
        # Students consider mostly major courses, plus electives.  The draw is
        # deliberately random so multiple trials represent different terms.
        options = rng.sample(major_courses, min(4, len(major_courses)))
        electives = [course for course in courses.values() if course.department != major]
        options += rng.sample(electives, min(3, len(electives)))

        utilities = {}
        for course in options:
            major_bonus = 30 if course.department == major else 0
            senior_need = 20 if year == "Senior" and course.level >= 3000 else 0
            level_fit = 15 if course.level < 2000 and year == "Freshman" else 0
            utilities[course.name] = round(rng.uniform(35, 85) + major_bonus + senior_need + level_fit, 2)
        students.append(Student(f"Student_{index:04d}", major, year, utilities))
    return students


def valid_bundle(student: Student, bundle: Iterable[str], courses: Dict[str, Course]) -> bool:
    return sum(courses[name].credits for name in bundle) <= student.target_credits


def senior_first_allocation(students: List[Student], courses: Dict[str, Course], rng: random.Random) -> Dict[str, Set[str]]:
    """Baseline: seniors, juniors, sophomores, then freshmen pick in random order."""
    remaining = {name: course.capacity for name, course in courses.items()}
    allocations: Dict[str, Set[str]] = defaultdict(set)
    for year in YEARS:
        cohort = [student for student in students if student.year == year]
        rng.shuffle(cohort)  # registration time is probabilistic within a class year
        for student in cohort:
            credits = 0.0
            for name in sorted(student.utilities, key=student.utilities.get, reverse=True):
                course = courses[name]
                if remaining[name] and credits + course.credits <= student.target_credits:
                    allocations[student.name].add(name)
                    remaining[name] -= 1
                    credits += course.credits
    return allocations


def optimal_market_bundle(student: Student, courses: Dict[str, Course], prices: Dict[str, float]) -> Set[str]:
    """Choose a full feasible schedule at current prices for demand discovery."""
    score = lambda name: student.utilities[name] - student.price_modifier(courses[name]) * prices[name]
    major_subjects = student.major_subjects or {student.major}
    major_ranked = sorted((name for name in student.utilities if courses[name].department in major_subjects), key=score, reverse=True)
    ranked = sorted(student.utilities, key=score, reverse=True)
    bundle: Set[str] = set()
    credits = major_credits = 0.0
    # Protect the student's major-progress floor, while letting prices decide
    # which of the relevant courses are most affordable.
    for name in major_ranked + ranked:
        if name in bundle:
            continue
        course = courses[name]
        is_major = course.department in (student.major_subjects or {student.major})
        if credits + course.credits > student.target_credits:
            continue
        if not is_major and major_credits < student.major_credit_minimum:
            continue
        bundle.add(name)
        credits += course.credits
        major_credits += course.credits if is_major else 0
    return bundle


def market_allocation(students: List[Student], courses: Dict[str, Course]) -> Dict[str, Set[str]]:
    """Price discovery plus capacity-aware fallback to each student's next choice."""
    prices = {name: 10.0 for name in courses}
    demand_bundles = {}
    for _ in range(100):
        demanded = defaultdict(int)
        for student in students:
            bundle = optimal_market_bundle(student, courses, prices)
            demand_bundles[student.name] = bundle
            for name in bundle:
                demanded[name] += 1
        maximum_change = 0.0
        for name, course in courses.items():
            old_price = prices[name]
            # Under-subscribed offered courses become cheaper; contested courses
            # become dearer, but neither is ever removed from consideration.
            prices[name] = max(0.25, old_price + 0.04 * (demanded[name] - course.capacity))
            maximum_change = max(maximum_change, abs(prices[name] - old_price))
        if maximum_change < 0.01:
            break

    # First, distribute major-progress seats fairly in rounds. No student can
    # receive a second major course while another comparable student still has
    # no major course. This prevents the architecture failure where a junior
    # lost every ARCH seat to peers with several ARCH allocations.
    remaining = {name: course.capacity for name, course in courses.items()}
    allocations: Dict[str, Set[str]] = defaultdict(set)
    credits = defaultdict(float)
    major_credits = defaultdict(float)
    # Honor the first lexicographic rule before broad major-course fairness:
    # reserve each senior's top graduation-relevant course where capacity allows.
    senior_needs = []
    for student in students:
        if student.year != "Senior":
            continue
        major_subjects = student.major_subjects or {student.major}
        choices = [name for name in student.utilities if courses[name].department in major_subjects and courses[name].level >= 3000]
        if choices:
            choice = max(choices, key=student.utilities.get)
            senior_needs.append((student.utilities[choice], student, choice))
    for _, student, name in sorted(senior_needs, reverse=True, key=lambda entry: entry[0]):
        course = courses[name]
        if remaining[name] and course.credits <= student.target_credits:
            allocations[student.name].add(name)
            remaining[name] -= 1
            credits[student.name] += course.credits
            major_credits[student.name] += course.credits
    ordered_students = sorted(students, key=lambda student: YEAR_ORDER[student.year], reverse=True)
    progress_possible = True
    while progress_possible:
        progress_possible = False
        for student in ordered_students:
            if major_credits[student.name] >= student.major_credit_minimum:
                continue
            major_subjects = student.major_subjects or {student.major}
            candidates = [
                name for name in student.utilities
                if name not in allocations[student.name]
                and courses[name].department in major_subjects
                and remaining[name] > 0
                and credits[student.name] + courses[name].credits <= student.target_credits
            ]
            if not candidates:
                continue
            best = max(candidates, key=lambda name: student.utilities[name] - student.price_modifier(courses[name]) * prices[name])
            allocations[student.name].add(best)
            remaining[best] -= 1
            credits[student.name] += courses[best].credits
            major_credits[student.name] += courses[best].credits
            progress_possible = True

    # A rejected request must fall through to the student's next relevant
    # preference. Every considered course stays available as a fallback, while
    # its price-adjusted score determines its priority at that course.
    claims = []
    top_graduation_need = {}
    for student in students:
        required = [
            name for name in student.utilities
            if student.year == "Senior"
            and courses[name].department in (student.major_subjects or {student.major})
            and courses[name].level >= 3000
        ]
        if required:
            top_graduation_need[student.name] = max(required, key=student.utilities.get)
    for student in students:
        for name, utility in student.utilities.items():
            effective_price = student.price_modifier(courses[name]) * prices[name]
            score = utility - effective_price
            # The senior-major upper-level rule is a policy guarantee, not a
            # soft preference that can disappear because of a random draw.
            graduation_priority = int(
                top_graduation_need.get(student.name) == name
            )
            major_need = int(courses[name].department in (student.major_subjects or {student.major}))
            claims.append((graduation_priority, major_need, score, student, name))
    claims.sort(key=lambda claim: (claim[0], claim[1], claim[2]), reverse=True)

    for _, _, _, student, name in claims:
        course = courses[name]
        is_major = course.department in (student.major_subjects or {student.major})
        # Let electives fill a schedule too; the claim order has already given
        # major requirements and graduation courses first access.
        if name not in allocations[student.name] and remaining[name] and credits[student.name] + course.credits <= student.target_credits:
            allocations[student.name].add(name)
            remaining[name] -= 1
            credits[student.name] += course.credits
            major_credits[student.name] += course.credits if is_major else 0
    return allocations


def metrics(students: List[Student], courses: Dict[str, Course], allocations: Dict[str, Set[str]]) -> Dict[str, float]:
    total_utility = total_credits = major_course_count = 0.0
    filled_seats = sum(len(bundle) for bundle in allocations.values())
    senior_major_choices = senior_major_wins = 0
    for student in students:
        bundle = allocations[student.name]
        total_utility += sum(student.utilities[name] for name in bundle)
        total_credits += sum(courses[name].credits for name in bundle)
        major_course_count += sum(courses[name].department in (student.major_subjects or {student.major}) for name in bundle)
        required_options = [
            name for name in student.utilities
            if student.year == "Senior"
            and courses[name].department in (student.major_subjects or {student.major})
            and courses[name].level >= 3000
        ]
        # One student generally needs one next graduation-relevant course, not
        # every course they happen to prefer. Measure access to their top one.
        if required_options:
            top_requirement = max(required_options, key=student.utilities.get)
            senior_major_choices += 1
            senior_major_wins += top_requirement in bundle
    return {
        "average utility": total_utility / len(students),
        "average credits": total_credits / len(students),
        "major-course share": major_course_count / max(1, filled_seats),
        "senior major-course access": senior_major_wins / max(1, senior_major_choices),
    }


def student_comparison(students: List[Student], courses: Dict[str, Course], senior_first: Dict[str, Set[str]], market: Dict[str, Set[str]]) -> list[dict]:
    """Return an inspectable, preference-to-allocation record for every student."""
    report = []
    for student in students:
        preferences = sorted(student.utilities, key=student.utilities.get, reverse=True)
        baseline = sorted(senior_first[student.name])
        priced = sorted(market[student.name])
        baseline_utility = sum(student.utilities[name] for name in baseline)
        market_utility = sum(student.utilities[name] for name in priced)
        report.append({
            "student_id": student.name,
            "year": student.year,
            "program_category": student.major,
            "target_credits": student.target_credits,
            "ranked_preferences": [{"course": name, "utility": student.utilities[name]} for name in preferences],
            "senior_first": {
                "courses": baseline,
                "credits": sum(courses[name].credits for name in baseline),
                "utility": round(baseline_utility, 2),
            },
            "market": {
                "courses": priced,
                "credits": sum(courses[name].credits for name in priced),
                "utility": round(market_utility, 2),
            },
            "market_minus_senior_first_utility": round(market_utility - baseline_utility, 2),
        })
    return sorted(report, key=lambda entry: entry["market_minus_senior_first_utility"], reverse=True)


def print_student_extremes(report: list[dict], count: int) -> None:
    if not count:
        return
    print("\nStudents helped most by market allocation:")
    for item in report[:count]:
        print(f"  {item['student_id']}: {item['market_minus_senior_first_utility']:+.2f} utility | "
              f"senior-first {item['senior_first']['credits']}cr, market {item['market']['credits']}cr")
    print("Students helped least by market allocation:")
    for item in report[-count:][::-1]:
        print(f"  {item['student_id']}: {item['market_minus_senior_first_utility']:+.2f} utility | "
              f"senior-first {item['senior_first']['credits']}cr, market {item['market']['credits']}cr")


def compare(catalog: Dict[str, Course], students_count: int, offerings_count: int, trials: int, seed: int, profiles: List[dict] | None = None,
            report_path: str | None = None, show_students: int = 0) -> None:
    all_results: Dict[str, List[Dict[str, float]]] = defaultdict(list)
    detailed_report = None
    for trial in range(trials):
        rng = random.Random(seed + trial)
        courses = catalog if profiles else choose_offerings(catalog, offerings_count, rng)
        students = students_from_profiles(profiles, courses, rng, students_count) if profiles else generate_students(courses, students_count, rng)
        baseline_allocation = senior_first_allocation(students, courses, rng)
        market_result = market_allocation(students, courses)
        all_results["Senior-first registration"].append(metrics(students, courses, baseline_allocation))
        all_results["Price-and-priority market"].append(metrics(students, courses, market_result))
        if trial == 0 and (report_path or show_students):
            detailed_report = student_comparison(students, courses, baseline_allocation, market_result)

    actual_count = len(profiles) if profiles and students_count <= 0 else students_count
    print(f"\nProbabilistic enrollment comparison ({trials} trials; {actual_count} students per trial)")
    print(f"{'Metric':<30} {'Senior-first':>15} {'Market':>15}")
    print("-" * 62)
    for metric_name in next(iter(all_results.values()))[0]:
        baseline = mean(result[metric_name] for result in all_results["Senior-first registration"])
        market = mean(result[metric_name] for result in all_results["Price-and-priority market"])
        suffix = "%" if "share" in metric_name or "access" in metric_name else ""
        multiplier = 100 if suffix else 1
        print(f"{metric_name:<30} {baseline * multiplier:>14.2f}{suffix:<1} {market * multiplier:>14.2f}{suffix:<1}")
    if detailed_report:
        print_student_extremes(detailed_report, show_students)
        if report_path:
            Path(report_path).write_text(json.dumps(detailed_report, indent=2), encoding="utf-8")
            print(f"\nSaved per-student comparison to {report_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compare two probabilistic Cornell enrollment policies.")
    parser.add_argument("--catalog", default="cornell_courses_FA25_all.json")
    parser.add_argument("--profiles", default="cornell_fa25_synthetic_profiles.json")
    parser.add_argument("--students", type=int, default=0, help="Profiles to sample; 0 uses all saved profiles.")
    parser.add_argument("--offerings", type=int, default=45)
    parser.add_argument("--trials", type=int, default=20)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--report", help="Write first-trial per-student comparison JSON to this path.")
    parser.add_argument("--show-students", type=int, default=0, help="Print this many best and worst market outcomes.")
    args = parser.parse_args()
    profile_data = load_profiles(args.profiles) if args.profiles else None
    compare(load_courses(args.catalog), args.students, args.offerings, args.trials, args.seed, profile_data,
            args.report, args.show_students)
