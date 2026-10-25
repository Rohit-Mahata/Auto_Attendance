import time
from datetime import datetime
from tkinter import *
from tkinter import ttk, messagebox

from ui.theme import *
from ui.views.live_monitor import LiveMonitorView
from ui.views.students_view import StudentsView
from ui.views.attendance_view import AttendanceView
from ui.views.ai_settings_view import AISettingsView
from ui.views.cctv_settings_view import CCTVSettingsView

class MainWindow(Tk):
    """
    Unified Single-Window Desktop Application Shell for Classroom Face Recognition.
    Eliminates multi-window clutter by hosting all navigation views inside a single workspace.
    """
    def __init__(self):
        super().__init__()
        self.title("CLASSEYE AI — Intelligent Classroom Face Recognition Attendance System")
        self.geometry("1480x880+40+20")
        self.minsize(1200, 720)
        self.configure(bg=BG_DARK)

        self.current_tab = None
        self.nav_buttons = {}

        # Shared Deep Learning AI Engines (loaded once in memory)
        from ai_pipeline.face_detector import FaceDetector
        from ai_pipeline.face_recognizer import FaceRecognizer
        self.detector = FaceDetector()
        self.recognizer = FaceRecognizer()

        self._build_shell()
        self._start_clock()

        # Bring window to foreground on user desktop
        self.lift()
        self.attributes('-topmost', True)
        self.after_idle(self.attributes, '-topmost', False)
        self.focus_force()

    def _build_shell(self):
        # Master grid: row 0 = Header, row 1 = Content (Sidebar + Main Area)
        self.rowconfigure(0, weight=0)
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

        # ================= 1. Top Global Header =================
        header = Frame(self, bg=BG_SURFACE, height=64, padx=20, pady=10)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(1, weight=1)

        # Brand / Title
        brand_frame = Frame(header, bg=BG_SURFACE)
        brand_frame.pack(side=LEFT)

        Label(
            brand_frame,
            text="🎓 CLASSEYE AI",
            font=("Segoe UI", 16, "bold"),
            bg=BG_SURFACE,
            fg=ACCENT_BLUE
        ).pack(side=LEFT)

        Label(
            brand_frame,
            text=" |  Classroom Attendance & Surveillance Intelligence",
            font=FONT_BODY,
            bg=BG_SURFACE,
            fg=TEXT_MUTED
        ).pack(side=LEFT, padx=(4, 0))

        # Status & Clock on Right
        status_frame = Frame(header, bg=BG_SURFACE)
        status_frame.pack(side=RIGHT)

        self.lbl_clock = Label(
            status_frame,
            text="",
            font=FONT_MONO,
            bg=BG_SURFACE,
            fg=TEXT_MUTED
        )
        self.lbl_clock.pack(side=LEFT, padx=(0, 16))

        pill = Frame(status_frame, bg="#064e3b", padx=10, pady=4)
        pill.pack(side=RIGHT)
        Label(
            pill,
            text="● SYSTEM READY",
            font=("Segoe UI", 9, "bold"),
            bg="#064e3b",
            fg="#34d399"
        ).pack()

        # Separator line
        sep = Frame(self, bg=BORDER_COLOR, height=1)
        sep.grid(row=0, column=0, sticky="sew")

        # ================= 2. Workspace Container =================
        workspace = Frame(self, bg=BG_DARK)
        workspace.grid(row=1, column=0, sticky="nsew")
        workspace.rowconfigure(0, weight=1)
        workspace.columnconfigure(0, weight=0)  # Sidebar fixed
        workspace.columnconfigure(1, weight=1)  # Views dynamic

        # Sidebar Navigation
        sidebar = Frame(workspace, bg=BG_SURFACE, width=240, padx=12, pady=16)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.columnconfigure(0, weight=1)

        Label(
            sidebar,
            text="NAVIGATION",
            font=("Segoe UI", 8, "bold"),
            bg=BG_SURFACE,
            fg=TEXT_DIM
        ).pack(anchor="w", padx=12, pady=(4, 12))

        # Navigation Tabs
        nav_items = [
            ("live", "📹  Live Monitor", LiveMonitorView),
            ("students", "👥  Student Registry", StudentsView),
            ("attendance", "📊  Attendance Logs", AttendanceView),
            ("ai_settings", "🧠  AI Calibration", AISettingsView),
            ("cctv_settings", "⚙️  CCTV & System", CCTVSettingsView),
        ]

        # Content Views Dictionary
        self.content_container = Frame(workspace, bg=BG_DARK)
        self.content_container.grid(row=0, column=1, sticky="nsew")
        self.content_container.rowconfigure(0, weight=1)
        self.content_container.columnconfigure(0, weight=1)

        self.views = {}
        for tab_id, label, view_class in nav_items:
            # Instantiate view inside single content container
            view_instance = view_class(self.content_container, self)
            view_instance.grid(row=0, column=0, sticky="nsew")
            self.views[tab_id] = view_instance

            # Create Sidebar Button
            btn = Button(
                sidebar,
                text=label,
                font=FONT_BODY_BOLD,
                anchor="w",
                padx=16,
                pady=10,
                bd=0,
                relief="flat",
                cursor="hand2",
                command=lambda tid=tab_id: self.switch_tab(tid)
            )
            btn.pack(fill=X, pady=3)
            self.nav_buttons[tab_id] = btn

        # Sidebar Footer
        footer_card = Frame(sidebar, bg=BG_CARD, padx=10, pady=10)
        footer_card.pack(side=BOTTOM, fill=X, pady=(16, 0))

        Label(
            footer_card,
            text="⚡ OpenCV Deep Learning",
            font=("Segoe UI", 9, "bold"),
            bg=BG_CARD,
            fg=ACCENT_BLUE
        ).pack(anchor="w")

        Label(
            footer_card,
            text="YuNet + SFace 128D\nv2.0 Production Arch",
            font=FONT_SMALL,
            bg=BG_CARD,
            fg=TEXT_MUTED
        ).pack(anchor="w", pady=(2, 0))

        # Activate default view
        self.switch_tab("live")

    def switch_tab(self, tab_id):
        if self.current_tab == tab_id:
            return

        # If switching away from live monitor, ensure we don't block
        target_view = self.views.get(tab_id)
        if not target_view:
            return

        # Raise active view to front
        target_view.tkraise()
        self.current_tab = tab_id

        # Refresh table data if switching to students or attendance
        if tab_id == "students" and hasattr(target_view, "load_students_table"):
            target_view.load_students_table()
        elif tab_id == "attendance" and hasattr(target_view, "refresh_records"):
            target_view.refresh_records()
        elif tab_id == "live" and hasattr(target_view, "reload_student_cache"):
            target_view.reload_student_cache()

        # Update sidebar active styling
        for tid, btn in self.nav_buttons.items():
            if tid == tab_id:
                btn.configure(
                    bg=BG_CARD,
                    fg=ACCENT_BLUE,
                    activebackground=BG_CARD,
                    activeforeground=ACCENT_BLUE
                )
            else:
                btn.configure(
                    bg=BG_SURFACE,
                    fg=TEXT_MUTED,
                    activebackground=BG_CARD_HOVER,
                    activeforeground=TEXT_MAIN
                )

    def _start_clock(self):
        def tick():
            now_str = datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
            self.lbl_clock.config(text=now_str)
            self.after(1000, tick)
        tick()

    def on_closing(self):
        # Stop camera streams cleanly
        live_view = self.views.get("live")
        if live_view and hasattr(live_view, "stop_stream"):
            live_view.stop_stream()
        self.destroy()
