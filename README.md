# A1 — Nurse Rostering Problem

A constraint satisfaction and local search implementation for the **Nurse Rostering Problem (NRP)**, completed as Assignment 1 for an AI course.

---

## Problem Overview

The goal is to assign daily shifts to a set of nurses over a scheduling horizon such that:

- Hard constraints (staffing quotas, shift sequencing, surgical coverage, leave days, shift budget) are **always satisfied**
- Soft constraints (balanced distribution of Morning / Afternoon / Evening shifts per nurse) are **minimised** in Part B

Each nurse-day cell is assigned one of the following shift codes:

| Code | Meaning |
|------|---------|
| `M`  | Morning |
| `A`  | Afternoon |
| `E`  | Evening |
| `B`  | Surgery (morning + afternoon; surgical nurses on surgical days only) |
| `R`  | Rest |

---

## Repository Structure

```
A1-starter-code/
├── part_a.py                 # Part A — CSP backtracking solver
├── part_b.py                 # Part B — CSP + local search solver
├── verifier.py               # Checks any solution JSON against all hard constraints
├── visualizer.py             # ANSI colour terminal visualiser for a roster
├── solution.json             # Sample solution output (JSON)
├── A1-Intro-to-AI-Release.pdf  # Full assignment specification
└── sample_test_cases/
    ├── test1.csv
    ├── test2.csv
    └── test3.csv
```

---

## Input Format

Input is a single-row CSV file with the following columns:

| Column | Type | Description |
|--------|------|-------------|
| `N` | int | Total number of nurses |
| `D` | int | Number of days in the schedule |
| `N_s` | int | Number of surgical nurses (indices 0 … N_s-1) |
| `N_g` | int | Number of general nurses (indices N_s … N-1) |
| `m` | int | Exact nurses required on Morning bucket each day |
| `a` | int | Exact nurses required on Afternoon bucket each day |
| `e` | int | Exact nurses required on Evening bucket each day |
| `T` | float | Time budget in seconds |
| `days` | string | Length-D string of `G` (general) / `S` (surgical) day types |
| `K` | int | Maximum shift-units per nurse (`B` costs 2, others cost 1) |
| `leaves` | string | Length N×D string; `L` marks a mandatory rest day, `W` marks a working-eligible day |

**Example (`test1.csv`):**
```
N,D,N_s,N_g,m,a,e,T,days,K,leaves
18,9,9,9,1,3,3,100,SSSGGSGSG,6,WWWWWWWWWWLWWWW...
```

---

## Output Format

A JSON object with one key per nurse-day cell:

```json
{
  "N0_0": "R",
  "N0_1": "M",
  "N1_0": "A",
  ...
}
```

Key format: `N{nurse_index}_{day_index}` (both zero-based).  
An empty object `{}` is written when no valid solution is found.

---

## Hard Constraints

| ID | Rule |
|----|------|
| H1 | Every cell has a valid shift code; only surgical nurses may hold `B` |
| H2 | No two consecutive Morning shifts (`M` or `B`) |
| H3 | No Morning shift immediately after an Evening shift |
| H4 | Each day must have exactly `m` morning-bucket, `a` afternoon-bucket, and `e` evening-bucket nurses |
| H5 | No nurse may work more than 5 consecutive days |
| H6 | After a `B` shift, the nurse cannot work `M` or `A` the next day |
| H7 | Surgical days must have at least one `B` shift assigned |
| H8 | Each nurse's total shift units may not exceed `K` |
| H9 | Nurses must rest (`R`) on their designated leave days |

---

## Approach

### Part A — Backtracking CSP (`part_a.py`)

Pure constraint satisfaction with the following techniques:

- **MRV (Minimum Remaining Values)** heuristic — at each day, the nurse with the fewest legal shifts is assigned first
- **Forward checking** — prunes branches where a nurse would have no legal options the next day
- **Quota feasibility pruning** — checks at each step whether remaining unassigned nurses can still satisfy daily staffing quotas
- **Next-day lookahead** — verifies that tomorrow's quotas are reachable before committing to today's assignments

### Part B — CSP + Local Search (`part_b.py`)

Two-phase approach:

1. **Phase 1 — Backtracking construction** (same as Part A, extended with a shift-balance ordering heuristic)  
   - `balance_order()` prefers shifts the nurse has had least often, seeding the roster with a naturally balanced initial solution

2. **Phase 2 — Stochastic hill climbing** (`local_search()`)  
   - Move: randomly select a day and two nurses, then swap their shifts if both placements remain hard-constraint-legal  
   - Accept: strict improvements or lateral (zero-delta) moves up to `MAX_SIDEWAYS_MOVES = 100` consecutive sideways steps  
   - Objective: minimise `Σ_i [(M_i − A_i)² + (A_i − E_i)² + (M_i − E_i)²]` over all nurses  
   - Best-seen roster is restored at the end

---

## Usage

### Run Part A (hard constraints only)
```bash
python part_a.py <input.csv> <output.json>
```

### Run Part B (hard + soft constraints)
```bash
python part_b.py <input.csv> <output.json>
```

### Verify a solution
```bash
python verifier.py <input.csv> <output.json>
```

### Visualise a roster (terminal)
```bash
python visualizer.py <input.csv> <output.json>
```

---

## Requirements

- Python 3.8+
- No external dependencies — standard library only (`csv`, `json`, `random`, `sys`)

---

## Team

| Member | Branch |
|--------|--------|
| Pradunya | `origin/Pradunya` |
