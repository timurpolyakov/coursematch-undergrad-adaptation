# Cornell Enrollment Policy Simulator (Built with Codex)

This project compares a synthetic senior-first registration process with a
price-and-priority market. It uses a saved Fall 2025 Cornell course catalog and
16,138 synthetic student profiles; it is a policy prototype, not a prediction
of individual enrollment behavior.

## Scope

This repository is designed to explore how alternative allocation rules behave
under stated modeling assumptions. It can compare simulated outcomes, identify
tradeoffs between class years, and produce inspectable per-student allocation
reports. It is not an enrollment system, a forecasting tool, or evidence that
one policy should be deployed at Cornell.

In particular, the project does **not** use private student data, actual course
requests, degree audits, or official enrollment decisions. The saved catalog
and aggregate program distribution provide context; preferences, student
eligibility, and most constraints are synthetic.

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

## Limitations

### Data and behavioral assumptions

- Every course currently has a fallback capacity of 45 because the public API
  response used by the scraper does not expose usable enrollment caps.
- Profiles represent broad program categories, not declared majors, colleges,
  transcripts, or degree audits. The course-to-program mappings are manual
  assumptions in `profile_builder.py`.
- Utilities are randomly drawn synthetic preference scores. They do not measure
  student demand, course importance, willingness to pay, or academic outcomes.
- The class-year budgets and price modifiers are policy parameters, not values
  estimated from real behavior.

### Scheduling and eligibility assumptions

- A course is allocated at the course level, not at a particular lecture,
  discussion, lab, studio, or recitation section.
- The model does not enforce meeting-time conflicts, prerequisites,
  co-requisites, college requirements, cross-listings, instructor consent,
  waitlists, or reserved-seat rules.
- A course consideration set is a synthetic shortlist. A student who exhausts
  that list can remain below a viable full schedule.

### Allocation and evaluation assumptions

- The market uses a heuristic price-adjustment loop and priority rules; it does
  not prove a competitive-equilibrium, welfare-optimal, or strategy-proof
  allocation.
- Senior graduation protection can improve access to one top upper-level major
  course while still reducing a senior's total utility. The charts should be
  read as tradeoffs, not a single fairness score.
- One simulation seed is illustrative only. Policy conclusions require paired
  replications, uncertainty intervals, and holdout scenarios.
- Large error bars in raw utility charts describe differences among students;
  they do not by themselves show whether the policy difference is meaningful.

## Interpreting policy comparisons

The two policies can produce nearly identical charts when there is more modeled
course capacity than demand for the same courses. In that situation, price
modifiers and budgets rarely decide an allocation. To test whether a policy
meaningfully changes outcomes, use stress scenarios that introduce one or more
of these conditions:

- More juniors and seniors competing for the same upper-level major courses.
- Reduced capacity for those contested upper-level courses.
- A smaller set of offered courses, so that demand is concentrated rather than
  spread across the full catalog.

These are experimental conditions for sensitivity testing, not claims about
actual Cornell enrollment. Compare policy deltas alongside uncertainty; wide
student-level variation can hide a very small average policy effect.

## Improvement roadmap

1. **Use better constraint data.** Add authorized section capacities,
   reservation rules, meeting patterns, prerequisites, and linked components.
   Preserve source and refresh date for every imported field.
2. **Model feasible schedules.** Allocate specific lecture/discussion/lab
   combinations, reject time conflicts, and include college and degree-progress
   requirements where reliable data is available.
3. **Calibrate synthetic behavior.** Replace arbitrary utility, budget, and
   modifier values with documented scenarios or aggregate evidence. Keep a
   baseline scenario and clearly label all assumptions.
4. **Make experiments discriminating.** Run normal-demand and bottleneck
   scenarios, use common random seeds across policies, and report paired
   deltas, confidence intervals, and worst-cohort outcomes.
5. **Define a policy objective before tuning.** Specify senior-access floors,
   junior major-progress goals, utility/credit objectives, and fairness
   guardrails before selecting price modifiers.
6. **Strengthen validation.** Add automated tests for capacity, credits,
   budgets, priority guarantees, and report schema; then validate results on
   held-out seeds and scenarios.

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
