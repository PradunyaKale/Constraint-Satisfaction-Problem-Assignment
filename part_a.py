import sys 
import csv
import json

BASE_DOMAIN = ['R', 'M', 'A', 'E']
SURGERY_SHIFT = 'B'

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

class NurseRoster:

    def __init__(self, N, D, Ns, Ng, m, a, e, T, days, K, leaves):
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

        self.start_time = None
        
    def consecutive_work_before(self, i, d):
        streak = 0
        dd = d - 1
        while dd >= 0 and streak < 5 and self.roster[i][dd] != 'R':
            streak += 1
            dd -= 1
        return streak
        
    def candidate_shifts(self, i, d):
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


    def apply(self, i, d, shift):
        self.roster[i][d] = shift
        counts = self.day_counts[d]
        if shift in ('M', 'A', 'E', 'B'):
            counts[shift] += 1
            self.shift_units[i] += 2 if shift == 'B' else 1

    def undo(self, i, d, shift):
        self.roster[i][d] = None
        counts = self.day_counts[d]
        if shift in ('M', 'A', 'E', 'B'):
            counts[shift] -= 1
            self.shift_units[i] -= 2 if shift == 'B' else 1


    def day_bucket_totals(self, d):
        c = self.day_counts[d]
        return c['M'] + c['B'], c['A'] + c['B'], c['E']

    def within_budget(self, d):
        mm, aa, ee = self.day_bucket_totals(d)
        return mm <= self.m and aa <= self.a and ee <= self.e

    def day_complete_and_valid(self, d):
        """Called once every nurse has a shift on day d (H4 + H7)."""
        mm, aa, ee = self.day_bucket_totals(d)
        if mm != self.m or aa != self.a or ee != self.e:
            return False
        if self.days[d] == 'S' and self.day_counts[d]['B'] == 0:
            return False
        return True

    def search(self, day=0, nurse=0):
        if day == self.D:
            return True

        if nurse == self.N:
            return self.day_complete_and_valid(day) and self.search(day + 1, 0)

        for shift in self.candidate_shifts(nurse, day):
            self.apply(nurse, day, shift)
            if self.within_budget(day) and self.search(day, nurse + 1):
                return True
            self.undo(nurse, day, shift)

        return False

    def solve(self):
        ok = self.search()
        return ok

    def to_json_dict(self):
        result = {}
        for i in range(self.N):
            for d in range(self.D):
                result[f"N{i}_{d}"] = self.roster[i][d]
        return result
    
    
if __name__ == '__main__': 

    N, D, Ns, Ng, m, a, e, T, days, max_shifts, leaves = parse_input(sys.argv[1])
    output_file = sys.argv[2]
    
    problem = NurseRoster(N, D, Ns, Ng, m, a, e, T, days, max_shifts, leaves)
    solved = problem.solve()

    with open(output_file, 'w') as f:
        if solved:
            json.dump(problem.to_json_dict(), f)
        else:
            json.dump({}, f)