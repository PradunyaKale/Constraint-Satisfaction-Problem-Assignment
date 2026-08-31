import sys
import csv
import json
import random

BASE_DOMAIN = ['R', 'M', 'A', 'E']
SURGERY_SHIFT = 'B'

MAX_SIDEWAYS_MOVES = 100

MAX_ITERATIONS = 10000


def parse_input(input_csv):
    """Reads the CSV and initializes problem variables."""
    with open(input_csv, 'r') as f:
        reader = csv.DictReader(f)
        row = next(reader)
        print(row)

        N = int(row['N'])               #Number of nurses
        D = int(row['D'])               #Number of days
        N_s = int(row['N_s'])           #Number of surgical nurses
        N_g = int(row['N_g'])           #Number of general nurses
        m = int(row['m'])               #Exact number of nursese required on Morning
        a = int(row['a'])               #Exact number of nursese required on Afternoon
        e = int(row['e'])               #Exact number of nursese required on Evening
        T = float(row['T'])             #The time budget for providing a solution to a test problem (in seconds)
        days = row['days']              # A string of length D indicating which days are general and which days are surgical
        max_shifts = int(row['K'])      #The maximum shifts allowed for any nurse overall
        leaves = row['leaves']          #Example: WWWWWLWWWWWW
    return N, D, N_s, N_g, m, a, e, T, days, max_shifts, leaves


class NurseRosterSoft:

    def __init__(self, N, D, Ns, Ng, m, a, e, T, days, K, leaves):
        """Initializes the nurse roster problem state, including per-nurse shift counts used for the soft-cost objective."""
        self.N, self.D = N, D
        self.Ns, self.Ng = Ns, Ng
        self.m, self.a, self.e = m, a, e
        self.T = T
        self.days = days
        self.K = K

        self.nurse_type = ['S'] * Ns + ['G'] * Ng

        self.leave_days = [set() for _ in range(N)]
        for i in range(N):
            block = leaves[i * D:(i + 1) * D]
            for d, c in enumerate(block):
                if c == 'L':
                    self.leave_days[i].add(d)

        self.roster = [[None] * D for _ in range(N)]
        self.shift_units = [0] * N
        self.day_counts = [{'M': 0, 'A': 0, 'E': 0, 'B': 0} for _ in range(D)]

        self.nurse_counts = [{'M': 0, 'A': 0, 'E': 0} for _ in range(N)]

        self.start_time = None

    # ------------------------------------------------------------------
    # Shared with Part A: per-nurse legal-value computation
    # ------------------------------------------------------------------
    def consecutive_work_before(self, i, d):
        """Counts the number of consecutive working days for a nurse immediately before day d."""
        streak = 0
        dd = d - 1
        while dd >= 0 and streak < 5 and self.roster[i][dd] != 'R':
            streak += 1
            dd -= 1
        return streak

    def candidate_shifts(self, i, d):
        """Computes the legal shift assignments for a nurse on a given day, based on constraints already fixed by prior days."""

        if d in self.leave_days[i]:
            return ['R']

        options = list(BASE_DOMAIN)
        if self.nurse_type[i] == 'S' and self.days[d] == 'S':
            options.append(SURGERY_SHIFT)

        prev = self.roster[i][d - 1] if d > 0 else None
        legal = []
        for shift in options:
            if shift == 'R':
                legal.append(shift)
                continue

            # H5: 5 consecutive working days already used up -> must rest
            if self.consecutive_work_before(i, d) >= 5:
                continue

            # H2: no two consecutive morning shifts (B counts as a morning)
            if shift in ('M', 'B') and prev in ('M', 'B'):
                continue

            # H3: no morning immediately after evening
            if shift in ('M', 'B') and prev == 'E':
                continue

            # H6: after a B, cannot do M or A the next day
            if prev == 'B' and shift in ('M', 'A'):
                continue

            # H8: total shift-unit budget K
            units = 2 if shift == 'B' else 1
            if self.shift_units[i] + units > self.K:
                continue

            legal.append(shift)
        return legal

    def unrestricted_domain(self, i, d):
        """Returns the full set of possible shifts for a nurse on a given day, without applying sequential constraints."""

        if d in self.leave_days[i]:
            return ['R']
        options = list(BASE_DOMAIN)
        if self.nurse_type[i] == 'S' and self.days[d] == 'S':
            options.append(SURGERY_SHIFT)
        return options

    def forward_check(self, i, d):
        """Checks whether a nurse still has at least one legal shift option on the next day."""

        if d + 1 >= self.D:
            return True
        return len(self.candidate_shifts(i, d + 1)) > 0

    # ------------------------------------------------------------------
    # Soft-constraint-aware value ordering (construction phase only)
    # ------------------------------------------------------------------
    
    def balance_order(self, i, options):
        """Reorders a nurse's candidate shifts to prefer the M/A/E bucket the nurse currently has fewest of, promoting balance during construction."""

        counts = self.nurse_counts[i]

        normal_shifts = ['M', 'A', 'E']

        # Sort M/A/E according to which shift has the fewest assignments
        normal_shifts = sorted(normal_shifts, key=lambda shift: counts[shift])

        result = []

        # R should always come first
        if 'R' in options:
            result.append('R')

        # Add M/A/E in balanced order
        for shift in normal_shifts:
            if shift in options:
                result.append(shift)

        # B should always come last
        if 'B' in options:
            result.append('B')

        return result

    # ------------------------------------------------------------------
    # Apply / undo an assignment (construction phase)
    # ------------------------------------------------------------------
    def apply(self, i, d, shift):
        """Assigns a shift to a nurse on a given day and updates shift, day, and nurse-level counters."""
        self.roster[i][d] = shift
        counts = self.day_counts[d]
        if shift in ('M', 'A', 'E', 'B'):
            counts[shift] += 1
            self.shift_units[i] += 2 if shift == 'B' else 1
        if shift == 'B':
            self.nurse_counts[i]['M'] += 1
            self.nurse_counts[i]['A'] += 1
        elif shift in ('M', 'A', 'E'):
            self.nurse_counts[i][shift] += 1

    def undo(self, i, d, shift):
        """Reverts a previously applied shift assignment and updates shift, day, and nurse-level counters."""
        self.roster[i][d] = None
        counts = self.day_counts[d]
        if shift in ('M', 'A', 'E', 'B'):
            counts[shift] -= 1
            self.shift_units[i] -= 2 if shift == 'B' else 1
        if shift == 'B':
            self.nurse_counts[i]['M'] -= 1
            self.nurse_counts[i]['A'] -= 1
        elif shift in ('M', 'A', 'E'):
            self.nurse_counts[i][shift] -= 1

    # ------------------------------------------------------------------
    # Day-level quota (H4/H7) -- same as Part A
    # ------------------------------------------------------------------
    def day_bucket_totals(self, d):
        """Computes the total number of nurses covering the Morning, Afternoon, and Evening buckets on a given day."""
        c = self.day_counts[d]
        return c['M'] + c['B'], c['A'] + c['B'], c['E']

    def within_budget(self, d):
        """Checks whether the current shift counts for a day are within the required limits."""
        mm, aa, ee = self.day_bucket_totals(d)
        return mm <= self.m and aa <= self.a and ee <= self.e

    def day_complete_and_valid(self, d):
        """Validates that a fully assigned day satisfies the exact staffing requirements and surgical-day coverage constraint."""
        mm, aa, ee = self.day_bucket_totals(d)
        if mm != self.m or aa != self.a or ee != self.e:
            return False
        if self.days[d] == 'S' and self.day_counts[d]['B'] == 0:
            return False
        return True

    def quota_feasible(self, day, domains, b_already_assigned):
        """Checks whether remaining unassigned nurses can still satisfy the day's staffing requirements, given their current candidate domains."""
        mm, aa, ee = self.day_bucket_totals(day)
        need_m, need_a, need_e = self.m - mm, self.a - aa, self.e - ee
        if need_m < 0 or need_a < 0 or need_e < 0:
            return False
        supply_m = sum(1 for v in domains.values() if 'M' in v or 'B' in v)
        supply_a = sum(1 for v in domains.values() if 'A' in v or 'B' in v)
        supply_e = sum(1 for v in domains.values() if 'E' in v)
        if supply_m < need_m or supply_a < need_a or supply_e < need_e:
            return False
        if self.days[day] == 'S' and not b_already_assigned:
            if not any('B' in v for v in domains.values()):
                return False
        return True

    def next_day_quota_plausible(self, day):
        """Performs a lookahead check to verify that the following day's staffing requirements can plausibly be met given current assignments."""
        nd = day + 1
        if nd >= self.D:
            return True
        domains = {}
        for i in range(self.N):
            if self.roster[i][day] is not None:
                domains[i] = self.candidate_shifts(i, nd)
            else:
                domains[i] = self.unrestricted_domain(i, nd)
        supply_m = sum(1 for v in domains.values() if 'M' in v or 'B' in v)
        supply_a = sum(1 for v in domains.values() if 'A' in v or 'B' in v)
        supply_e = sum(1 for v in domains.values() if 'E' in v)
        if supply_m < self.m or supply_a < self.a or supply_e < self.e:
            return False
        if self.days[nd] == 'S' and not any('B' in v for v in domains.values()):
            return False
        return True


    # ------------------------------------------------------------------
    # Phase 1: backtracking search to find ANY valid roster
    # ------------------------------------------------------------------
    def search(self, day=0, unassigned=None):
        """Performs backtracking search with MRV ordering and forward checking to find a valid nurse roster assignment."""
        if day == self.D:
            return True
        if unassigned is None:
            unassigned = list(range(self.N))
        if not unassigned:
            return self.day_complete_and_valid(day) and self.search(day + 1, None)

        domains = {i: self.candidate_shifts(i, day) for i in unassigned}
        if any(len(v) == 0 for v in domains.values()):
            return False

        b_assigned = self.day_counts[day]['B'] > 0
        if not self.quota_feasible(day, domains, b_assigned):
            return False
        if not self.next_day_quota_plausible(day):
            return False

        # MRV: branch on the most-constrained nurse first.
        nurse = min(unassigned, key=lambda i: len(domains[i]))
        remaining = [i for i in unassigned if i != nurse]
        ordered = self.balance_order(nurse, domains[nurse])

        for shift in ordered:
            self.apply(nurse, day, shift)
            if (self.within_budget(day)
                    and self.forward_check(nurse, day)
                    and self.search(day, remaining)):
                return True
            self.undo(nurse, day, shift)

        return False

    # ------------------------------------------------------------------
    # Phase 2: same-day pairwise-swap local search on the soft cost
    # ------------------------------------------------------------------
    def nurse_cost(self, i):
        """Computes the soft-constraint cost for a single nurse based on the spread of their Morning, Afternoon, and Evening shift counts."""
        # cost_i = (M-A)^2 + (A-E)^2 + (M-E)^2 -- the exact-integer
        # closed form of the spec's 9*(1/3)*sum-of-squared-deviations
        # formula for exactly 3 buckets (standard sum-of-squared-
        # pairwise-differences identity), so no floats are needed.
        c = self.nurse_counts[i]
        m, a, e = c['M'], c['A'], c['E']
        return (m - a) ** 2 + (a - e) ** 2 + (m - e) ** 2

    def total_cost(self):
        """Computes the total soft-constraint cost across all nurses."""
        return sum(self.nurse_cost(i) for i in range(self.N))

    @staticmethod
    def temporal_ok(prev, cur):
        """Checks whether two consecutive shift assignments satisfy the sequential shift constraints."""
        if cur in ('M', 'B') and prev in ('M', 'B'):
            return False
        if cur in ('M', 'B') and prev == 'E':
            return False
        if prev == 'B' and cur in ('M', 'A'):
            return False
        return True

    def can_place(self, i, d, shift):
        """Checks whether a nurse could legally hold a given shift on a given day, considering both the preceding and following days."""
        if d in self.leave_days[i] and shift != 'R':                # H9
            return False
        if shift == 'B' and (self.nurse_type[i] != 'S'               # H1
                              or self.days[d] != 'S'):
            return False

        prev = self.roster[i][d - 1] if d > 0 else None
        nxt = self.roster[i][d + 1] if d + 1 < self.D else None
        if prev is not None and not self.temporal_ok(prev, shift):    # H2/H3
            return False
        if nxt is not None and not self.temporal_ok(shift, nxt):      # H2/H3/H6 (forward)
            return False

        if shift != 'R':
            old = self.roster[i][d]
            old_units = 2 if old == 'B' else (1 if old in ('M', 'A', 'E') else 0)
            new_units = 2 if shift == 'B' else 1
            if self.shift_units[i] - old_units + new_units > self.K:  # H8
                return False

            back = 0
            dd = d - 1
            while dd >= 0 and back < 5 and self.roster[i][dd] != 'R':
                back += 1
                dd -= 1
            fwd = 0
            dd = d + 1
            while dd < self.D and fwd < 5 and self.roster[i][dd] != 'R':
                fwd += 1
                dd += 1
            if back + 1 + fwd > 5:                                    # H5
                return False

        return True

    def _cell_delta(self, i, shift, sign):
        """Updates a nurse's shift-unit and shift-count totals to reflect adding or removing a single shift assignment."""
        if shift in ('M', 'A', 'E', 'B'):
            self.shift_units[i] += sign * (2 if shift == 'B' else 1)
        if shift == 'B':
            self.nurse_counts[i]['M'] += sign
            self.nurse_counts[i]['A'] += sign
        elif shift in ('M', 'A', 'E'):
            self.nurse_counts[i][shift] += sign

    def commit_swap(self, i, j, d, new_i, new_j):
        """Performs a same-day shift swap between two nurses, updating their shift-unit and shift-count totals accordingly."""
        old_i, old_j = self.roster[i][d], self.roster[j][d]
        self._cell_delta(i, old_i, -1)
        self._cell_delta(j, old_j, -1)
        self.roster[i][d] = new_i
        self.roster[j][d] = new_j
        self._cell_delta(i, new_i, +1)
        self._cell_delta(j, new_j, +1)

    def _recompute_derived_state(self):
        """Rebuilds nurse shift counts and shift-unit totals from the current roster after a wholesale roster substitution."""
        self.nurse_counts = [{'M': 0, 'A': 0, 'E': 0} for _ in range(self.N)]
        self.shift_units = [0] * self.N
        for i in range(self.N):
            for d in range(self.D):
                shift = self.roster[i][d]
                if shift == 'B':
                    self.nurse_counts[i]['M'] += 1
                    self.nurse_counts[i]['A'] += 1
                    self.shift_units[i] += 2
                elif shift in ('M', 'A', 'E'):
                    self.nurse_counts[i][shift] += 1
                    self.shift_units[i] += 1

    def local_search(self):
        """Performs stochastic hill climbing with sideways moves on the soft cost, using same-day nurse-pair swaps as the move set."""
        if self.N < 2 or self.D == 0:
            return

        rng = random.Random()

        current_cost = self.total_cost()
        best_cost = current_cost
        best_roster = [row[:] for row in self.roster]
        sideways_streak = 0

        for _ in range(MAX_ITERATIONS):
            d = rng.randrange(self.D)
            i = rng.randrange(self.N)
            j = rng.randrange(self.N)
            if i == j:
                continue
            oi, oj = self.roster[i][d], self.roster[j][d]
            if oi == oj:
                continue
            if not (self.can_place(i, d, oj) and self.can_place(j, d, oi)):
                continue

            before = self.nurse_cost(i) + self.nurse_cost(j)
            self.commit_swap(i, j, d, oj, oi)
            after = self.nurse_cost(i) + self.nurse_cost(j)
            delta = after - before

            if delta < 0:
                # Genuine improvement -- always accept, reset the
                # sideways allowance, and remember this as the best
                # roster seen so far.
                current_cost += delta
                sideways_streak = 0
                if current_cost < best_cost:
                    best_cost = current_cost
                    best_roster = [row[:] for row in self.roster]
                continue

            if delta == 0 and sideways_streak < MAX_SIDEWAYS_MOVES:
                # Lateral move on a plateau/shoulder: take it to keep
                # exploring, but count it against the streak limit.
                sideways_streak += 1
                continue

            # Move makes things worse, or the sideways allowance for
            # this plateau is used up -- reject and revert.
            self.commit_swap(i, j, d, oi, oj)

        # Belt-and-braces: hand back the best roster ever observed,
        # not just wherever the walk happened to be when time ran out.
        if best_cost < current_cost:
            self.roster = best_roster
            self._recompute_derived_state()

    def solve(self):
        """Runs the backtracking search followed by local search to produce a valid, cost-optimized nurse roster."""
        found = self.search()
        if not found:
            return False

        self.local_search()
        return True

    def to_json_dict(self):
        """Converts the solved roster into a JSON-serializable dictionary."""
        result = {}
        for i in range(self.N):
            for d in range(self.D):
                result[f"N{i}_{d}"] = self.roster[i][d]
        return result


if __name__ == '__main__':
    N, D, Ns, Ng, m, a, e, T, days, max_shifts, leaves = parse_input(sys.argv[1])
    output_file = sys.argv[2]

    problem = NurseRosterSoft(N, D, Ns, Ng, m, a, e, T, days, max_shifts, leaves)
    solved = problem.solve()

    with open(output_file, 'w') as f:
        if solved:
            json.dump(problem.to_json_dict(), f)
        else:
            json.dump({}, f)