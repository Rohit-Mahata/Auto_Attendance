import time
from datetime import datetime
from tkinter import *
from tkinter import ttk, messagebox
import cv2
import numpy as np
from PIL import Image, ImageTk

from ui.theme import *
from db_engine import db
from cctv_stream import ThreadedCCTVStream
from ai_pipeline.face_detector import FaceDetector
from ai_pipeline.face_recognizer import FaceRecognizer
from ai_pipeline.classroom_tracker import ClassroomTracker

class LiveMonitorView(Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=BG_DARK)
        self.controller = controller

        # Core Engines (shared from controller or initialized)
        self.detector = getattr(controller, "detector", None) or FaceDetector()
        self.recognizer = getattr(controller, "recognizer", None) or FaceRecognizer()
        self.tracker = ClassroomTracker()
        self.stream = None
        self.is_running = False

        # Session State
        self.session_marked = set()
        self.students_cache = {}
        self.reload_student_cache()

        self._build_layout()

    def reload_student_cache(self):
        students = db.get_all_students()
        self.students_cache = {s["student_id"]: s for s in students}
        self.recognizer.load_enrolled_embeddings()

    def _build_layout(self):
        # 2-column layout: Left (Video Canvas & Controls), Right (Live Stats & Feed)
        self.columnconfigure(0, weight=3)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        # ================= LEFT: Video Feed Panel =================
        left_panel = Frame(self, bg=BG_DARK, padx=16, pady=16)
        left_panel.grid(row=0, column=0, sticky="nsew")
        left_panel.rowconfigure(1, weight=1)
        left_panel.columnconfigure(0, weight=1)

        # Top Control Strip
        ctrl_frame = Frame(left_panel, bg=BG_SURFACE, padx=12, pady=10, relief="flat")
        ctrl_frame.grid(row=0, column=0, sticky="ew", pady=(0, 12))

        Label(
            ctrl_frame,
            text="🎥 Source:",
            font=FONT_BODY_BOLD,
            bg=BG_SURFACE,
            fg=TEXT_MAIN
        ).pack(side=LEFT, padx=(0, 8))

        self.var_camera_src = StringVar(value=db.get_setting("default_camera", "0"))
        self.entry_cam = Entry(
            ctrl_frame,
            textvariable=self.var_camera_src,
            width=28,
            bg=BG_CARD,
            fg=TEXT_MAIN,
            insertbackground=TEXT_MAIN,
            font=FONT_BODY,
            relief="flat"
        )
        self.entry_cam.pack(side=LEFT, padx=(0, 12), ipady=3)

        self.btn_start = Button(ctrl_frame, text="▶ Start Stream", command=self.start_stream)
        style_button(self.btn_start, variant="success")
        self.btn_start.pack(side=LEFT, padx=4)

        self.btn_stop = Button(ctrl_frame, text="⏹ Stop", command=self.stop_stream, state=DISABLED)
        style_button(self.btn_stop, variant="danger")
        self.btn_stop.pack(side=LEFT, padx=4)

        self.lbl_stream_status = Label(
            ctrl_frame,
            text="● Offline",
            font=FONT_BODY_BOLD,
            bg=BG_SURFACE,
            fg=TEXT_MUTED
        )
        self.lbl_stream_status.pack(side=RIGHT, padx=8)

        # Video Canvas Container
        canvas_card = Frame(left_panel, bg=BG_SURFACE, padx=2, pady=2, relief="flat")
        canvas_card.grid(row=1, column=0, sticky="nsew")
        canvas_card.rowconfigure(0, weight=1)
        canvas_card.columnconfigure(0, weight=1)

        self.canvas = Canvas(canvas_card, bg="#050811", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        # Bottom HUD Info
        hud_bar = Frame(left_panel, bg=BG_SURFACE, padx=12, pady=8)
        hud_bar.grid(row=2, column=0, sticky="ew", pady=(12, 0))

        self.lbl_fps = Label(hud_bar, text="FPS: 0.0", font=FONT_SMALL, bg=BG_SURFACE, fg=TEXT_MUTED)
        self.lbl_fps.pack(side=LEFT, padx=8)

        self.lbl_classroom = Label(
            hud_bar,
            text=f"Classroom: {db.get_setting('classroom_name', 'Classroom-A1')}",
            font=FONT_SMALL,
            bg=BG_SURFACE,
            fg=ACCENT_BLUE
        )
        self.lbl_classroom.pack(side=LEFT, padx=16)

        # ================= RIGHT: Analytics & Real-Time Log =================
        right_panel = Frame(self, bg=BG_SURFACE, padx=16, pady=16)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(0, 16), pady=16)
        right_panel.rowconfigure(2, weight=1)
        right_panel.columnconfigure(0, weight=1)

        Label(
            right_panel,
            text="Classroom Telemetry",
            font=FONT_SUBTITLE,
            bg=BG_SURFACE,
            fg=TEXT_MAIN
        ).grid(row=0, column=0, sticky="w", pady=(0, 12))

        # 3 KPI Stat Badges in a grid
        stats_frame = Frame(right_panel, bg=BG_SURFACE)
        stats_frame.grid(row=1, column=0, sticky="ew", pady=(0, 16))
        stats_frame.columnconfigure((0, 1, 2), weight=1)

        self.badge_detected = self._create_kpi_card(stats_frame, 0, "Detected", "0", ACCENT_BLUE)
        self.badge_verified = self._create_kpi_card(stats_frame, 1, "Verified", "0", ACCENT_EMERALD)
        self.badge_unknown = self._create_kpi_card(stats_frame, 2, "Unknown", "0", ACCENT_ROSE)

        # Real-time Attendance Feed List
        Label(
            right_panel,
            text="📋 Live Attendance Log",
            font=FONT_BODY_BOLD,
            bg=BG_SURFACE,
            fg=TEXT_MAIN
        ).grid(row=2, column=0, sticky="nw", pady=(4, 6))

        feed_container = Frame(right_panel, bg=BG_CARD)
        feed_container.grid(row=3, column=0, sticky="nsew")
        right_panel.rowconfigure(3, weight=1)

        self.feed_list = Listbox(
            feed_container,
            bg=BG_CARD,
            fg=TEXT_MAIN,
            selectbackground=BG_CARD_HOVER,
            font=FONT_SMALL,
            bd=0,
            highlightthickness=0
        )
        scrollbar = Scrollbar(feed_container, orient=VERTICAL, command=self.feed_list.yview)
        self.feed_list.configure(yscrollcommand=scrollbar.set)
        self.feed_list.pack(side=LEFT, fill=BOTH, expand=True, padx=4, pady=4)
        scrollbar.pack(side=RIGHT, fill=Y)

        # Clear session button
        btn_clear = Button(right_panel, text="Clear Session Feed", command=self.clear_feed)
        style_button(btn_clear, variant="secondary")
        btn_clear.grid(row=4, column=0, sticky="ew", pady=(10, 0))

    def _create_kpi_card(self, parent, col, title, value, accent_color):
        card = Frame(parent, bg=BG_CARD, padx=8, pady=8, relief="flat")
        card.grid(row=0, column=col, padx=3, sticky="ew")

        lbl_val = Label(card, text=value, font=("Segoe UI", 16, "bold"), bg=BG_CARD, fg=accent_color)
        lbl_val.pack()

        lbl_t = Label(card, text=title, font=FONT_SMALL, bg=BG_CARD, fg=TEXT_MUTED)
        lbl_t.pack()

        return lbl_val

    def clear_feed(self):
        self.feed_list.delete(0, END)
        self.session_marked.clear()

    def start_stream(self):
        src = self.var_camera_src.get().strip()
        self.stream = ThreadedCCTVStream(source=src)
        if not self.stream.start():
            messagebox.showerror("Camera Error", self.stream.status_message, parent=self)
            return

        self.is_running = True
        self.btn_start.config(state=DISABLED)
        self.btn_stop.config(state=NORMAL)
        self.lbl_stream_status.config(text="● Live Stream Active", fg=ACCENT_EMERALD)
        self.reload_student_cache()
        self._video_loop()

    def stop_stream(self):
        self.is_running = False
        if self.stream:
            self.stream.stop()
            self.stream = None
        self.btn_start.config(state=NORMAL)
        self.btn_stop.config(state=DISABLED)
        self.lbl_stream_status.config(text="● Offline", fg=TEXT_MUTED)
        self.lbl_fps.config(text="FPS: 0.0")

    def _video_loop(self):
        if not self.is_running or not self.stream:
            return

        grabbed, frame = self.stream.read()
        if grabbed and frame is not None:
            self._process_frame(frame)

        self.after(25, self._video_loop)

    def _process_frame(self, frame):
        orig_h, orig_w = frame.shape[:2]

        # 1. Detect faces using YuNet Deep Learning Detector
        detections = self.detector.detect(frame)
        total_detected = len(detections)
        verified_count = 0
        unknown_count = 0

        # 2. Multi-face tracking across classroom desks
        tracked_faces = self.tracker.update_tracks(detections)

        # 3. Recognition & Embedding Matching
        for tid, track, det in tracked_faces:
            raw_face = det.get("raw_face_record")
            bbox = det["bbox"]
            x, y, w, h = bbox

            # Extract 128-D SFace feature
            aligned_face = self.recognizer.align_and_crop(frame, raw_face)
            probe_feat = self.recognizer.extract_feature(aligned_face)

            # Match against enrolled database
            best_sid, conf_pct, is_match = self.recognizer.match_probe(probe_feat)
            self.tracker.record_vote(tid, best_sid, conf_pct, is_match)

            # Check confirmed identity with hysteresis
            confirmed_id, confirmed_conf, is_confirmed = self.tracker.get_confirmed_identity(tid)

            if is_confirmed and confirmed_id:
                verified_count += 1
                student_info = self.students_cache.get(confirmed_id)
                name = student_info["name"] if student_info else f"ID: {confirmed_id}"
                roll = student_info["roll_no"] if student_info else ""

                # Auto mark attendance once per session
                if confirmed_id not in self.session_marked:
                    self.session_marked.add(confirmed_id)
                    marked, msg = db.mark_attendance(
                        student_id=confirmed_id,
                        name=name,
                        roll_no=roll,
                        confidence=confirmed_conf,
                        classroom=db.get_setting("classroom_name", "Classroom-A1")
                    )
                    t_str = datetime.now().strftime("%H:%M:%S")
                    entry_text = f"[{t_str}]  {name} ({confirmed_conf}%)"
                    self.feed_list.insert(0, entry_text)

                # Draw Emerald Green box for recognized student
                color = (0, 230, 115)  # BGR
                label = f"{name} ({int(confirmed_conf)}%)"
            else:
                unknown_count += 1
                color = (40, 40, 240)  # BGR Red
                label = "Unknown Face"

            # Draw bounding box & tag
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            cv2.rectangle(frame, (x, max(0, y - 26)), (x + len(label) * 9 + 10, y), color, -1)
            cv2.putText(
                frame,
                label,
                (x + 5, max(18, y - 7)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (255, 255, 255),
                1,
                cv2.LINE_AA
            )

        # Update KPI Badges
        self.badge_detected.config(text=str(total_detected))
        self.badge_verified.config(text=str(verified_count))
        self.badge_unknown.config(text=str(unknown_count))
        self.lbl_fps.config(text=f"FPS: {self.stream.get_fps()}")

        # Render frame onto Tkinter Canvas
        self._render_to_canvas(frame)

    def _render_to_canvas(self, frame):
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()

        if cw <= 1 or ch <= 1:
            return

        fh, fw = frame.shape[:2]
        ratio = min(cw / fw, ch / fh)
        nw, nh = int(fw * ratio), int(fh * ratio)

        resized = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_LINEAR)
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)
        photo = ImageTk.PhotoImage(image=img)

        self.canvas.delete("all")
        self.canvas.create_image(cw // 2, ch // 2, image=photo, anchor=CENTER)
        self.canvas.image = photo
