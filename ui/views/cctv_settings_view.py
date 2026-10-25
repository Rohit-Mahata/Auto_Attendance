import os
from tkinter import *
from tkinter import messagebox
from ui.theme import *
from db_engine import db
from cctv_stream import is_host_reachable
from config import DB_PATH, EMBEDDINGS_PATH, MODELS_DIR

class CCTVSettingsView(Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=BG_DARK)
        self.controller = controller
        self._build_layout()

    def _build_layout(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        container = Frame(self, bg=BG_DARK, padx=24, pady=24)
        container.grid(row=0, column=0, sticky="nsew")
        container.columnconfigure((0, 1), weight=1)

        # ================= LEFT: Camera Configuration =================
        card_cam = Frame(container, bg=BG_SURFACE, padx=20, pady=20)
        card_cam.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        Label(
            card_cam,
            text="📹 Classroom CCTV Stream Configuration",
            font=FONT_SUBTITLE,
            bg=BG_SURFACE,
            fg=ACCENT_BLUE
        ).pack(anchor="w", pady=(0, 16))

        # Classroom Name
        Label(card_cam, text="Classroom Identifier", font=FONT_BODY_BOLD, bg=BG_SURFACE, fg=TEXT_MAIN).pack(anchor="w", pady=(4, 2))
        self.var_classroom = StringVar(value=db.get_setting("classroom_name", "Classroom-A1"))
        entry_cr = Entry(card_cam, textvariable=self.var_classroom, bg=BG_CARD, fg=TEXT_MAIN, font=FONT_BODY, relief="flat")
        entry_cr.pack(fill=X, pady=(0, 12), ipady=3)

        # Camera Source / RTSP URL
        Label(card_cam, text="Default Camera Source (RTSP URL / Webcam Index)", font=FONT_BODY_BOLD, bg=BG_SURFACE, fg=TEXT_MAIN).pack(anchor="w", pady=(4, 2))
        Label(card_cam, text="e.g., '0' (Webcam) or 'rtsp://admin:pass@192.168.1.50:554/stream1'", font=FONT_SMALL, bg=BG_SURFACE, fg=TEXT_MUTED).pack(anchor="w")
        self.var_source = StringVar(value=db.get_setting("default_camera", "0"))
        entry_src = Entry(card_cam, textvariable=self.var_source, bg=BG_CARD, fg=TEXT_MAIN, font=FONT_BODY, relief="flat")
        entry_src.pack(fill=X, pady=(2, 12), ipady=3)

        # Test Connectivity Button
        btn_test = Button(card_cam, text="⚡ Test Camera Connection", command=self.test_connection)
        style_button(btn_test, variant="secondary")
        btn_test.pack(fill=X, pady=(4, 16))

        # Save Settings Button
        btn_save = Button(card_cam, text="💾 Save Camera Settings", command=self.save_settings)
        style_button(btn_save, variant="primary")
        btn_save.pack(fill=X)

        # ================= RIGHT: System Diagnostics =================
        card_diag = Frame(container, bg=BG_SURFACE, padx=20, pady=20)
        card_diag.grid(row=0, column=1, sticky="nsew", padx=(12, 0))

        Label(
            card_diag,
            text="⚙️ System & Biometrics Diagnostics",
            font=FONT_SUBTITLE,
            bg=BG_SURFACE,
            fg=TEXT_MAIN
        ).pack(anchor="w", pady=(0, 16))

        students_count = len(db.get_all_students())
        attendance_count = len(db.get_attendance_logs())
        db_size_kb = round(os.path.getsize(str(DB_PATH)) / 1024, 1) if DB_PATH.exists() else 0

        diag_items = [
            ("Database Engine", f"SQLite 3 ({DB_PATH.name})"),
            ("Database Size", f"{db_size_kb} KB"),
            ("Enrolled Students", f"{students_count} Students"),
            ("Logged Attendance Events", f"{attendance_count} Records"),
            ("Biometric Vectors File", str(EMBEDDINGS_PATH.name)),
            ("Deep Learning Models Path", str(MODELS_DIR.name)),
        ]

        for title, val in diag_items:
            f = Frame(card_diag, bg=BG_CARD, padx=12, pady=10)
            f.pack(fill=X, pady=4)
            Label(f, text=title, font=FONT_BODY_BOLD, bg=BG_CARD, fg=TEXT_MAIN).pack(anchor="w")
            Label(f, text=val, font=FONT_SMALL, bg=BG_CARD, fg=ACCENT_BLUE).pack(anchor="w", pady=(2, 0))

    def test_connection(self):
        src = self.var_source.get().strip()
        if src.isdigit():
            messagebox.showinfo("Camera Test", f"Local webcam index {src} is configured.", parent=self)
            return

        reachable = is_host_reachable(src, timeout=2.0)
        if reachable:
            messagebox.showinfo("Connectivity Success", f"Network camera endpoint is online and reachable:\n{src}", parent=self)
        else:
            messagebox.showwarning("Connection Failed", f"Could not reach network camera host at:\n{src}\nPlease check IP, port, and network route.", parent=self)

    def save_settings(self):
        cr = self.var_classroom.get().strip()
        cam = self.var_source.get().strip()
        db.set_setting("classroom_name", cr)
        db.set_setting("default_camera", cam)
        messagebox.showinfo("Saved", "CCTV and classroom settings updated successfully.", parent=self)
