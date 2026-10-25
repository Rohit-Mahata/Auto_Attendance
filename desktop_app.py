"""
Northfield University of Technology — Attendance Intelligence System
100% Pure Native Desktop Application (Zero Website, Zero Browser)
Built with Python Tkinter matching flow.png, student_portal.png, dept_view.png, settings_rules.png
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

# ================= Color Palette (Matches flow.png) =================
BG_APP = "#f7f6f2"           # Warm off-white / ivory canvas
BG_CARD = "#ffffff"          # Pure white card surface
BG_CARD_SUBTLE = "#f2f0ea"   # Subtle breakdown card background
BG_GRID_FLOOR = "#182026"    # Dark classroom chalkboard floor
BORDER_COLOR = "#e5e3dc"     # Crisp subtle borders
TEXT_MAIN = "#192026"        # Deep charcoal
TEXT_MUTED = "#656e77"       # Secondary muted text
TEXT_DIM = "#8c959f"         # Dim tertiary text

ACCENT_GREEN = "#1d734d"     # Official Northfield forest green
ACCENT_GREEN_RING = "#22c55e"# Bright green seat ring
ACCENT_GREEN_BG = "#eaf5ee"  # Green badge background

ACCENT_AMBER = "#b25e02"     # Unclear amber
ACCENT_AMBER_RING = "#f59e0b"# Bright amber ring
ACCENT_AMBER_BG = "#fdf5ea"  # Amber badge background

ACCENT_ROSE = "#cf222e"      # Absent / Offline red
ACCENT_ROSE_BG = "#ffebe9"

class NorthfieldDesktopApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Northfield University of Technology — Attendance Intelligence")
        self.geometry("1440x880+30+20")
        self.minsize(1200, 720)
        self.configure(bg=BG_APP)

        # State Data
        self.enrolled = 60
        self.counted = 50
        self.identified = 44
        self.unclear_count = 6
        self.absent = 10
        self.active_person_idx = 1 # Person 2 (index 1)
        self.review_mode = "person" # "person" or "name"
        self.mismatch_active = False

        # 6 Unclear Persons
        self.unclear_persons = [
            {
                "id": 1,
                "row": 1, "col": 8,
                "tracking": "Still tracking · row 1, seat 8 · followed in 12 of 16 frames",
                "crops": [
                    ("09:01", "Turned away", False),
                    ("09:03", "Shadowed", False),
                    ("09:06", "Blurred", False),
                    ("09:08", "Best so far", True)
                ],
                "candidates": [
                    ("22CS1029", "Imran Sheikh", "Strong", "●●●", ACCENT_GREEN),
                    ("22CS1058", "Lakshya Bist", "Fair", "●●○", ACCENT_AMBER),
                    ("22CS1012", "Bikram Thapa", "Weak", "●○○", TEXT_DIM)
                ]
            },
            {
                "id": 2,
                "row": 2, "col": 3,
                "tracking": "Still tracking · row 2, seat 3 · followed in 14 of 16 frames",
                "crops": [
                    ("09:02", "Too dark", False),
                    ("09:04", "Blurred", False),
                    ("09:05", "Turned away", False),
                    ("09:07", "Partly hidden", False),
                    ("09:08", "Best so far", True)
                ],
                "candidates": [
                    ("22CS1038", "Karan Mehta", "Strong", "●●●", ACCENT_GREEN),
                    ("22CS1044", "Simran Kaur", "Fair", "●●○", ACCENT_AMBER),
                    ("22CS1059", "Dev Patel", "Weak", "●○○", TEXT_DIM)
                ]
            },
            {
                "id": 3,
                "row": 3, "col": 8,
                "tracking": "Still tracking · row 3, seat 8 · followed in 15 of 16 frames",
                "crops": [
                    ("09:02", "Looking down", False),
                    ("09:05", "Blurred", False),
                    ("09:08", "Best so far", True)
                ],
                "candidates": [
                    ("22CS1007", "Anjali Gurung", "Strong", "●●●", ACCENT_GREEN),
                    ("22CS1040", "Pooja Rana", "Fair", "●●○", ACCENT_AMBER)
                ]
            },
            {
                "id": 4,
                "row": 4, "col": 5,
                "tracking": "Still tracking · row 4, seat 5 · followed in 10 of 16 frames",
                "crops": [
                    ("09:03", "Turned sideways", False),
                    ("09:07", "Best so far", True)
                ],
                "candidates": [
                    ("22CS1063", "Tanvir Rahman", "Strong", "●●●", ACCENT_GREEN),
                    ("22CS1047", "Aarav Sharma", "Weak", "●○○", TEXT_DIM)
                ]
            },
            {
                "id": 5,
                "row": 5, "col": 2,
                "tracking": "Still tracking · row 5, seat 2 · followed in 13 of 16 frames",
                "crops": [
                    ("09:04", "Low light", False),
                    ("09:08", "Best so far", True)
                ],
                "candidates": [
                    ("22CS1051", "Fatima Noor", "Strong", "●●●", ACCENT_GREEN),
                    ("22CS1056", "Joel Mathew", "Weak", "●○○", TEXT_DIM)
                ]
            },
            {
                "id": 6,
                "row": 5, "col": 9,
                "tracking": "Still tracking · row 5, seat 9 · followed in 11 of 16 frames",
                "crops": [
                    ("09:02", "Hoodie occlusion", False),
                    ("09:07", "Best so far", True)
                ],
                "candidates": [
                    ("22CS1018", "Rohit Mahata", "Strong", "●●●", ACCENT_GREEN),
                    ("22CS1033", "Kavya Reddy", "Fair", "●●○", ACCENT_AMBER)
                ]
            }
        ]

        self._build_top_header()
        self._build_views_container()
        self.show_view("instructor")

    # ================= 1. Top Header =================
    def _build_top_header(self):
        header = tk.Frame(self, bg="#ffffff", height=60, bd=0, highlightthickness=1, highlightbackground=BORDER_COLOR)
        header.pack(fill=tk.X, side=tk.TOP)

        # Left Logo
        left_box = tk.Frame(header, bg="#ffffff")
        left_box.pack(side=tk.LEFT, padx=24, pady=10)

        # Circular N Logo
        logo_lbl = tk.Label(
            left_box, text="N", font=("Times New Roman", 15, "bold"),
            bg="#ffffff", fg=ACCENT_GREEN, width=2, height=1,
            bd=1, relief="solid", highlightcolor=ACCENT_GREEN
        )
        logo_lbl.pack(side=tk.LEFT, padx=(0, 10))

        title_box = tk.Frame(left_box, bg="#ffffff")
        title_box.pack(side=tk.LEFT)
        tk.Label(title_box, text="Northfield University of Technology", font=("Segoe UI", 12, "bold"), bg="#ffffff", fg=TEXT_MAIN).pack(anchor="w")
        self.lbl_sub = tk.Label(title_box, text="Attendance · Instructor view", font=("Segoe UI", 9), bg="#ffffff", fg=TEXT_MUTED)
        self.lbl_sub.pack(anchor="w")

        # Center Navigation Tabs
        nav_box = tk.Frame(header, bg=BG_APP, padx=4, pady=4, bd=1, relief="solid", highlightbackground=BORDER_COLOR)
        nav_box.pack(side=tk.LEFT, padx=30)

        self.tab_buttons = {}
        tabs = [
            ("instructor", "📋 Instructor Flow"),
            ("student", "🎓 Student Portal"),
            ("dept", "🏢 Department Office"),
            ("settings", "⚙️ Enrolment & Rules")
        ]
        for key, text in tabs:
            btn = tk.Button(
                nav_box, text=text, font=("Segoe UI", 9, "bold"),
                bg=BG_APP, fg=TEXT_MUTED, bd=0, relief="flat", cursor="hand2", padx=10, pady=4,
                command=lambda k=key: self.show_view(k)
            )
            btn.pack(side=tk.LEFT, padx=2)
            self.tab_buttons[key] = btn

        # Right Profile
        right_box = tk.Frame(header, bg="#ffffff")
        right_box.pack(side=tk.RIGHT, padx=24)
        tk.Label(right_box, text="Dr. Meera Iyer", font=("Segoe UI", 10, "bold"), bg="#ffffff", fg=TEXT_MAIN).pack(anchor="e")
        tk.Label(right_box, text="School of Computing & Engineering", font=("Segoe UI", 8), bg="#ffffff", fg=TEXT_MUTED).pack(anchor="e")

    # ================= 2. Views Container =================
    def _build_views_container(self):
        self.views_container = tk.Frame(self, bg=BG_APP)
        self.views_container.pack(fill=tk.BOTH, expand=True)

        self.views = {
            "instructor": tk.Frame(self.views_container, bg=BG_APP),
            "student": tk.Frame(self.views_container, bg=BG_APP),
            "dept": tk.Frame(self.views_container, bg=BG_APP),
            "settings": tk.Frame(self.views_container, bg=BG_APP)
        }

        for v in self.views.values():
            v.place(x=0, y=0, relwidth=1, relheight=1)

        self._build_instructor_view(self.views["instructor"])
        self._build_student_view(self.views["student"])
        self._build_dept_view(self.views["dept"])
        self._build_settings_view(self.views["settings"])

    def show_view(self, key):
        view = self.views.get(key)
        if view:
            view.tkraise()
            for k, btn in self.tab_buttons.items():
                if k == key:
                    btn.configure(bg="#ffffff", fg=ACCENT_GREEN)
                else:
                    btn.configure(bg=BG_APP, fg=TEXT_MUTED)

            sub_texts = {
                "instructor": "Attendance · Instructor view",
                "student": "Student portal · Attendance",
                "dept": "Attendance · Department office",
                "settings": "Attendance · Settings & Enrolment"
            }
            self.lbl_sub.config(text=sub_texts.get(key, ""))

    # ================= 3. INSTRUCTOR VIEW (flow.png) =================
    def _build_instructor_view(self, parent):
        # Outer Scrollable/Padded Frame
        outer = tk.Frame(parent, bg=BG_APP, padx=28, pady=16)
        outer.pack(fill=tk.BOTH, expand=True)

        # Top Session Meta Bar + Stat Counters
        meta_bar = tk.Frame(outer, bg=BG_APP)
        meta_bar.pack(fill=tk.X, pady=(0, 14))

        meta_left = tk.Frame(meta_bar, bg=BG_APP)
        meta_left.pack(side=tk.LEFT)

        tk.Label(meta_left, text="Attendance › CS-2104 › Session 14", font=("Segoe UI", 9), bg=BG_APP, fg=TEXT_MUTED).pack(anchor="w")
        today_str = datetime.now().strftime("%a %d %b %Y")
        self.lbl_session_sub = tk.Label(
            meta_left,
            text=f"Block B, Lab 3 · {today_str} · 09:00 – 10:00 · Still tracking {self.unclear_count} people",
            font=("Segoe UI", 9), bg=BG_APP, fg=TEXT_MUTED
        )
        self.lbl_session_sub.pack(anchor="w")

        # KPI Counters on Right
        kpi_frame = tk.Frame(meta_bar, bg=BG_APP)
        kpi_frame.pack(side=tk.RIGHT)

        def make_kpi(p, val, lbl, color=TEXT_MAIN):
            f = tk.Frame(p, bg=BG_APP, padx=12)
            f.pack(side=tk.LEFT)
            v = tk.Label(f, text=str(val), font=("Segoe UI", 22, "bold"), bg=BG_APP, fg=color)
            v.pack()
            l = tk.Label(f, text=lbl, font=("Segoe UI", 8), bg=BG_APP, fg=TEXT_MUTED)
            l.pack()
            return v

        self.kpi_enrolled_lbl = make_kpi(kpi_frame, self.enrolled, "Enrolled")
        self.kpi_counted_lbl = make_kpi(kpi_frame, self.counted, "Counted in room")
        self.kpi_identified_lbl = make_kpi(kpi_frame, self.identified, "Identified", ACCENT_GREEN)
        self.kpi_unclear_lbl = make_kpi(kpi_frame, self.unclear_count, "Unclear", ACCENT_AMBER)
        self.kpi_absent_lbl = make_kpi(kpi_frame, self.absent, "Absent")

        # Submit Box
        sub_box = tk.Frame(kpi_frame, bg=BG_APP, padx=10)
        sub_box.pack(side=tk.LEFT)
        self.btn_submit = tk.Button(
            sub_box, text="Submit", font=("Segoe UI", 10, "bold"),
            bg="#e5e3dc", fg=TEXT_DIM, bd=0, relief="flat", padx=16, pady=4, state=tk.DISABLED
        )
        self.btn_submit.pack()
        self.lbl_submit_hint = tk.Label(sub_box, text=f"Resolve {self.unclear_count} to submit", font=("Segoe UI", 8), bg=BG_APP, fg=TEXT_MUTED)
        self.lbl_submit_hint.pack()

        # Rule 1 Banner (Hidden by default)
        self.banner_frame = tk.Frame(outer, bg=ACCENT_AMBER_BG, highlightbackground="#f6d19c", highlightthickness=1, padx=12, pady=8)
        lbl_b = tk.Label(
            self.banner_frame,
            text="⚠️ Count Mismatch: Headcount detected 50, but only 48 active tracks found. 2 people not located (seats row 3 seat 4, row 5 seat 7 obscured). Not guessing identities.",
            font=("Segoe UI", 9, "bold"), bg=ACCENT_AMBER_BG, fg="#7c4103"
        )
        lbl_b.pack(side=tk.LEFT)
        tk.Button(
            self.banner_frame, text="Acknowledge", font=("Segoe UI", 8, "bold"),
            bg="#ffffff", bd=1, relief="solid", command=self.toggle_mismatch_rule
        ).pack(side=tk.RIGHT)

        # Two-Column Classroom Workspace
        workspace = tk.Frame(outer, bg=BG_APP)
        workspace.pack(fill=tk.BOTH, expand=True)
        workspace.columnconfigure(0, weight=5)
        workspace.columnconfigure(1, weight=5)
        workspace.rowconfigure(0, weight=1)

        # ================= LEFT: CLASSROOM VIEW =================
        left_card = tk.Frame(workspace, bg=BG_CARD, bd=1, relief="solid", highlightbackground=BORDER_COLOR, padx=16, pady=16)
        left_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        # Title
        lh = tk.Frame(left_card, bg=BG_CARD)
        lh.pack(fill=tk.X, pady=(0, 8))
        tk.Label(lh, text="CLASSROOM VIEW", font=("Segoe UI", 9, "bold"), bg=BG_CARD, fg=TEXT_MUTED).pack(side=tk.LEFT)
        tk.Label(lh, text="50 people counted · 5 rows of 10", font=("Segoe UI", 9), bg=BG_CARD, fg=TEXT_MUTED).pack(side=tk.RIGHT)

        # Blackboard Seating Grid Canvas
        self.canvas_grid = tk.Canvas(left_card, bg=BG_GRID_FLOOR, height=270, highlightthickness=0)
        self.canvas_grid.pack(fill=tk.X, pady=4)
        self.canvas_grid.bind("<Button-1>", self.on_canvas_seat_click)

        # Legend
        leg_box = tk.Frame(left_card, bg=BG_CARD, pady=6)
        leg_box.pack(fill=tk.X)
        tk.Label(leg_box, text="○ Identified with confidence", font=("Segoe UI", 8), bg=BG_CARD, fg=ACCENT_GREEN).pack(side=tk.LEFT, padx=(0, 16))
        tk.Label(leg_box, text="○ Unclear, being tracked", font=("Segoe UI", 8), bg=BG_CARD, fg=ACCENT_AMBER).pack(side=tk.LEFT)
        tk.Label(leg_box, text="Rings follow each person between frames", font=("Segoe UI", 8), bg=BG_CARD, fg=TEXT_DIM).pack(side=tk.RIGHT)

        # Breakdown Card: "HOW THE NUMBERS ADD UP"
        breakdown = tk.Frame(left_card, bg=BG_CARD_SUBTLE, padx=12, pady=10, bd=1, relief="solid", highlightbackground=BORDER_COLOR)
        breakdown.pack(fill=tk.X, pady=(8, 0))

        tk.Label(breakdown, text="HOW THE NUMBERS ADD UP", font=("Segoe UI", 8, "bold"), bg=BG_CARD_SUBTLE, fg=TEXT_MUTED).pack(anchor="w", pady=(0, 4))

        def add_step(p, num, title, math_txt, res_txt, res_color):
            row = tk.Frame(p, bg=BG_CARD_SUBTLE)
            row.pack(fill=tk.X, pady=2)
            tk.Label(row, text=str(num), font=("Segoe UI", 7, "bold"), bg=ACCENT_GREEN_BG, fg=ACCENT_GREEN, width=2).pack(side=tk.LEFT, padx=(0, 6))
            tk.Label(row, text=title, font=("Segoe UI", 9, "bold"), bg=BG_CARD_SUBTLE, fg=TEXT_MAIN).pack(side=tk.LEFT, padx=(0, 8))
            m = tk.Label(row, text=math_txt, font=("Segoe UI", 8), bg=BG_CARD_SUBTLE, fg=TEXT_MUTED)
            m.pack(side=tk.LEFT)
            r = tk.Label(row, text=res_txt, font=("Segoe UI", 9, "bold"), bg=BG_CARD_SUBTLE, fg=res_color)
            r.pack(side=tk.RIGHT)
            return m, r

        self.step1_m, self.step1_r = add_step(breakdown, 1, "Count everyone first", "60 enrolled – 50 counted", "= 10 absent", ACCENT_GREEN)
        self.step2_m, self.step2_r = add_step(breakdown, 2, "Name the faces", f"50 counted – {self.identified} identified", f"= {self.unclear_count} still unclear", ACCENT_AMBER)
        self.step3_m, self.step3_r = add_step(breakdown, 3, "Check the names left", f"60 enrolled – {self.identified} identified", f"= {self.enrolled - self.identified} names unaccounted", TEXT_MAIN)

        tk.Label(
            breakdown,
            text="16 unaccounted names = 6 people in the room + 10 absent. Unclear faces are only compared against these 16.",
            font=("Segoe UI", 7), bg=BG_CARD_SUBTLE, fg=TEXT_MUTED
        ).pack(anchor="w", pady=(4, 0))

        # Simulation Buttons (Built-in Rules)
        sim_bar = tk.Frame(left_card, bg=BG_CARD, pady=6)
        sim_bar.pack(fill=tk.X)
        tk.Label(sim_bar, text="Rules Simulation:", font=("Segoe UI", 8, "bold"), bg=BG_CARD, fg=TEXT_MUTED).pack(side=tk.LEFT, padx=(0, 8))
        tk.Button(
            sim_bar, text="⚡ Rule 1: Toggle Count Mismatch (48 vs 50)",
            font=("Segoe UI", 8), bg="#ffffff", bd=1, relief="solid", fg=ACCENT_AMBER,
            command=self.toggle_mismatch_rule
        ).pack(side=tk.LEFT, padx=4)
        tk.Button(
            sim_bar, text="⏰ Rule 2: Last-Minute Arrival (09:21)",
            font=("Segoe UI", 8), bg="#ffffff", bd=1, relief="solid", fg=TEXT_MAIN,
            command=self.simulate_late_arrival
        ).pack(side=tk.LEFT, padx=4)

        # ================= RIGHT: NEEDS REVIEW =================
        right_card = tk.Frame(workspace, bg=BG_CARD, bd=1, relief="solid", highlightbackground=BORDER_COLOR, padx=16, pady=16)
        right_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        # Header with By person / By name
        rh = tk.Frame(right_card, bg=BG_CARD)
        rh.pack(fill=tk.X, pady=(0, 6))
        self.lbl_review_title = tk.Label(rh, text="NEEDS REVIEW · PERSON 2 OF 6", font=("Segoe UI", 9, "bold"), bg=BG_CARD, fg=TEXT_MAIN)
        self.lbl_review_title.pack(side=tk.LEFT)

        toggle_frame = tk.Frame(rh, bg=BG_CARD_SUBTLE, bd=1, relief="solid", highlightbackground=BORDER_COLOR)
        toggle_frame.pack(side=tk.RIGHT)
        self.btn_by_person = tk.Button(toggle_frame, text="By person", font=("Segoe UI", 8, "bold"), bg=TEXT_MAIN, fg="#ffffff", bd=0, relief="flat", padx=8, pady=2, command=lambda: self.set_review_mode("person"))
        self.btn_by_person.pack(side=tk.LEFT)
        self.btn_by_name = tk.Button(toggle_frame, text="By name", font=("Segoe UI", 8), bg=BG_CARD_SUBTLE, fg=TEXT_MUTED, bd=0, relief="flat", padx=8, pady=2, command=lambda: self.set_review_mode("name"))
        self.btn_by_name.pack(side=tk.LEFT)

        # Pager Strip (1 to 6)
        pager_strip = tk.Frame(right_card, bg=BG_CARD)
        pager_strip.pack(fill=tk.X, pady=(2, 6))
        self.pager_btns_frame = tk.Frame(pager_strip, bg=BG_CARD)
        self.pager_btns_frame.pack(side=tk.LEFT)
        tk.Label(pager_strip, text="People leave this list once they are named", font=("Segoe UI", 8), bg=BG_CARD, fg=TEXT_MUTED).pack(side=tk.RIGHT)

        # Crop Photos Carousel
        self.carousel_frame = tk.Frame(right_card, bg="#ffffff", bd=1, relief="solid", highlightbackground=BORDER_COLOR, padx=10, pady=8)
        self.carousel_frame.pack(fill=tk.X, pady=(0, 8))

        self.lbl_carousel_title = tk.Label(self.carousel_frame, text="Photos of this person, 5 from the last 8 minutes", font=("Segoe UI", 8, "bold"), bg="#ffffff", fg=TEXT_MAIN)
        self.lbl_carousel_title.pack(anchor="w", pady=(0, 6))

        self.crops_box = tk.Frame(self.carousel_frame, bg="#ffffff")
        self.crops_box.pack(fill=tk.X)

        # Tracking Callout Box
        self.tracking_callout = tk.Frame(right_card, bg=ACCENT_AMBER_BG, bd=1, relief="solid", highlightbackground="#fae2be", padx=10, pady=6)
        self.tracking_callout.pack(fill=tk.X, pady=(0, 8))
        self.lbl_tracking_lead = tk.Label(self.tracking_callout, text="Still tracking · row 2, seat 3 · followed in 14 of 16 frames", font=("Segoe UI", 8, "bold"), bg=ACCENT_AMBER_BG, fg=ACCENT_AMBER)
        self.lbl_tracking_lead.pack(anchor="w")
        tk.Label(self.tracking_callout, text="The camera keeps following this person and marks them automatically as soon as a face is clear.", font=("Segoe UI", 7), bg=ACCENT_AMBER_BG, fg="#7b4f17").pack(anchor="w")

        # Candidate Names Section
        self.candidates_container = tk.Frame(right_card, bg=BG_CARD)
        self.candidates_container.pack(fill=tk.BOTH, expand=True)

        self.lbl_candidates_head = tk.Label(self.candidates_container, text="POSSIBLE NAMES · FROM THE 16 UNACCOUNTED", font=("Segoe UI", 8, "bold"), bg=BG_CARD, fg=TEXT_MUTED)
        self.lbl_candidates_head.pack(anchor="w", pady=(2, 4))

        self.candidates_list_frame = tk.Frame(self.candidates_container, bg=BG_CARD)
        self.candidates_list_frame.pack(fill=tk.BOTH, expand=True)

        # Bottom Actions
        act_box = tk.Frame(right_card, bg=BG_CARD)
        act_box.pack(fill=tk.X, pady=(6, 0))
        tk.Button(act_box, text="None of these", font=("Segoe UI", 8, "bold"), bg="#ffffff", bd=1, relief="solid", fg=TEXT_MAIN, padx=12, pady=4, command=self.action_none_of_these).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        tk.Button(act_box, text="Skip and keep tracking", font=("Segoe UI", 8, "bold"), bg="#ffffff", bd=1, relief="solid", fg=TEXT_MAIN, padx=12, pady=4, command=self.action_skip_tracking).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0))

        # Bottom Legal Footer
        tk.Label(
            outer,
            text="A weak match is never marked automatically. Only a confident match, or your confirmation, marks a student present. Photos are kept only while a review is open and are deleted when you submit. Every confirmation is logged with your name and time.",
            font=("Segoe UI", 7), bg=BG_APP, fg=TEXT_MUTED, wraplength=1380, justify="left"
        ).pack(fill=tk.X, pady=(12, 0))

        self.render_seating_grid()
        self.render_review_panel()

    # ================= Canvas Drawing: 50-Seat Grid =================
    def render_seating_grid(self):
        self.canvas_grid.delete("all")
        self.canvas_grid.update_idletasks()
        cw = self.canvas_grid.winfo_width() or 640
        ch = self.canvas_grid.winfo_height() or 270

        # Draw "Snapshot 09:08:40"
        self.canvas_grid.create_text(20, 14, text="Snapshot 09:08:40", fill="#7b8895", font=("Consolas", 8), anchor="w")

        # 5 rows x 10 cols
        margin_x = 24
        margin_y = 30
        cell_w = (cw - 2 * margin_x) / 10
        cell_h = (ch - margin_y - 14) / 5

        self.seat_coords = {}

        for r in range(1, 6):
            for c in range(1, 10 + 1):
                x = margin_x + (c - 1) * cell_w
                y = margin_y + (r - 1) * cell_h
                w = cell_w - 6
                h = cell_h - 6

                # Store seat bounding box for click detection
                self.seat_coords[(r, c)] = (x, y, x + w, y + h)

                # Desk outline
                self.canvas_grid.create_rectangle(x, y, x + w, y + h, fill="#232a31", outline="#2e3740", width=1)

                # Check if this seat is an active unclear person
                unclear_person = next((p for p in self.unclear_persons if p["row"] == r and p["col"] == c), None)

                cx = x + w / 2
                cy = y + h / 2
                rad = min(w, h) * 0.30

                if unclear_person:
                    is_active = (self.unclear_persons.index(unclear_person) == self.active_person_idx)
                    ring_color = "#ffffff" if is_active else ACCENT_AMBER_RING
                    self.canvas_grid.create_oval(cx - rad, cy - rad, cx + rad, cy + rad, outline=ring_color, width=2, fill="#382814")
                    # Amber badge number
                    bx = x + w - 7
                    by = y + 7
                    self.canvas_grid.create_oval(bx - 7, by - 7, bx + 7, by + 7, fill=ACCENT_AMBER_RING, outline="")
                    self.canvas_grid.create_text(bx, by, text=str(unclear_person["id"]), fill="#192026", font=("Segoe UI", 7, "bold"))
                else:
                    # Identified seat
                    self.canvas_grid.create_oval(cx - rad, cy - rad, cx + rad, cy + rad, outline=ACCENT_GREEN_RING, width=2, fill="#132e20")
                    self.canvas_grid.create_oval(cx - 2, cy - 2, cx + 2, cy + 2, fill=ACCENT_GREEN_RING, outline="")

    def on_canvas_seat_click(self, event):
        for (r, c), (x1, y1, x2, y2) in self.seat_coords.items():
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                unclear_idx = next((i for i, p in enumerate(self.unclear_persons) if p["row"] == r and p["col"] == c), None)
                if unclear_idx is not None:
                    self.active_person_idx = unclear_idx
                    self.render_seating_grid()
                    self.render_review_panel()
                break

    # ================= Right Review Panel =================
    def render_review_panel(self):
        # 1. Pager Buttons
        for w in self.pager_btns_frame.winfo_children():
            w.destroy()

        if not self.unclear_persons:
            self.lbl_review_title.config(text="ALL UNCLEAR PEOPLE RESOLVED")
            for w in self.crops_box.winfo_children(): w.destroy()
            for w in self.candidates_list_frame.winfo_children(): w.destroy()
            self.lbl_carousel_title.config(text="All 50 students in classroom verified.")
            self.lbl_tracking_lead.config(text="All seated attendees confirmed. Ready to submit.")
            self.update_math_and_kpis()
            return

        if self.active_person_idx >= len(self.unclear_persons):
            self.active_person_idx = 0

        p = self.unclear_persons[self.active_person_idx]
        self.lbl_review_title.config(text=f"NEEDS REVIEW · PERSON {p['id']} OF {len(self.unclear_persons)}")

        for idx, person in enumerate(self.unclear_persons):
            is_active = (idx == self.active_person_idx)
            btn = tk.Button(
                self.pager_btns_frame, text=str(person["id"]), font=("Segoe UI", 8, "bold"),
                bg=ACCENT_AMBER_BG if is_active else "#ffffff",
                fg=ACCENT_AMBER if is_active else TEXT_MAIN,
                bd=1, relief="solid", width=2,
                command=lambda i=idx: self.select_person(i)
            )
            btn.pack(side=tk.LEFT, padx=2)

        # 2. Carousel Crops
        for w in self.crops_box.winfo_children():
            w.destroy()

        self.lbl_carousel_title.config(text=f"Photos of this person, {len(p['crops'])} from the last 8 minutes")
        for time_str, note_str, is_best in p["crops"]:
            col = tk.Frame(self.crops_box, bg="#ffffff", padx=4)
            col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            # Silhouette preview box
            box = tk.Canvas(col, width=54, height=54, bg="#27313a", highlightthickness=2 if is_best else 0, highlightbackground=ACCENT_GREEN)
            box.pack(pady=(0, 2))
            box.create_oval(15, 12, 39, 36, fill="#475569", outline="#64748b")
            box.create_arc(8, 32, 46, 60, start=0, extent=180, fill="#475569", outline="#64748b")

            tk.Label(col, text=time_str, font=("Segoe UI", 7, "bold"), bg="#ffffff", fg=TEXT_MAIN).pack()
            tk.Label(col, text=note_str, font=("Segoe UI", 6), bg="#ffffff", fg=ACCENT_GREEN if is_best else TEXT_MUTED).pack()

        # 3. Tracking Callout
        self.lbl_tracking_lead.config(text=p["tracking"])

        # 4. Candidate Names
        unaccounted = self.enrolled - self.identified
        self.lbl_candidates_head.config(text=f"POSSIBLE NAMES · FROM THE {unaccounted} UNACCOUNTED")

        for w in self.candidates_list_frame.winfo_children():
            w.destroy()

        for sid, name, rating, dots, color in p["candidates"]:
            card = tk.Frame(self.candidates_list_frame, bg="#ffffff", bd=1, relief="solid", highlightbackground=BORDER_COLOR, padx=8, pady=6)
            card.pack(fill=tk.X, pady=2)

            # Avatar Initials
            initials = "".join(part[0] for part in name.split())
            av = tk.Label(card, text=initials, font=("Segoe UI", 8, "bold"), bg=BG_CARD_SUBTLE, fg=TEXT_MAIN, width=3, height=1)
            av.pack(side=tk.LEFT, padx=(0, 8))

            info = tk.Frame(card, bg="#ffffff")
            info.pack(side=tk.LEFT)
            tk.Label(info, text=name, font=("Segoe UI", 9, "bold"), bg="#ffffff", fg=TEXT_MAIN).pack(anchor="w")
            tk.Label(info, text=f"{sid} · ID photo on file", font=("Segoe UI", 7), bg="#ffffff", fg=TEXT_MUTED).pack(anchor="w")

            btn = tk.Button(
                card, text="This is them", font=("Segoe UI", 8, "bold"),
                bg=TEXT_MAIN, fg="#ffffff", bd=0, relief="flat", padx=10, pady=3, cursor="hand2",
                command=lambda s=sid, n=name: self.confirm_student(s, n)
            )
            btn.pack(side=tk.RIGHT)

            rating_box = tk.Frame(card, bg="#ffffff")
            rating_box.pack(side=tk.RIGHT, padx=12)
            tk.Label(rating_box, text=f"{dots} {rating}", font=("Segoe UI", 8, "bold"), bg="#ffffff", fg=color).pack()

        self.update_math_and_kpis()

    def select_person(self, idx):
        self.active_person_idx = idx
        self.render_seating_grid()
        self.render_review_panel()

    def confirm_student(self, sid, name):
        # Update counts
        self.identified += 1
        self.unclear_count -= 1

        # Remove confirmed person from unclear list
        self.unclear_persons.pop(self.active_person_idx)

        if self.active_person_idx >= len(self.unclear_persons):
            self.active_person_idx = 0

        self.render_seating_grid()
        self.render_review_panel()
        self.update_math_and_kpis()

    def action_none_of_these(self):
        messagebox.showinfo("Marked", "Student marked as unknown/unregistered attendee.", parent=self)
        if self.unclear_persons:
            self.active_person_idx = (self.active_person_idx + 1) % len(self.unclear_persons)
            self.render_seating_grid()
            self.render_review_panel()

    def action_skip_tracking(self):
        if self.unclear_persons:
            self.active_person_idx = (self.active_person_idx + 1) % len(self.unclear_persons)
            self.render_seating_grid()
            self.render_review_panel()

    def set_review_mode(self, mode):
        self.review_mode = mode
        if mode == "person":
            self.btn_by_person.configure(bg=TEXT_MAIN, fg="#ffffff")
            self.btn_by_name.configure(bg=BG_CARD_SUBTLE, fg=TEXT_MUTED)
        else:
            self.btn_by_person.configure(bg=BG_CARD_SUBTLE, fg=TEXT_MUTED)
            self.btn_by_name.configure(bg=TEXT_MAIN, fg="#ffffff")
            messagebox.showinfo("By Name View", "Switching to candidate-first review mode.", parent=self)

    def toggle_mismatch_rule(self):
        self.mismatch_active = not self.mismatch_active
        if self.mismatch_active:
            try:
                self.banner_frame.pack(fill=tk.X, pady=(0, 10), before=self.canvas_grid.master.master)
            except Exception:
                self.banner_frame.pack(fill=tk.X, pady=(0, 10), side=tk.TOP)
        else:
            self.banner_frame.pack_forget()

    def simulate_late_arrival(self):
        messagebox.showinfo(
            "Rule 2 Triggered",
            "Rule 2: Last-Minute Arrival Detected!\n\n"
            "Student: Sudeep Singh Dhami (2333438)\n"
            "Arrival Time: 09:21 (11 mins after session start)\n"
            "Action: Automatically tagged as 'Late' (not absent). Arrival snapshot logged.",
            parent=self
        )

    def update_math_and_kpis(self):
        unaccounted = self.enrolled - self.identified

        self.kpi_enrolled_lbl.config(text=str(self.enrolled))
        self.kpi_counted_lbl.config(text=str(self.counted))
        self.kpi_identified_lbl.config(text=str(self.identified))
        self.kpi_unclear_lbl.config(text=str(self.unclear_count))
        self.kpi_absent_lbl.config(text=str(self.absent))

        self.step2_m.config(text=f"50 counted – {self.identified} identified")
        self.step2_r.config(text=f"= {self.unclear_count} still unclear")

        self.step3_m.config(text=f"60 enrolled – {self.identified} identified")
        self.step3_r.config(text=f"= {unaccounted} names unaccounted")

        self.lbl_session_sub.config(text=f"Block B, Lab 3 · Fri 23 Oct 2026 · 09:00 – 10:00 · Still tracking {self.unclear_count} people")

        if self.unclear_count == 0:
            self.btn_submit.config(state=tk.NORMAL, bg=ACCENT_GREEN, fg="#ffffff")
            self.lbl_submit_hint.config(text="Ready to submit", fg=ACCENT_GREEN)
            self.btn_submit.config(command=lambda: messagebox.showinfo("Submitted", "Attendance submitted successfully!\n44 + 6 = 50 Present\n10 Absent", parent=self))
        else:
            self.btn_submit.config(state=tk.DISABLED, bg="#e5e3dc", fg=TEXT_DIM)
            self.lbl_submit_hint.config(text=f"Resolve {self.unclear_count} to submit", fg=TEXT_MUTED)

    # ================= 4. STUDENT VIEW (student_portal.png) =================
    def _build_student_view(self, parent):
        outer = tk.Frame(parent, bg=BG_APP, padx=32, pady=20)
        outer.pack(fill=tk.BOTH, expand=True)

        # Header
        h = tk.Frame(outer, bg=BG_APP)
        h.pack(fill=tk.X, pady=(0, 16))
        left = tk.Frame(h, bg=BG_APP)
        left.pack(side=tk.LEFT)
        tk.Label(left, text="My attendance", font=("Segoe UI", 20, "bold"), bg=BG_APP, fg=TEXT_MAIN).pack(anchor="w")
        tk.Label(left, text="Autumn term 2026 · You need at least 75% in every course to sit the exam", font=("Segoe UI", 10), bg=BG_APP, fg=TEXT_MUTED).pack(anchor="w")

        right = tk.Frame(h, bg=BG_APP)
        right.pack(side=tk.RIGHT)
        tk.Label(right, text="81%", font=("Segoe UI", 32, "bold"), bg=BG_APP, fg=ACCENT_GREEN).pack(side=tk.LEFT, padx=(0, 8))
        tk.Label(right, text="Overall\n87 of 107 sessions", font=("Segoe UI", 9), bg=BG_APP, fg=TEXT_MUTED).pack(side=tk.LEFT)

        # Grid
        grid = tk.Frame(outer, bg=BG_APP)
        grid.pack(fill=tk.BOTH, expand=True)
        grid.columnconfigure(0, weight=6)
        grid.columnconfigure(1, weight=4)

        # Left Courses Table
        c_card = tk.Frame(grid, bg=BG_CARD, bd=1, relief="solid", highlightbackground=BORDER_COLOR, padx=16, pady=16)
        c_card.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        tk.Label(c_card, text="COURSES", font=("Segoe UI", 9, "bold"), bg=BG_CARD, fg=TEXT_MUTED).pack(anchor="w", pady=(0, 8))

        courses = [
            ("Data Structures", "CS-2104 · Dr. M. Iyer", "24 / 28", "86%", "Can miss 6 more sessions", ACCENT_GREEN),
            ("Discrete Mathematics", "MA-2101 · Dr. K. Verma", "21 / 26", "81%", "Can miss 5 more sessions", ACCENT_GREEN),
            ("Computer Organisation", "CS-2106 · Dr. A. Rao", "19 / 27", "70%", "Below 75% · can miss only 2 more", ACCENT_AMBER),
            ("Technical Writing", "HS-2102 · Ms. T. Gurung", "14 / 14", "100%", "Can miss 5 more sessions", ACCENT_GREEN),
            ("Data Structures Lab", "CS-2108 · Mr. P. Singh", "9 / 12", "75%", "Right on 75% · can miss 1 more", ACCENT_AMBER),
        ]
        for cname, prof, att, pct, note, col in courses:
            row = tk.Frame(c_card, bg=BG_CARD, pady=6)
            row.pack(fill=tk.X)
            cinfo = tk.Frame(row, bg=BG_CARD, width=160)
            cinfo.pack(side=tk.LEFT)
            tk.Label(cinfo, text=cname, font=("Segoe UI", 9, "bold"), bg=BG_CARD, fg=TEXT_MAIN).pack(anchor="w")
            tk.Label(cinfo, text=prof, font=("Segoe UI", 7), bg=BG_CARD, fg=TEXT_MUTED).pack(anchor="w")

            tk.Label(row, text=att, font=("Segoe UI", 9), bg=BG_CARD, fg=TEXT_MAIN, width=8).pack(side=tk.LEFT)
            tk.Label(row, text=pct, font=("Segoe UI", 9, "bold"), bg=BG_CARD, fg=col, width=6).pack(side=tk.LEFT)
            tk.Label(row, text=note, font=("Segoe UI", 8), bg=BG_CARD, fg=col).pack(side=tk.RIGHT)

        # Right Sessions Log
        s_card = tk.Frame(grid, bg=BG_CARD, bd=1, relief="solid", highlightbackground=BORDER_COLOR, padx=16, pady=16)
        s_card.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
        tk.Label(s_card, text="RECENT SESSIONS", font=("Segoe UI", 9, "bold"), bg=BG_CARD, fg=TEXT_MUTED).pack(anchor="w", pady=(0, 8))

        sessions = [
            ("Fri 23 Oct", "CS-2104", "Present", "Camera", ACCENT_GREEN),
            ("Thu 22 Oct", "CS-2108", "Present", "Camera", ACCENT_GREEN),
            ("Thu 22 Oct", "MA-2101", "Present", "Camera", ACCENT_GREEN),
            ("Wed 21 Oct", "CS-2106", "Absent", "Not detected", ACCENT_ROSE),
            ("Wed 21 Oct", "HS-2102", "Present", "Camera", ACCENT_GREEN),
            ("Tue 20 Oct", "CS-2104", "Late", "Camera, 09:21", ACCENT_AMBER),
        ]
        for dt, code, st, src, col in sessions:
            r = tk.Frame(s_card, bg=BG_CARD, pady=4)
            r.pack(fill=tk.X)
            tk.Label(r, text=dt, font=("Segoe UI", 8), bg=BG_CARD, fg=TEXT_MAIN, width=10).pack(side=tk.LEFT)
            tk.Label(r, text=code, font=("Segoe UI", 8, "bold"), bg=BG_CARD, fg=TEXT_MAIN, width=8).pack(side=tk.LEFT)
            tk.Label(r, text=st, font=("Segoe UI", 8, "bold"), bg=BG_CARD, fg=col, width=8).pack(side=tk.LEFT)
            tk.Label(r, text=src, font=("Segoe UI", 7), bg=BG_CARD, fg=TEXT_MUTED).pack(side=tk.RIGHT)

    # ================= 5. DEPARTMENT VIEW (dept_view.png) =================
    def _build_dept_view(self, parent):
        outer = tk.Frame(parent, bg=BG_APP, padx=32, pady=20)
        outer.pack(fill=tk.BOTH, expand=True)

        h = tk.Frame(outer, bg=BG_APP)
        h.pack(fill=tk.X, pady=(0, 16))
        tk.Label(h, text="Section CS-3A · Today", font=("Segoe UI", 20, "bold"), bg=BG_APP, fg=TEXT_MAIN).pack(side=tk.LEFT)

        kpis = tk.Frame(h, bg=BG_APP)
        kpis.pack(side=tk.RIGHT)
        for val, lbl, col in [("3", "Submitted", ACCENT_GREEN), ("1", "Waiting", ACCENT_AMBER), ("1", "Upcoming", TEXT_MAIN), ("1", "Camera offline", ACCENT_ROSE)]:
            b = tk.Frame(kpis, bg=BG_APP, padx=10)
            b.pack(side=tk.LEFT)
            tk.Label(b, text=val, font=("Segoe UI", 16, "bold"), bg=BG_APP, fg=col).pack()
            tk.Label(b, text=lbl, font=("Segoe UI", 7), bg=BG_APP, fg=TEXT_MUTED).pack()

        card = tk.Frame(outer, bg=BG_CARD, bd=1, relief="solid", highlightbackground=BORDER_COLOR, padx=16, pady=16)
        card.pack(fill=tk.BOTH, expand=True)
        tk.Label(card, text="TODAY'S SESSIONS", font=("Segoe UI", 9, "bold"), bg=BG_CARD, fg=TEXT_MUTED).pack(anchor="w", pady=(0, 8))

        sched = [
            ("09:00", "CS-2104 Data Structures", "B-Lab 3", "Dr. M. Iyer", "Submitted · 52 of 58", ACCENT_GREEN),
            ("10:00", "MA-2101 Discrete Maths", "B-204", "Dr. K. Verma", "Roll call (camera offline)", ACCENT_AMBER),
            ("11:15", "CS-2106 Computer Org.", "B-105", "Dr. A. Rao", "Waiting · 3 to review", ACCENT_AMBER),
            ("12:15", "HS-2102 Technical Writing", "A-301", "Ms. T. Gurung", "Submitted · 55 of 58", ACCENT_GREEN),
            ("14:00", "CS-2108 DS Lab", "B-Lab 2", "Mr. P. Singh", "Not started", TEXT_DIM),
        ]
        for tm, crs, rm, inst, st, col in sched:
            r = tk.Frame(card, bg=BG_CARD, pady=6)
            r.pack(fill=tk.X)
            tk.Label(r, text=tm, font=("Segoe UI", 8), bg=BG_CARD, fg=TEXT_MAIN, width=8).pack(side=tk.LEFT)
            tk.Label(r, text=crs, font=("Segoe UI", 9, "bold"), bg=BG_CARD, fg=TEXT_MAIN, width=24).pack(side=tk.LEFT)
            tk.Label(r, text=rm, font=("Segoe UI", 8), bg=BG_CARD, fg=TEXT_MUTED, width=10).pack(side=tk.LEFT)
            tk.Label(r, text=inst, font=("Segoe UI", 8), bg=BG_CARD, fg=TEXT_MAIN, width=16).pack(side=tk.LEFT)
            tk.Label(r, text=st, font=("Segoe UI", 8, "bold"), bg=BG_CARD, fg=col).pack(side=tk.RIGHT)

    # ================= 6. SETTINGS VIEW (settings_rules.png) =================
    def _build_settings_view(self, parent):
        outer = tk.Frame(parent, bg=BG_APP, padx=32, pady=20)
        outer.pack(fill=tk.BOTH, expand=True)

        tk.Label(outer, text="Enrolment and rules", font=("Segoe UI", 20, "bold"), bg=BG_APP, fg=TEXT_MAIN).pack(anchor="w")
        tk.Label(outer, text="School of Computing & Engineering · changes apply from next session", font=("Segoe UI", 9), bg=BG_APP, fg=TEXT_MUTED).pack(anchor="w", pady=(0, 16))

        grid = tk.Frame(outer, bg=BG_APP)
        grid.pack(fill=tk.BOTH, expand=True)
        grid.columnconfigure((0, 1), weight=1)

        # Enrolment
        card_l = tk.Frame(grid, bg=BG_CARD, bd=1, relief="solid", highlightbackground=BORDER_COLOR, padx=16, pady=16)
        card_l.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        tk.Label(card_l, text="FACE ENROLMENT · SECTION CS-3A", font=("Segoe UI", 9, "bold"), bg=BG_CARD, fg=TEXT_MUTED).pack(anchor="w")
        tk.Label(card_l, text="53 of 58 enrolled", font=("Segoe UI", 18, "bold"), bg=BG_CARD, fg=ACCENT_GREEN).pack(anchor="w")
        tk.Label(card_l, text="2 pending · 2 opted out · 1 needs a new photo", font=("Segoe UI", 8), bg=BG_CARD, fg=TEXT_MUTED).pack(anchor="w", pady=(0, 10))

        enrols = [
            ("22CS1007", "Anjali Gurung", "Enrolled", ACCENT_GREEN),
            ("22CS1012", "Bikram Thapa", "Pending photo", ACCENT_AMBER),
            ("22CS1029", "Imran Sheikh", "Needs new photo", ACCENT_AMBER),
            ("22CS1033", "Kavya Reddy", "Opted out", TEXT_DIM),
            ("22CS1038", "Karan Mehta", "Enrolled", ACCENT_GREEN),
            ("22CS1044", "Simran Kaur", "Enrolled", ACCENT_GREEN),
            ("22CS1047", "Aarav Sharma", "Enrolled", ACCENT_GREEN),
        ]
        for sid, name, st, col in enrols:
            r = tk.Frame(card_l, bg=BG_CARD, pady=4)
            r.pack(fill=tk.X)
            tk.Label(r, text=sid, font=("Segoe UI", 8), bg=BG_CARD, fg=TEXT_MAIN, width=12).pack(side=tk.LEFT)
            tk.Label(r, text=name, font=("Segoe UI", 8, "bold"), bg=BG_CARD, fg=TEXT_MAIN, width=18).pack(side=tk.LEFT)
            tk.Label(r, text=st, font=("Segoe UI", 8, "bold"), bg=BG_CARD, fg=col).pack(side=tk.RIGHT)

        # Rules
        card_r = tk.Frame(grid, bg=BG_CARD, bd=1, relief="solid", highlightbackground=BORDER_COLOR, padx=16, pady=16)
        card_r.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        tk.Label(card_r, text="MATCHING AND MARKING RULES", font=("Segoe UI", 9, "bold"), bg=BG_CARD, fg=TEXT_MUTED).pack(anchor="w", pady=(0, 8))

        rules = [
            ("Snapshots per session", "6, about 2 minutes apart"),
            ("Marked present when", "matched in at least 2 snapshots"),
            ("Counted as late after", "10 minutes"),
            ("Counted as absent after", "30 minutes"),
            ("Weak matches", "always sent to the instructor")
        ]
        for k, v in rules:
            r = tk.Frame(card_r, bg=BG_CARD, pady=4)
            r.pack(fill=tk.X)
            tk.Label(r, text=k, font=("Segoe UI", 8), bg=BG_CARD, fg=TEXT_MUTED).pack(side=tk.LEFT)
            tk.Label(r, text=v, font=("Segoe UI", 8, "bold"), bg=BG_CARD, fg=TEXT_MAIN).pack(side=tk.RIGHT)

        tk.Label(
            card_r,
            text="A weak match is never marked automatically, so one wrong face never changes someone's record.",
            font=("Segoe UI", 7), bg=BG_CARD, fg=TEXT_MUTED, wraplength=480, justify="left"
        ).pack(anchor="w", pady=(12, 0))

def main():
    app = NorthfieldDesktopApp()
    app.mainloop()

if __name__ == "__main__":
    main()
