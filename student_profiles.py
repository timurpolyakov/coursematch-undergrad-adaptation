"""Create reproducible, synthetic Fall 2025 student profiles.

The supplied distribution is by broad program category, not individual major or
college.  The mappings below are explicit modeling assumptions and can be
edited as better aggregate data becomes available.
"""

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path


YEARS = ("Freshman", "Sophomore", "Junior", "Senior")

# Broad program category -> roster subjects that plausibly provide its major
# requirements.  These are course-selection assumptions, not Cornell records
# of each student's declared major or college.
SUBJECT_MAP = {
    "Computer & Information Sciences": ("CS", "INFO", "IS", "BTRY"),
    "Engineering": ("AEP", "BEE", "BME", "CHEME", "CEE", "ECE", "MAE", "MSE", "ORIE"),
    "Mathematics & Statistics": ("MATH", "STSCI", "ORIE"),
    "Biological & Biomedical Sciences": ("BIOG", "BIOMG", "BIOEE", "BIOMS"),
    "Agriculture, Agriculture Operations & Related Sciences": ("AGSCI", "ANSC", "CALS", "HORT"),
    "Natural Resources & Conservation": ("NRES", "EAS", "NTRES"),
    "Nutritional Sciences": ("NS", "HADM", "HNF"),
    "Physical Sciences": ("CHEM", "PHYS", "ASTRO"),
    "Health Professions & Related Clinical Sciences": ("HADM", "ILR", "PUBPOL"),
    "Area, Ethnic, Cultural & Gender Studies": ("AAS", "AMST", "ASRC", "FGSS"),
    "Communication, Journalism & Related Programs": ("COMM", "ILR", "PAM"),
    "Family & Consumer Sciences/Human Sciences": ("HD", "HDFS", "DEA"),
    "Psychology": ("PSYCH",),
    "Public Administration & Social Service Professions": ("PAM", "ILR", "PUBPOL"),
    "Social Sciences": ("ECON", "GOVT", "SOC", "ANTHR"),
    "Business, Management & Marketing": ("AEM", "HADM", "PAM"),
    "History": ("HIST",),
    "Architecture & Related Programs": ("ARCH", "AAP"),
    "Foreign Languages, Literatures & Linguistics": ("LING", "FREN", "SPAN", "CHIN", "GERST"),
    "English Language & Literature/Letters": ("ENGL", "CREA"),
    "Liberal Arts & Sciences/General Studies & Humanities": ("AS", "HIST", "PHIL", "ENGL"),
    "Philosophy & Religious Studies": ("PHIL", "RELST"),
    "Visual & Performing Arts": ("ART", "MUSIC", "THEAT", "PM"),
    "Multi/Interdisciplinary": ("CIS", "ENVS", "STS"),
    "Unknown": ("AS",),
}

# Plausible non-major choices for each broad academic area.  This prevents an
# arbitrary open seat from becoming a student's only fallback schedule option.
RELATED_SUBJECTS = {
    "Computer & Information Sciences": ("MATH", "STSCI", "ORIE", "ECON", "PHIL", "INFO", "IS"),
    "Engineering": ("MATH", "PHYS", "CHEM", "CS", "ORIE", "STSCI"),
    "Mathematics & Statistics": ("CS", "STSCI", "ORIE", "ECON", "PHYS"),
    "Biological & Biomedical Sciences": ("CHEM", "PHYS", "MATH", "STSCI", "NS"),
    "Social Sciences": ("ECON", "GOVT", "SOC", "PSYCH", "STSCI"),
    "Business, Management & Marketing": ("ECON", "AEM", "HADM", "PAM", "STSCI"),
}
NON_GENERAL_FALLBACKS = {"TIBET", "AKKAD", "ARAB", "ASL", "HEBRW", "SANSKR", "TURK", "YIDD"}


def course_level_ok(level: int, year: str) -> bool:
    ranges = {"Freshman": (1000, 2999), "Sophomore": (1000, 3999), "Junior": (2000, 4999), "Senior": (2000, 9999)}
    low, high = ranges[year]
    return low <= level <= high


def build_profiles(distribution_path: str, catalog_path: str, seed: int) -> list[dict]:
    rng = random.Random(seed)
    distribution = json.loads(Path(distribution_path).read_text())["groups"]
    catalog = json.loads(Path(catalog_path).read_text())
    by_subject = defaultdict(list)
    all_courses = list(catalog.values())
    for course in all_courses:
        if 1000 <= course["level"] < 5000:
            by_subject[course["department"]].append(course)

    eligible = {
        year: [course for course in all_courses if 1000 <= course["level"] < 5000 and course_level_ok(course["level"], year)]
        for year in YEARS
    }

    profiles = []
    student_number = 1
    for _, categories in distribution.items():
        for raw_category, count in categories.items():
            category = raw_category.split(" ", 1)[1] if raw_category[:2].isdigit() else raw_category
            subjects = SUBJECT_MAP.get(category, ("AS",))
            related_subjects = RELATED_SUBJECTS.get(category, ("ECON", "MATH", "PHIL", "HIST", "ENGL"))
            major_by_year = {
                year: [course for subject in subjects for course in by_subject[subject] if course_level_ok(course["level"], year)]
                for year in YEARS
            }
            elective_by_year = {}
            for year in YEARS:
                pool = major_by_year[year] or eligible[year]
                pool_names = {course["name"] for course in pool}
                elective_by_year[year] = [course for course in eligible[year] if course["name"] not in pool_names]
            for index in range(count):
                year = YEARS[index % 4]  # equal class-year representation per category
                major_pool = major_by_year[year]
                if not major_pool:
                    major_pool = eligible[year]
                related_pool = [course for course in elective_by_year[year] if course["department"] in related_subjects]
                broad_pool = [course for course in elective_by_year[year] if course["department"] not in NON_GENERAL_FALLBACKS]
                # Most electives are adjacent to the program; broader Cornell
                # electives provide enough realistic fallbacks to reach 12–20 credits.
                elective_pool = related_pool + [course for course in broad_pool if course not in related_pool]
                target = round(rng.triangular(12, 20, 16))
                # A student needs substantial fallbacks: several sections can
                # fill, and 1- or 2-credit offerings should not strand a
                # 16-credit schedule. Keep sampling until the consideration
                # set contains at least target + 8 possible credits.
                major_options = rng.sample(major_pool, min(12, len(major_pool)))
                elective_options = rng.sample(elective_pool, min(10, len(elective_pool)))
                options = major_options + elective_options
                remaining = [course for course in elective_pool if course not in options]
                while sum(course["credits"] for course in options) < target + 8 and remaining:
                    course = remaining.pop(rng.randrange(len(remaining)))
                    options.append(course)
                major_options = [course for course in options if course["department"] in subjects]
                elective_options = [course for course in options if course["department"] not in subjects]
                profiles.append({
                    "id": f"FA25_{student_number:05d}",
                    "program_category": category,
                    "major_subjects": list(subjects),
                    "year": year,
                    "target_credits": target,
                    "major_credit_minimum": round(target * 0.75, 2),
                    "considered_courses": [course["name"] for course in major_options + elective_options],
                })
                student_number += 1
    return profiles


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--distribution", default="cornell_fa25_program_distribution.json")
    parser.add_argument("--catalog", default="cornell_courses_FA25_all.json")
    parser.add_argument("--output", default="cornell_fa25_synthetic_profiles.json")
    parser.add_argument("--seed", type=int, default=2025)
    args = parser.parse_args()
    profiles = build_profiles(args.distribution, args.catalog, args.seed)
    Path(args.output).write_text(json.dumps(profiles, indent=2), encoding="utf-8")
    print(f"Saved {len(profiles)} synthetic profiles to {args.output}")
