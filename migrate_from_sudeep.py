import os
import glob
import sqlite3
import cv2
import numpy as np
from pathlib import Path

from config import DATA_DIR, STUDENTS_DIR, EMBEDDINGS_PATH
from db.database import production_db
from ai_pipeline.face_detector import FaceDetector
from ai_pipeline.face_recognizer import FaceRecognizer

def migrate():
    sudeep_db_path = Path(__file__).resolve().parent.parent / "sudeep" / "student.db"
    sudeep_data_dir = Path(__file__).resolve().parent.parent / "sudeep" / "data"

    if not sudeep_db_path.exists():
        print(f"[Migration] Legacy DB not found at: {sudeep_db_path}")
        return

    detector = FaceDetector()
    recognizer = FaceRecognizer()

    conn = sqlite3.connect(str(sudeep_db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM student")
    students = cur.fetchall()

    print(f"[Migration] Found {len(students)} students in legacy database. Migrating...")

    for row in students:
        sid = str(row["Student_ID"]).strip()
        name = row["Name"].strip()
        roll = str(row["Roll"]).strip()

        # Check existing photos for this student
        photo_pattern = str(sudeep_data_dir / f"user.{sid}.*.jpg")
        sample_files = glob.glob(photo_pattern)
        sample_count = len(sample_files)

        features = []
        if sample_files:
            # Pick up to 8 diverse samples
            step = max(1, len(sample_files) // 8)
            selected = sample_files[::step][:8]

            for img_path in selected:
                img = cv2.imread(img_path)
                if img is None:
                    continue

                detections = detector.detect(img)
                if detections:
                    best_face = max(detections, key=lambda d: d["bbox"][2] * d["bbox"][3])
                    aligned = recognizer.align_and_crop(img, best_face.get("raw_face_record"))
                    feat = recognizer.extract_feature(aligned)
                    if feat is not None:
                        features.append(feat)

        has_bio = 0
        if features:
            recognizer.enroll_student(sid, features)
            has_bio = 1
            print(f"[Migration] Extracted 128-D Deep Vector for {name} (ID: {sid}) from {len(features)} photos.")

        student_data = {
            "student_id": sid,
            "roll_no": roll,
            "name": name,
            "department": row["Dep"] or "Computer Science",
            "course": row["Course"] or "B.Tech",
            "year": row["Year"] or "2024-25",
            "semester": row["Semester"] or "7th Semester",
            "gender": row["Gender"] or "Male",
            "email": row["Email"] or f"{sid}@university.edu",
            "phone": row["Phone"] or "",
            "enrolled_date": "2026-10-23",
            "photo_sample_count": sample_count,
            "has_embedding": has_bio
        }
        db_id = production_db.register_student(student_data)
        if has_bio and features:
            centroid = np.mean(np.vstack(features), axis=0)
            norm = np.linalg.norm(centroid)
            if norm > 1e-6:
                centroid = centroid / norm
            production_db.save_face_template(
                student_id_int=db_id,
                embedding_vec=centroid.astype(np.float32),
                quality=0.92,
                pose_group="front",
                source="migration",
                confirmed_by="MigrationScript"
            )

    recognizer.save_enrolled_embeddings()
    conn.close()
    print("[Migration] Migration completed successfully into production database!")

if __name__ == "__main__":
    migrate()
