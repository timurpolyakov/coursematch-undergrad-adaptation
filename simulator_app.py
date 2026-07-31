"""Desktop controls for running the enrollment-policy comparison."""

import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk


ROOT = Path(__file__).resolve().parent


class EnrollmentGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Cornell Enrollment Policy Simulator")
        self.minsize(720, 480)

        controls = ttk.Frame(self, padding=12)
        controls.pack(fill="x")
        # Use the complete synthetic population by default so reports and
        # downstream graphs reflect the model rather than a small sample.
        self.students = tk.IntVar(value=0)
        self.trials = tk.IntVar(value=1)
        self.seed = tk.IntVar(value=2025)
        self._field(controls, "Profiles (0 = all 16,138)", self.students, 0)
        self._field(controls, "Trials", self.trials, 1)
        self._field(controls, "Random seed", self.seed, 2)
        self.run_button = ttk.Button(controls, text="Run both policies", command=self.run)
        self.run_button.grid(row=0, column=6, padx=(16, 0), pady=4, sticky="ew")

        self.status = ttk.Label(self, text="Choose inputs, then run the comparison.", padding=(12, 0))
        self.status.pack(anchor="w")
        self.output = tk.Text(self, wrap="word", height=25, padx=12, pady=12)
        self.output.pack(fill="both", expand=True, padx=12, pady=12)

    def _field(self, parent, label, value, column):
        ttk.Label(parent, text=label).grid(row=0, column=column * 2, sticky="w")
        ttk.Entry(parent, textvariable=value, width=12).grid(row=0, column=column * 2 + 1, padx=(4, 12), pady=4)

    def run(self):
        try:
            students, trials, seed = self.students.get(), self.trials.get(), self.seed.get()
            if students < 0 or trials < 1:
                raise ValueError
        except (tk.TclError, ValueError):
            self.status.config(text="Profiles must be 0 or greater; trials must be at least 1.")
            return
        self.run_button.state(["disabled"])
        self.output.delete("1.0", "end")
        self.status.config(text="Running senior-first and price-and-priority simulations…")
        threading.Thread(target=self._run_process, args=(students, trials, seed), daemon=True).start()

    def _run_process(self, students, trials, seed):
        command = [
            sys.executable, "enrollment_simulator.py", "--students", str(students), "--trials", str(trials), "--seed", str(seed),
            "--show-students", "5", "--report", "allocation_report.json",
        ]
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        text = result.stdout if result.returncode == 0 else result.stderr
        self.after(0, self._finished, text, result.returncode)

    def _finished(self, text, returncode):
        self.output.insert("1.0", text)
        self.status.config(text="Complete." if returncode == 0 else "Simulation failed; see output.")
        self.run_button.state(["!disabled"])


if __name__ == "__main__":
    EnrollmentGUI().mainloop()
