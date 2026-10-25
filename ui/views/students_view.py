import time
import threading
from datetime import datetime
from tkinter import *
from tkinter import ttk, messagebox
import cv2
import numpy as np

from ui.theme import *
from db_engine import db
from config import STUDENTS_DIR
from ai_pipeline.face_detector import FaceDetector
from ai_pipeline.face_recognizer import FaceRecognizer

class StudentsView(Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg=BG_DARK)
        self.controller = controller
        self.detector = getattr(controller, "detector", None) or FaceDetector()
        self.recognizer = getattr(controller, "recognizer", None) or FaceRecognizer()

        self.selected_student_id = None
        self._build_layout()
        self.load_students_table()

    def _build_layout(self):
        self.columnconfigure(0, weight=2)
        self.columnconfigure(1, weight=3)
        self.rowconfigure(0, weight=1)

        # ================= LEFT: Student Form & Biometric Enrolment =================
        form_panel = Frame(self, bg=BG_SURFACE, padx=16, pady=16)
        form_panel.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        form_panel.columnconfigure(1, weight=1)

        Label(
            form_panel,
            text="Student Registry & Biometrics",
            font=FONT_SUBTITLE,
            bg=BG_SURFACE,
            fg=TEXT_MAIN
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 16))

        # Form Fields
        fields = [
            ("Student ID *", "student_id"),
            ("Roll No *", "roll_no"),
            ("Full Name *", "name"),
            ("Department", "department"),
            ("Course", "course"),
            ("Year", "year"),
            ("Semester", "semester"),
            ("Gender", "gender"),
            ("Email", "email"),
            ("Phone", "phone"),
        ]

        self.form_vars = {}
        for idx, (label_text, key) in enumerate(fields, start=1):
            Label(
                form_panel,
                text=label_text,
                font=FONT_SMALL,
                bg=BG_SURFACE,
                fg=TEXT_MUTED
            ).grid(row=idx, column=0, sticky="w", pady=4)

            var = StringVar()
            entry = Entry(
                form_panel,
                textvariable=var,
                bg=BG_CARD,
                fg=TEXT_MAIN,
                insertbackground=TEXT_MAIN,
                font=FONT_BODY,
                relief="flat"
            )
            entry.grid(row=idx, column=1, sticky="ew", pady=4, padx=(8, 0), ipady=2)
            self.form_vars[key] = var

        # Form Action Buttons
        btn_box = Frame(form_panel, bg=BG_SURFACE)
        btn_box.grid(row=11, column=0, columnspan=2, sticky="ew", pady=(16, 12))

        btn_save = Button(btn_box, text="💾 Save Student", command=self.save_student)
        style_button(btn_save, variant="primary")
        btn_save.pack(side=LEFT, padx=(0, 6))

        btn_reset = Button(btn_box, text="Reset", command=self.reset_form)
        style_button(btn_reset, variant="secondary")
        btn_reset.pack(side=LEFT, padx=6)

        btn_delete = Button(btn_box, text="Delete", command=self.delete_student)
        style_button(btn_delete, variant="danger")
        btn_delete.pack(side=LEFT, padx=6)

        # Biometric AI Enrolment Card
        bio_card = Frame(form_panel, bg=BG_CARD, padx=12, pady=12, relief="flat")
        bio_card.grid(row=12, column=0, columnspan=2, sticky="ew", pady=(8, 0))

        Label(
            bio_card,
            text="🧠 Biometric Deep Face Enrolment",
            font=FONT_BODY_BOLD,
            bg=BG_CARD,
            fg=ACCENT_BLUE
        ).pack(anchor="w", pady=(0, 4))

        self.lbl_enrolment_status = Label(
            bio_card,
            text="Status: Select a student to view enrolment",
            font=FONT_SMALL,
            bg=BG_CARD,
            fg=TEXT_MUTED
        )
        self.lbl_enrolment_status.pack(anchor="w", pady=(0, 8))

        self.btn_capture = Button(
            bio_card,
            text="📸 Capture 5 Samples & Enroll AI (SFace)",
            command=self.capture_and_enroll
        )
        style_button(self.btn_capture, variant="success")
        self.btn_capture.pack(fill=X)

        # ================= RIGHT: Searchable Student Table =================
        table_panel = Frame(self, bg=BG_SURFACE, padx=16, pady=16)
        table_panel.grid(row=0, column=1, sticky="nsew", padx=(0, 16), pady=16)
        table_panel.rowconfigure(2, weight=1)
        table_panel.columnconfigure(0, weight=1)

        # Search Bar
        search_box = Frame(table_panel, bg=BG_SURFACE)
        search_box.grid(row=0, column=0, sticky="ew", pady=(0, 12))

        Label(search_box, text="🔍 Search:", font=FONT_BODY_BOLD, bg=BG_SURFACE, fg=TEXT_MAIN).pack(side=LEFT, padx=(0, 8))
        self.var_search = StringVar()
        self.var_search.trace_add("write", lambda *args: self.filter_table())
        entry_search = Entry(
            search_box,
            textvariable=self.var_search,
            width=30,
            bg=BG_CARD,
            fg=TEXT_MAIN,
            insertbackground=TEXT_MAIN,
            font=FONT_BODY,
            relief="flat"
        )
        entry_search.pack(side=LEFT, ipady=3)

        # Student Count Badge
        self.lbl_student_count = Label(
            search_box,
            text="Total: 0 Students",
            font=FONT_SMALL,
            bg=BG_SURFACE,
            fg=TEXT_MUTED
        )
        self.lbl_student_count.pack(side=RIGHT)

        # Treeview Table
        columns = ("id", "roll", "name", "dept", "course", "embedding")
        self.tree = ttk.Treeview(table_panel, columns=columns, show="headings", selectmode="browse")

        self.tree.heading("id", text="Student ID")
        self.tree.heading("roll", text="Roll No")
        self.tree.heading("name", text="Name")
        self.tree.heading("dept", text="Department")
        self.tree.heading("course", text="Course")
        self.tree.heading("embedding", text="Biometrics")

        self.tree.column("id", width=90, anchor="center")
        self.tree.column("roll", width=90, anchor="center")
        self.tree.column("name", width=140, anchor="w")
        self.tree.column("dept", width=110, anchor="w")
        self.tree.column("course", width=100, anchor="w")
        self.tree.column("embedding", width=110, anchor="center")

        tree_scroll = Scrollbar(table_panel, orient=VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)

        self.tree.grid(row=2, column=0, sticky="nsew")
        tree_scroll.grid(row=2, column=1, sticky="ns")

        self.tree.bind("<<TreeviewSelect>>", self.on_row_select)

    def load_students_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        students = db.get_all_students()
        for s in students:
            bio_status = "🟢 Enrolled" if s["has_embedding"] else "🔴 Pending"
            self.tree.insert("", END, values=(
                s["student_id"],
                s["roll_no"],
                s["name"],
                s["department"],
                s["course"],
                bio_status
            ))

        self.lbl_student_count.config(text=f"Total: {len(students)} Students")

    def filter_table(self):
        q = self.var_search.get().lower().strip()
        for item in self.tree.get_children():
            self.tree.delete(item)

        students = db.get_all_students()
        count = 0
        for s in students:
            if not q or (q in str(s["student_id"]).lower() or q in str(s["name"]).lower() or q in str(s["roll_no"]).lower()):
                bio_status = "🟢 Enrolled" if s["has_embedding"] else "🔴 Pending"
                self.tree.insert("", END, values=(
                    s["student_id"],
                    s["roll_no"],
                    s["name"],
                    s["department"],
                    s["course"],
                    bio_status
                ))
                count += 1
        self.lbl_student_count.config(text=f"Matched: {count} Students")

    def on_row_select(self, event):
        selected = self.tree.selection()
        if not selected:
            return
        row = self.tree.item(selected[0])["values"]
        student_id = str(row[0])
        student = db.get_student(student_id)
        if not student:
            return

        self.selected_student_id = student_id
        for k, v in self.form_vars.items():
            v.set(student.get(k, ""))

        if student["has_embedding"]:
            self.lbl_enrolment_status.config(
                text=f"🟢 Enrolled with {student['photo_sample_count']} samples (128-D vector active)",
                fg=ACCENT_EMERALD
            )
        else:
            self.lbl_enrolment_status.config(
                text="🔴 No face profile enrolled yet. Click below to enroll.",
                fg=ACCENT_ROSE
            )

    def reset_form(self):
        self.selected_student_id = None
        for v in self.form_vars.values():
            v.set("")
        self.lbl_enrolment_status.config(
            text="Status: Select a student to view enrolment",
            fg=TEXT_MUTED
        )

    def save_student(self):
        sid = self.form_vars["student_id"].get().strip()
        name = self.form_vars["name"].get().strip()
        roll = self.form_vars["roll_no"].get().strip()

        if not sid or not name or not roll:
            messagebox.showwarning("Validation Error", "Student ID, Roll No, and Name are required.", parent=self)
            return

        student_data = {
            "student_id": sid,
            "roll_no": roll,
            "name": name,
            "department": self.form_vars["department"].get().strip(),
            "course": self.form_vars["course"].get().strip(),
            "year": self.form_vars["year"].get().strip(),
            "semester": self.form_vars["semester"].get().strip(),
            "gender": self.form_vars["gender"].get().strip(),
            "email": self.form_vars["email"].get().strip(),
            "phone": self.form_vars["phone"].get().strip(),
            "enrolled_date": datetime.now().strftime("%Y-%m-%d"),
            "photo_sample_count": 0,
            "has_embedding": 0
        }

        # Preserve existing biometric status if updating
        existing = db.get_student(sid)
        if existing:
            student_data["photo_sample_count"] = existing["photo_sample_count"]
            student_data["has_embedding"] = existing["has_embedding"]

        db.upsert_student(student_data)
        messagebox.showinfo("Success", f"Student {name} saved successfully.", parent=self)
        self.load_students_table()

    def delete_student(self):
        if not self.selected_student_id:
            messagebox.showwarning("Selection", "Please select a student from the table first.", parent=self)
            return

        confirm = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete student ID {self.selected_student_id} and their biometric profile?",
            parent=self
        )
        if confirm:
            db.delete_student(self.selected_student_id)
            self.recognizer.delete_enrolled_student(self.selected_student_id)
            self.reset_form()
            self.load_students_table()
            messagebox.showinfo("Deleted", "Student removed successfully.", parent=self)

    def capture_and_enroll(self):
        sid = self.form_vars["student_id"].get().strip()
        name = self.form_vars["name"].get().strip()
        if not sid or not name:
            messagebox.showwarning("Required", "Please select or enter Student ID and Name before capturing faces.", parent=self)
            return

        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            messagebox.showerror("Camera Error", "Could not access local webcam for facial enrolment.", parent=self)
            return

        captured_embeddings = []
        samples_needed = 5
        sample_count = 0
        student_folder = STUDENTS_DIR / sid
        student_folder.mkdir(parents=True, exist_ok=True)

        messagebox.showinfo(
            "Facial Enrolment Instructions",
            f"Camera will now capture 5 face samples for {name}.\n\n"
            "• Look straight at the camera.\n"
            "• Slightly tilt head left, right, up for full-angle coverage.\n"
            "• Press 'C' or SPACEBAR to capture sample.\n"
            "• Press 'Q' or ESC to exit.",
            parent=self
        )

        while sample_count < samples_needed:
            ret, frame = cap.read()
            if not ret or frame is None:
                continue

            display_frame = frame.copy()
            detections = self.detector.detect(frame)

            msg = f"Samples: {sample_count}/{samples_needed} | Press 'C' or SPACEBAR to Capture"
            cv2.rectangle(display_frame, (0, 0), (display_frame.shape[1], 40), (20, 25, 35), -1)
            cv2.putText(display_frame, msg, (15, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (56, 189, 248), 2)

            valid_face = None
            if len(detections) > 0:
                # Pick largest face
                largest = max(detections, key=lambda d: d["bbox"][2] * d["bbox"][3])
                x, y, w, h = largest["bbox"]
                cv2.rectangle(display_frame, (x, y), (x + w, y + h), (0, 230, 115), 2)
                cv2.putText(display_frame, f"Face Ready ({int(largest['score']*100)}%)", (x, y - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 230, 115), 2)
                valid_face = largest

            cv2.imshow("Biometric Face Enrolment - Press C to Capture", display_frame)
            key = cv2.waitKey(1) & 0xFF

            if key in (ord('c'), ord('C'), 32):  # 'c' or space
                if valid_face is not None:
                    # Align crop and extract 128-D vector
                    aligned = self.recognizer.align_and_crop(frame, valid_face.get("raw_face_record"))
                    feat = self.recognizer.extract_feature(aligned)
                    if feat is not None:
                        sample_count += 1
                        captured_embeddings.append(feat)
                        sample_path = student_folder / f"sample_{sample_count}.jpg"
                        cv2.imwrite(str(sample_path), aligned if aligned is not None else frame)
                        print(f"[Enrolment] Captured sample {sample_count}/{samples_needed}")

            elif key in (ord('q'), ord('Q'), 27):  # 'q' or ESC
                break

        cap.release()
        cv2.destroyAllWindows()

        if sample_count >= 1:
            success = self.recognizer.enroll_student(sid, captured_embeddings)
            if success:
                db.update_student_biometric_status(sid, sample_count=sample_count, has_embedding=1)
                self.load_students_table()
                self.lbl_enrolment_status.config(
                    text=f"🟢 Enrolled with {sample_count} samples (128-D vector active)",
                    fg=ACCENT_EMERALD
                )
                messagebox.showinfo(
                    "Enrolment Complete",
                    f"Successfully enrolled {sample_count} facial vectors for {name}!\n"
                    "Their profile is now active for classroom CCTV attendance.",
                    parent=self
                )
        else:
            messagebox.showwarning("Cancelled", "No face samples were captured.", parent=self)
