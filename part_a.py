import sys 
import csv

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
if __name__ == '__main__': 

    N, D, Ns, Ng, m, a, e, T, days, max_shifts, leaves = parse_input(sys.argv[1])
    output_file = sys.argv[2]


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