# Cornell Enrollment Policy Simulator (Built with Codex)

This project compares a synthetic senior-first registration process with a
price-and-priority market. It uses a saved Fall 2025 Cornell course catalog and
16,138 synthetic student profiles; it is a policy prototype, not a prediction
of individual enrollment behavior.

## What the model enforces

- Course capacity. The public roster API did not provide usable enrollment
  caps for this catalog, so every course currently uses the documented fallback
  capacity of 45 seats.
- A student-specific credit ceiling of 12–20 credits.
- A major-progress floor: profiles target at least 75% major-related credits.
- Class-year priority during major-progress allocation.
- Senior protection for each senior's highest-utility upper-level major course.
- Dynamic prices, with upper-level major-course modifiers of 0.35 for seniors,
  0.45 for juniors, and 0.70 for sophomores and freshmen.
- Binding market budgets: 125 for seniors, 115 for juniors, and 100 for
  sophomores and freshmen.
- Preference fallback when a higher-ranked course is unavailable.

Time conflicts, prerequisites, linked discussion/lab sections, college
requirements, cross-listings, waitlists, and actual section caps are not yet
modeled.

## Project layout

| File | Purpose |
| --- | --- |
| `course_model.py` | Shared `Course` data model. |
| `course_catalog.py` | Downloads and saves course catalog data. |
| `profile_builder.py` | Builds synthetic student profiles from aggregate distributions. |
| `enrollment_simulator.py` | Runs the senior-first and market allocation comparison. |
| `weight_tuner.py` | Evaluates upper-level major-course modifier policies. |
| `simulator_app.py` | Desktop controls for a simulation run. |
| `allocation_viewer.py` | Desktop viewer for a generated allocation report. |

The three `cornell_*.json` files are the model inputs: catalog, program
distribution, and synthetic profiles. Generated reports and Python bytecode are
ignored by Git.

## Run the simulator

```bash
python3 enrollment_simulator.py --students 1000 --trials 3 --seed 2026
```

To write a per-student allocation report:

```bash
python3 enrollment_simulator.py --students 1000 --trials 1 --seed 2026 \
  --report allocation_report.json
python3 allocation_viewer.py
```

To use the desktop interface:

```bash
python3 simulator_app.py
```

## Tune modifier weights

```bash
python3 weight_tuner.py --students 1000 --trials 5 \
  --output weight_tuning_results.json
```

Each candidate receives the same seed-derived preference draws, and the output
includes trial-level 95% confidence intervals. A policy should only be adopted
when its benefit is larger than that uncertainty.

## Refresh data

Refresh a subset of roster subjects:

```bash
python3 course_catalog.py --term FA25 --subjects CS ORIE MATH
```

Rebuild profiles after changing catalog or profile assumptions:

```bash
python3 profile_builder.py --seed 2025
```
