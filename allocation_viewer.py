"""Browse one simulation report and compare student allocations side by side."""

import json
import tkinter as tk
from pathlib import Path
from tkinter import ttk


REPORT = Path(__file__).with_name("allocation_report.json")


class StudentViewer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Student Allocation Viewer")
        self.geometry("1180x720")
        self.records = json.loads(REPORT.read_text(encoding="utf-8"))
        self.filtered = self.records[:]

        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")
        ttk.Label(top, text="Search student or program").pack(side="left")
        self.query = tk.StringVar()
        entry = ttk.Entry(top, textvariable=self.query, width=32)
        entry.pack(side="left", padx=6)
        self.query.trace_add("write", lambda *_: self.refresh_list())
        ttk.Label(top, text="Sort").pack(side="left", padx=(12, 0))
        self.sort_mode = tk.StringVar(value="Market improvement")
        selector = ttk.Combobox(top, textvariable=self.sort_mode, state="readonly", width=22,
                                values=("Market improvement", "Market utility", "Senior-first utility", "Student ID"))
        selector.pack(side="left", padx=6)
        selector.bind("<<ComboboxSelected>>", lambda _: self.refresh_list())
        self.count_label = ttk.Label(top)
        self.count_label.pack(side="right")

        body = ttk.Panedwindow(self, orient="horizontal")
        body.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        left = ttk.Frame(body)
        right = ttk.Frame(body)
        body.add(left, weight=1)
        body.add(right, weight=3)

        self.students = ttk.Treeview(left, columns=("id", "delta"), show="headings", selectmode="browse")
        self.students.heading("id", text="Student")
        self.students.heading("delta", text="Market Δ utility")
        self.students.column("id", width=130)
        self.students.column("delta", width=105, anchor="e")
        scroll = ttk.Scrollbar(left, orient="vertical", command=self.students.yview)
        self.students.configure(yscrollcommand=scroll.set)
        self.students.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.students.bind("<<TreeviewSelect>>", self.show_student)

        header = ttk.Label(right, text="Select a student", padding=(8, 2))
        self.header = header
        header.pack(anchor="w")
        panels = ttk.Panedwindow(right, orient="horizontal")
        panels.pack(fill="both", expand=True)
        self.preference = self.make_panel(panels, "Ranked preferences")
        self.baseline = self.make_panel(panels, "Senior-first")
        self.market = self.make_panel(panels, "Price-and-priority market")
        panels.add(self.preference, weight=1)
        panels.add(self.baseline, weight=1)
        panels.add(self.market, weight=1)
        self.refresh_list()

    @staticmethod
    def make_panel(parent, title):
        frame = ttk.Labelframe(parent, text=title, padding=8)
        text = tk.Text(frame, wrap="word", width=32, state="disabled")
        text.pack(fill="both", expand=True)
        frame.text = text
        return frame

    def refresh_list(self):
        query = self.query.get().strip().lower()
        data = [item for item in self.records if not query or query in item["student_id"].lower() or query in item["program_category"].lower()]
        keys = {
            "Market improvement": lambda item: item["market_minus_senior_first_utility"],
            "Market utility": lambda item: item["market"]["utility"],
            "Senior-first utility": lambda item: item["senior_first"]["utility"],
            "Student ID": lambda item: item["student_id"],
        }
        data.sort(key=keys[self.sort_mode.get()], reverse=self.sort_mode.get() != "Student ID")
        self.filtered = data
        self.students.delete(*self.students.get_children())
        for index, item in enumerate(data):
            self.students.insert("", "end", iid=str(index), values=(item["student_id"], f"{item['market_minus_senior_first_utility']:+.2f}"))
        self.count_label.config(text=f"{len(data):,} students")
        if data:
            self.students.selection_set("0")
            self.show_student()

    def fill(self, panel, text):
        panel.text.config(state="normal")
        panel.text.delete("1.0", "end")
        panel.text.insert("1.0", text)
        panel.text.config(state="disabled")

    def show_student(self, _event=None):
        selected = self.students.selection()
        if not selected:
            return
        item = self.filtered[int(selected[0])]
        self.header.config(text=(f"{item['student_id']}  |  {item['year']}  |  {item['program_category']}  |  "
                                 f"Target: {item['target_credits']} credits  |  Market Δ: {item['market_minus_senior_first_utility']:+.2f}"))
        self.fill(self.preference, "\n".join(f"{index + 1}. {entry['course']}  ({entry['utility']:.2f})" for index, entry in enumerate(item["ranked_preferences"])))
        self.fill(self.baseline, f"Credits: {item['senior_first']['credits']}\nUtility: {item['senior_first']['utility']:.2f}\n\n" + "\n".join(item["senior_first"]["courses"]))
        self.fill(self.market, f"Credits: {item['market']['credits']}\nUtility: {item['market']['utility']:.2f}\n\n" + "\n".join(item["market"]["courses"]))


if __name__ == "__main__":
    if not REPORT.exists():
        raise SystemExit("Run the simulator with --report allocation_report.json first.")
    StudentViewer().mainloop()
