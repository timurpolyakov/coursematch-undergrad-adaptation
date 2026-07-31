import time
import json
import argparse
from pathlib import Path
from typing import Dict, List
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen
from course_model import Course


def fetch_cornell_courses(roster: str, subjects: List[str]) -> Dict[str, Course]:
    """
    Connects to the Cornell Class Roster API, respects rate limits,
    and dynamically switches parsing logic based on standard (FA25+) or legacy rosters.
    """
    base_url = "https://classes.cornell.edu/api/2.0/search/classes.json"
    scraped_courses: Dict[str, Course] = {}

    # Determine if we are querying standard (FA25 and beyond) or legacy data
    is_standard = False
    try:
        term = roster[:2].upper()
        year = int(roster[2:])
        # Standard rules apply to Fall 2025 (FA25) and later
        if year > 25 or (year == 25 and term in ["FA", "SU"]):
            is_standard = True
    except Exception:
        # Fallback to standard if formatting check fails
        is_standard = True

    print(f"=== Initiating Cornell Roster Scrape for Term: {roster} ===")
    print(f"API Target Mode: {'[Standard Catalog Source (FA25+)]' if is_standard else '[Legacy Catalog Source (Pre-FA25)]'}")
    
    for subject in subjects:
        print(f"Fetching subject '{subject}' from Cornell API...")
        params = {
            "roster": roster,
            "subject": subject
        }
        
        try:
            request_url = f"{base_url}?{urlencode(params)}"
            with urlopen(request_url, timeout=30) as response:
                data = json.load(response)
            classes_list = data.get("data", {}).get("classes", [])
            print(f"  Successfully retrieved {len(classes_list)} course records for {subject}.")
            
            for item in classes_list:
                subj = item.get("subject")
                catalog_num_str = item.get("catalogNbr", "1000")
                course_id = f"{subj}_{catalog_num_str}"
                
                # Extract level as integer (e.g. 3110 or 1110)
                try:
                    level = int(catalog_num_str)
                except ValueError:
                    import re
                    numeric_part = re.findall(r'\d+', catalog_num_str)
                    level = int(numeric_part[0]) if numeric_part else 1000

                # Extract prerequisites cleanly using standard or legacy keys
                prereqs = ""
                if is_standard:
                    # For Fall 2025 and beyond, legacy catalogPrereqCoreq is empty
                    prereqs = item.get("catalogPrereq", "")
                else:
                    # Prior to Fall 2025, prereqs and coreqs are joined here
                    prereqs = item.get("catalogPrereqCoreq", "")

                # Fallback safeguard in case API transitions overlap
                if not prereqs:
                    prereqs = item.get("catalogPrereqCoreq", "") or item.get("catalogPrereq", "")

                # Clean up extracted prerequisite strings
                prereqs = prereqs.strip() if prereqs else ""

                enroll_groups = item.get("enrollGroups", [])
                credits = 3
                capacity = 45
                
                if enroll_groups:
                    group = enroll_groups[0]
                    credits = float(group.get("unitsMin", 3))
                    class_sections = group.get("classSections", [])

                    
                    # We sum up the enrollment capacities of the LECTURE (LEC) sections
                    lec_capacities = [
                        sec.get("enrollCap", 0) 
                        for sec in class_sections 
                        if sec.get("ssrComponent") == "LEC"
                    ]
                    
                    if lec_capacities and all(isinstance(value, (int, float)) and value > 0 for value in lec_capacities):
                        capacity = sum(lec_capacities)
                    else:
                        sec_capacities = [sec.get("enrollCap", 0) for sec in class_sections]
                        valid_capacities = [value for value in sec_capacities if isinstance(value, (int, float)) and value > 0]
                        if valid_capacities:
                            capacity = max(valid_capacities)

                if capacity <= 0:
                    capacity = 45

                # Build our Course object and store it
                course_obj = Course(
                    name=course_id,
                    department=subj,
                    level=level,
                    capacity=capacity,
                    credits=credits,
                    prerequisites=prereqs,
                )
                scraped_courses[course_id] = course_obj
                
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as e:
            print(f"  [Error] Exception occurred while processing {subject}: {e}")
            
        # "API usage should be limited to no more than 1 request per second"
        time.sleep(1.0)
        
    print(f"\nScraping complete. Total active Course objects built: {len(scraped_courses)}")
    return scraped_courses


def fetch_subject_codes(roster: str) -> List[str]:
    """Retrieve the complete official subject list for a roster."""
    endpoint = "https://classes.cornell.edu/api/2.0/config/subjects.json"
    request_url = f"{endpoint}?{urlencode({'roster': roster})}"
    with urlopen(request_url, timeout=30) as response:
        payload = json.load(response)
    subjects = payload.get("data", {}).get("subjects", [])
    # The API has used both an object and a bare-code representation.
    return [item.get("value") if isinstance(item, dict) else item for item in subjects]


def save_courses(courses: Dict[str, Course], output_path: str | Path) -> Path:
    """Save a fetched catalog in a format the simulator can load directly."""
    path = Path(output_path)
    path.write_text(
        json.dumps({name: course.to_dict() for name, course in courses.items()}, indent=2),
        encoding="utf-8",
    )
    print(f"Saved {len(courses)} courses to {path.resolve()}")
    return path


def load_courses(path: str | Path) -> Dict[str, Course]:
    catalog_path = Path(path)
    if not catalog_path.exists():
        return {}
    with catalog_path.open(encoding="utf-8") as file:
        return {name: Course.from_dict(data) for name, data in json.load(file).items()}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Save Cornell Class Roster courses as JSON.")
    parser.add_argument("--term", default="FA25")
    parser.add_argument("--all-subjects", action="store_true", help="Fetch every subject in the official roster.")
    parser.add_argument("--subjects", nargs="+", default=["CS", "ORIE", "MATH"])
    parser.add_argument("--output")
    parser.add_argument("--offset", type=int, default=0, help="Subject offset; supports resumable full fetches.")
    parser.add_argument("--limit", type=int, help="Maximum subjects to fetch in this run.")
    args = parser.parse_args()

    subject_codes = fetch_subject_codes(args.term) if args.all_subjects else args.subjects
    if args.limit:
        subject_codes = subject_codes[args.offset:args.offset + args.limit]
    elif args.offset:
        subject_codes = subject_codes[args.offset:]
    print(f"Fetching {len(subject_codes)} subjects.")
    scraped_db = fetch_cornell_courses(args.term, subject_codes)
    output = args.output or f"cornell_courses_{args.term}{'_all' if args.all_subjects else ''}.json"
    existing = load_courses(output)
    existing.update(scraped_db)
    save_courses(existing, output)
