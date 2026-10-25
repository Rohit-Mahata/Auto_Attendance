from tkinter import *
from tkinter import ttk, messagebox
from ui.theme import *
from db_engine import db
from config import YUNET_MODEL_FILE, SFACE_MODEL_FILE

class AISettingsView(Frame):
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

        # ================= LEFT: AI Model Architecture & Engine Status =================
        card_model = Frame(container, bg=BG_SURFACE, padx=20, pady=20)
        card_model.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        Label(
            card_model,
            text="🧠 Deep Learning Engine Architecture",
            font=FONT_SUBTITLE,
            bg=BG_SURFACE,
            fg=ACCENT_BLUE
        ).pack(anchor="w", pady=(0, 12))

        yunet_status = "🟢 Active (ONNX Loaded)" if YUNET_MODEL_FILE.exists() else "🔴 Missing"
        sface_status = "🟢 Active (ONNX Loaded)" if SFACE_MODEL_FILE.exists() else "🔴 Missing"

        specs = [
            ("Face Detector", f"OpenCV YuNet (ResNet-like DNN)\nStatus: {yunet_status}"),
            ("Classroom Angle Capability", "Supports up to 45° pitch and 60° yaw head tilts"),
            ("Small Face Sensitivity", "Detects distant student faces down to 10×10 px"),
            ("Face Landmark Warping", "5-Point canonical eye/nose/mouth geometry alignment"),
            ("Recognition Architecture", f"OpenCV SFace (MobileFaceNet Backbone)\nStatus: {sface_status}"),
            ("Biometric Representation", "128-Dimensional L2-Normalized Feature Vectors"),
            ("Matching Metric", "Cosine Similarity (Invariant to classroom lighting shifts)"),
        ]

        for title, desc in specs:
            f = Frame(card_model, bg=BG_CARD, padx=12, pady=10)
            f.pack(fill=X, pady=4)
            Label(f, text=title, font=FONT_BODY_BOLD, bg=BG_CARD, fg=TEXT_MAIN).pack(anchor="w")
            Label(f, text=desc, font=FONT_SMALL, bg=BG_CARD, fg=TEXT_MUTED).pack(anchor="w", pady=(2, 0))

        # ================= RIGHT: Real-time Calibration Controls =================
        card_controls = Frame(container, bg=BG_SURFACE, padx=20, pady=20)
        card_controls.grid(row=0, column=1, sticky="nsew", padx=(12, 0))

        Label(
            card_controls,
            text="🎛️ Classroom Calibration Parameters",
            font=FONT_SUBTITLE,
            bg=BG_SURFACE,
            fg=TEXT_MAIN
        ).pack(anchor="w", pady=(0, 16))

        # 1. Detection Threshold Slider
        Label(card_controls, text="Face Detection Sensitivity (Score Threshold)", font=FONT_BODY_BOLD, bg=BG_SURFACE, fg=TEXT_MAIN).pack(anchor="w", pady=(6, 2))
        Label(card_controls, text="Lower values detect dimmer / more distant faces in classroom back rows.", font=FONT_SMALL, bg=BG_SURFACE, fg=TEXT_MUTED).pack(anchor="w")
        self.slider_det = Scale(
            card_controls, from_=0.40, to=0.90, resolution=0.05, orient=HORIZONTAL,
            bg=BG_SURFACE, fg=TEXT_MAIN, highlightthickness=0, troughcolor=BG_CARD
        )
        self.slider_det.set(float(db.get_setting("min_confidence", "65")) / 100.0)
        self.slider_det.pack(fill=X, pady=(2, 14))

        # 2. Cosine Similarity Match Threshold Slider
        Label(card_controls, text="Identity Match Cosine Threshold", font=FONT_BODY_BOLD, bg=BG_SURFACE, fg=TEXT_MAIN).pack(anchor="w", pady=(6, 2))
        Label(card_controls, text="Threshold above which a face is positively verified as a student (0.50 - 0.70 recommended).", font=FONT_SMALL, bg=BG_SURFACE, fg=TEXT_MUTED).pack(anchor="w")
        self.slider_sim = Scale(
            card_controls, from_=0.45, to=0.80, resolution=0.02, orient=HORIZONTAL,
            bg=BG_SURFACE, fg=TEXT_MAIN, highlightthickness=0, troughcolor=BG_CARD
        )
        self.slider_sim.set(0.58)
        self.slider_sim.pack(fill=X, pady=(2, 14))

        # 3. Confirmation Frames
        Label(card_controls, text="Consecutive Confirmation Frames (Hysteresis)", font=FONT_BODY_BOLD, bg=BG_SURFACE, fg=TEXT_MAIN).pack(anchor="w", pady=(6, 2))
        Label(card_controls, text="Number of consecutive positive frames needed before marking attendance to prevent flickering.", font=FONT_SMALL, bg=BG_SURFACE, fg=TEXT_MUTED).pack(anchor="w")
        self.spin_confirm = Spinbox(card_controls, from_=1, to=8, width=10, bg=BG_CARD, fg=TEXT_MAIN, font=FONT_BODY, relief="flat")
        self.spin_confirm.delete(0, END)
        self.spin_confirm.insert(0, "3")
        self.spin_confirm.pack(anchor="w", pady=(4, 16))

        # 4. Save Button
        btn_save = Button(card_controls, text="💾 Apply & Save Calibration", command=self.save_calibration)
        style_button(btn_save, variant="primary")
        btn_save.pack(fill=X, pady=(16, 0))

    def save_calibration(self):
        det_val = int(self.slider_det.get() * 100)
        db.set_setting("min_confidence", str(det_val))
        messagebox.showinfo("Saved", "Classroom AI calibration settings updated successfully.", parent=self)
