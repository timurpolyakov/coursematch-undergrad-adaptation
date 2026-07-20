# Cornell Enrollment Policy Simulator

This project compares two synthetic Fall 2025 enrollment policies using the
saved course catalog and 16,138 generated student profiles. It is a policy
prototype, not a reconstruction or prediction of real individual enrollment.

## Active allocation constraints

The market allocation currently applies these rules in order:

1. **Course capacity:** no course receives more students than its recorded
   capacity. When the public historical roster lacks a capacity, the scraper
   currently uses a fallback of 45 seats.
2. **Credit ceiling:** a student cannot receive more credits than their target,
   drawn from 12 to 20 credits with a population mode of 16.
3. **Major-progress floor:** each profile targets at least 75% major-related
   credits. The allocator distributes major courses in rounds: a student gets
   their next available major course before another comparable student gets an
   additional one. This repeats until the floor is met or no relevant seat is
   available.
4. **Class-year priority:** within each major-progress round, seniors are
   considered before juniors, then sophomores and freshmen.
5. **Senior graduation protection:** a senior's highest-utility upper-level
   major course receives priority in contested course allocation.
6. **Dynamic prices:** prices rise for excess demand and fall for
   under-enrollment. A student's effective price is adjusted by their major
   and class-year modifier.
7. **Preference fallback:** after protected major-progress allocation, a
   rejected student can still receive lower-ranked courses from their saved
   consideration set. Claims are ranked by utility minus effective price.

## Important limitations

- Profiles use supplied broad program-category totals, not private individual
  major, college, transcript, or preference records.
- Course-to-program mappings and fallback subjects are explicit modeling
  assumptions in `student_profiles.py`.
- Prerequisites, time conflicts, linked discussion/lab sections, college core
  requirements, PE, cross-listings, waitlists, and actual historical caps are
  not yet enforced.
- A student can remain below 12 credits if the model has no relevant available
  course in their consideration set. This is reported as an unmet outcome, not
  treated as a successful schedule.

## Running

```bash
python3 gui.py
python3 student_viewer.py
```

For a reproducible command-line run with a detailed report:

```bash
python3 simulation.py --trials 1 --seed 2025 --report student_allocation_comparison.json
```
