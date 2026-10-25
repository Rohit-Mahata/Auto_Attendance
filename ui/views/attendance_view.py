import os
import csv
from datetime import datetime
from tkinter import *
from tkinter import ttk, messagebox, filedialog

from ui.theme import *
from db_engine import db

class AttendanceView(Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=BG_DARK)
        self.controller = controller
        self._build_layout()
        self.refresh_records()

    def _build_layout(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        # ================= 1. Top KPI Summary Cards =================
        kpi_strip = Frame(self, bg=BG_DARK, padx=16, pady=16)
        kpi_strip.grid(row=0, column=0, sticky="ew")
        kpi_strip.columnconfigure((0, 1, 2, 3), weight=1)

        self.card_total = self._create_metric_card(kpi_strip, 0, "Enrolled Students", "0", ACCENT_BLUE)
        self.card_present = self._create_metric_card(kpi_strip, 1, "Present Today", "0", ACCENT_EMERALD)
        self.card_absent = self._create_metric_card(kpi_strip, 2, "Absent Today", "0", ACCENT_ROSE)
        self.card_rate = self._create_metric_card(kpi_strip, 3, "Attendance Rate", "0.0%", ACCENT_AMBER)

        # ================= 2. Filter & Action Strip =================
        filter_card = Frame(self, bg=BG_SURFACE, padx=16, pady=12)
        filter_card.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 12))

        Label(filter_card, text="📅 Date:", font=FONT_BODY_BOLD, bg=BG_SURFACE, fg=TEXT_MAIN).pack(side=LEFT, padx=(0, 6))
        self.var_date = StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        entry_date = Entry(
            filter_card,
            textvariable=self.var_date,
            width=12,
            bg=BG_CARD,
            fg=TEXT_MAIN,
            insertbackground=TEXT_MAIN,
            font=FONT_BODY,
            relief="flat"
        )
        entry_date.pack(side=LEFT, padx=(0, 14), ipady=3)

        Label(filter_card, text="🔍 Student:", font=FONT_BODY_BOLD, bg=BG_SURFACE, fg=TEXT_MAIN).pack(side=LEFT, padx=(0, 6))
        self.var_query = StringVar()
        entry_query = Entry(
            filter_card,
            textvariable=self.var_query,
            width=20,
            bg=BG_CARD,
            fg=TEXT_MAIN,
            insertbackground=TEXT_MAIN,
            font=FONT_BODY,
            relief="flat"
        )
        entry_query.pack(side=LEFT, padx=(0, 14), ipady=3)

        btn_filter = Button(filter_card, text="Filter Records", command=self.refresh_records)
        style_button(btn_filter, variant="primary")
        btn_filter.pack(side=LEFT, padx=4)

        btn_reset = Button(filter_card, text="Show All", command=self.show_all_records)
        style_button(btn_reset, variant="secondary")
        btn_reset.pack(side=LEFT, padx=4)

        btn_export = Button(filter_card, text="📥 Export CSV", command=self.export_csv)
        style_button(btn_export, variant="success")
        btn_export.pack(side=RIGHT, padx=4)

        # ================= 3. Attendance Logs Table =================
        table_card = Frame(self, bg=BG_SURFACE, padx=16, pady=16)
        table_card.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 16))
        table_card.rowconfigure(0, weight=1)
        table_card.columnconfigure(0, weight=1)

        columns = ("id", "sid", "roll", "name", "classroom", "date", "time", "conf", "status")
        self.tree = ttk.Treeview(table_card, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("id", text="#")
        self.tree.heading("sid", text="Student ID")
        self.tree.heading("roll", text="Roll No")
        self.tree.heading("name", text="Student Name")
        self.tree.heading("classroom", text="Classroom")
        self.tree.heading("date", text="Date")
        self.tree.heading("time", text="Time")
        self.tree.heading("conf", text="Confidence")
        self.tree.heading("status", text="Status")

        self.tree.column("id", width=50, anchor="center")
        self.tree.column("sid", width=90, anchor="center")
        self.tree.column("roll", width=90, anchor="center")
        self.tree.column("name", width=160, anchor="w")
        self.tree.column("classroom", width=110, anchor="center")
        self.tree.column("date", width=100, anchor="center")
        self.tree.column("time", width=90, anchor="center")
        self.tree.column("conf", width=90, anchor="center")
        self.tree.column("status", width=90, anchor="center")

        tree_scroll = Scrollbar(table_card, orient=VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        tree_scroll.grid(row=0, column=1, sticky="ns")

    def _create_metric_card(self, parent, col, title, value, accent_color):
        card = Frame(parent, bg=BG_SURFACE, padx=16, pady=14, relief="flat")
        card.grid(row=0, column=col, padx=8, sticky="ew")

        lbl_v = Label(card, text=value, font=("Segoe UI", 20, "bold"), bg=BG_SURFACE, fg=accent_color)
        lbl_v.pack(anchor="w")

        lbl_t = Label(card, text=title, font=FONT_SMALL, bg=BG_SURFACE, fg=TEXT_MUTED)
        lbl_t.pack(anchor="w", pady=(2, 0))

        return lbl_v

    def refresh_records(self):
        d = self.var_date.get().strip()
        q = self.var_query.get().strip()

        # Update KPI Summary Cards
        summary = db.get_attendance_summary(date=d if d else None)
        self.card_total.config(text=str(summary["total"]))
        self.card_present.config(text=str(summary["present"]))
        self.card_absent.config(text=str(summary["absent"]))
        self.card_rate.config(text=f"{summary['attendance_rate']}%")

        # Fetch records
        records = db.get_attendance_logs(date=d if d else None, student_query=q if q else None)

        for item in self.tree.get_children():
            self.tree.delete(item)

        for r in records:
            conf_str = f"{r['confidence']}%" if r["confidence"] else "N/A"
            self.tree.insert("", END, values=(
                r["id"],
                r["student_id"],
                r["roll_no"],
                r["name"],
                r["classroom_id"],
                r["date"],
                r["time"],
                conf_str,
                r["status"]
            ))

    def show_all_records(self):
        self.var_date.set("")
        self.var_query.set("")
        self.refresh_records()

    def export_csv(self):
        records = db.get_attendance_logs()
        if not records:
            messagebox.showinfo("Export", "No attendance records to export.", parent=self)
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files (*.csv)", "*.csv"), ("All Files", "*.*")],
            initialfile=f"attendance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            parent=self
        )
        if not filename:
            return

        try:
            with open(filename, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Log ID", "Student ID", "Roll No", "Student Name", "Classroom", "Date", "Time", "Confidence", "Status"])
                for r in records:
                    writer.writerow([
                        r["id"], r["student_id"], r["roll_no"], r["name"],
                        r["classroom_id"], r["date"], r["time"], r["confidence"], r["status"]
                    ])
            messagebox.showinfo("Export Successful", f"Attendance logs saved to:\n{filename}", parent=self)
        except Exception as e:
            messagebox.showerror("Export Failed", f"Error exporting CSV: {e}", parent=self)
