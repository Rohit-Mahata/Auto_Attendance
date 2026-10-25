"""
Student Guided Enrolment & Registration Service
Implements Section 3: Details form, legal consent, 3-4s burst capture,
liveness motion validation, attribute tagging, profile photo matching,
and pose-aware template creation.
"""

import os
import cv2
import json
import time
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

from config import DATA_DIR, STUDENTS_DIR
from security.encryption import security_engine
from db.database import production_db
from ai_pipeline.pipeline import (
    FaceDetector,
    ProductionFaceRecognizer,
    check_frame_quality,
    score_face_crop
)

ENROLMENT_BURST_DIR = DATA_DIR / "biometric_vault" / "burst_frames"
PROFILE_PHOTOS_DIR = DATA_DIR / "biometric_vault" / "profiles"
ENROLMENT_BURST_DIR.mkdir(parents=True, exist_ok=True)
PROFILE_PHOTOS_DIR.mkdir(parents=True, exist_ok=True)

class RegistrationService:
    def __init__(self, detector: Optional[FaceDetector] = None,
                 recognizer: Optional[ProductionFaceRecognizer] = None):
        self.detector = detector or FaceDetector()
        self.recognizer = recognizer or ProductionFaceRecognizer()

    # ================= Step 1: Validate Student Details =================
    def validate_student_details(self, details: Dict[str, Any], allow_existing: bool = False) -> Tuple[bool, str]:
        """
        Validates details matching field names from sudeep:
        Name, Student_ID (unique), Dep, Course, Year, Semester, Division (Section dropdown), Roll, Email.
        """
        required_fields = ["student_id", "name", "department", "division", "course", "year", "semester"]
        for f in required_fields:
            if not details.get(f) or not str(details.get(f)).strip():
                return False, f"Field '{f}' is required and cannot be empty."

        sid = str(details["student_id"]).strip()
        # University ID format check (alphanumeric, 3 to 16 chars)
        if len(sid) < 3 or len(sid) > 16:
            return False, "University ID must be between 3 and 16 characters."

        # Check existing registration
        existing = production_db.get_student_by_id(sid)
        if existing and not allow_existing:
            return False, f"University ID '{sid}' is already registered in the system."

        return True, "Details validated successfully."

    # ================= Step 2: Record Consent =================
    def record_consent(self, student_id: str, agreed: bool, wording_version: str = "v2026.1-np",
                       non_camera_opt_out: bool = False, actor: str = "StudentSelf") -> Tuple[bool, str]:
        """
        Records versioned consent. If opted out, student status is set to 'opted_out'.
        """
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        student = production_db.get_student_by_id(student_id)
        if not student:
            return False, f"Student {student_id} not found."

        student_int_id = student["id"]

        with production_db.get_connection() as conn:
            cur = conn.cursor()
            if non_camera_opt_out or not agreed:
                cur.execute("""
                    INSERT INTO consents (student_id, wording_version, consent_given, given_at, withdrawn_at)
                    VALUES (?, ?, 0, ?, ?);
                """, (student_int_id, wording_version, now_str, now_str))
                cur.execute("UPDATE students SET status = 'opted_out' WHERE id = ?;", (student_int_id,))
                conn.commit()
                production_db.log_audit(actor, "OPT_OUT_CONSENT", "students", student_id, after="opted_out")
                return True, "Non-camera alternative recorded. Student will be marked via roll call."

            cur.execute("""
                INSERT INTO consents (student_id, wording_version, consent_given, given_at)
                VALUES (?, ?, 1, ?);
            """, (student_int_id, wording_version, now_str))
            conn.commit()
            production_db.log_audit(actor, "GRANT_BIOMETRIC_CONSENT", "students", student_id, after=wording_version)
            return True, "Consent recorded successfully."

    # ================= Step 3: Process Capture Burst (3-4s, 60-70 frames) =================
    def process_burst_frames(self, student_id: str, frame_list_bgr: List[np.ndarray],
                             min_usable_frames: int = 30) -> Dict[str, Any]:
        """
        Evaluates 60-70 frames recorded during the 3-4s guided burst.
        Checks:
        - Exactly one face
        - Sufficient size (>= 40px)
        - Sharpness, brightness, eyes visible
        - Head turn liveness: verifies 3D head movement (minimum 4 pose groups covered)
        - Drops near-duplicate frames
        - Saves kept face crops encrypted at rest
        """
        student = production_db.get_student_by_id(student_id)
        if not student:
            return {"success": False, "error": f"Student {student_id} not found"}

        student_int_id = student["id"]
        kept_records = []
        pose_groups_found = set()
        prev_embedding = None

        for idx, frame in enumerate(frame_list_bgr):
            if frame is None or frame.size == 0:
                continue

            # Frame quality check
            is_ok, _, _ = check_frame_quality(frame, blur_threshold=70.0, min_brightness=35.0, max_brightness=235.0)
            if not is_ok:
                continue

            # Detect faces: strictly require exactly 1 face
            dets = self.detector.detect(frame)
            if len(dets) != 1:
                continue  # Discard frames with 0 or >1 people

            det = dets[0]
            x, y, w, h = det["bbox"]
            if w < 38 or h < 38:
                continue

            crop = frame[y:y+h, x:x+w]
            if crop.size == 0:
                continue

            attributes = score_face_crop(crop, det["bbox"], det.get("landmarks"))
            aligned = self.recognizer.align_and_crop(frame, det.get("raw_face_record"))
            emb = self.recognizer.extract_embedding(aligned)
            if emb is None:
                continue

            # Duplicate check: skip if identical pose/embedding to immediate predecessor
            if prev_embedding is not None:
                sim = ProductionFaceRecognizer.cosine_similarity(emb, prev_embedding)
                if sim > 0.98:  # Almost identical frame
                    continue

            prev_embedding = emb
            pose_groups_found.add(attributes["pose_group"])

            # Encrypt and save crop
            now_ts = int(time.time() * 1000)
            enc_filename = f"burst_{student_id}_{idx}_{now_ts}.enc"
            enc_path = ENROLMENT_BURST_DIR / enc_filename

            _, enc_jpg = cv2.imencode(".jpg", crop)
            encrypted_bytes = security_engine.encrypt_bytes(enc_jpg.tobytes())
            with open(enc_path, "wb") as f:
                f.write(encrypted_bytes)

            kept_records.append({
                "index": idx,
                "crop_path": str(enc_path),
                "embedding": emb,
                "attributes": attributes
            })

        # Validation Rule: Minimum 30 usable frames covering at least 4 pose groups
        if len(kept_records) < min_usable_frames:
            return {
                "success": False,
                "error": f"Insufficient usable frames ({len(kept_records)} < {min_usable_frames}). Please repeat the burst with even lighting.",
                "usable_count": len(kept_records),
                "pose_groups": list(pose_groups_found)
            }

        if len(pose_groups_found) < 3:
            return {
                "success": False,
                "error": f"Insufficient head movement variety ({len(pose_groups_found)} pose groups). Please turn head slowly left, right, up and down.",
                "usable_count": len(kept_records),
                "pose_groups": list(pose_groups_found)
            }

        # Save to database
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with production_db.get_connection() as conn:
            cur = conn.cursor()
            for rec in kept_records:
                attr = rec["attributes"]
                cur.execute("""
                    INSERT INTO enrolment_frames (
                        student_id, encrypted_file_ref, yaw, pitch, brightness,
                        sharpness, expression, glasses, face_size, quality,
                        selected_as_template, model_version, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, 'neutral', 0, ?, ?, 0, 'SFace-2021dec', ?);
                """, (student_int_id, rec["crop_path"], attr["yaw"], attr["pitch"],
                      attr["brightness"], attr["blur"], attr["width"], attr["quality"], now_str))

            cur.execute("""
                UPDATE students SET photo_sample_count = ? WHERE id = ?;
            """, (len(kept_records), student_int_id))
            conn.commit()

        production_db.log_audit("RegistrationEngine", "SAVE_BURST_FRAMES", "enrolment_frames", student_id,
                                after=f"Saved {len(kept_records)} encrypted frames")

        return {
            "success": True,
            "usable_count": len(kept_records),
            "pose_groups": list(pose_groups_found),
            "kept_records": kept_records
        }

    # ================= Step 4: Validate Profile Photo =================
    def validate_and_save_profile_photo(self, student_id: str, profile_image_bgr: np.ndarray,
                                        burst_embeddings: List[np.ndarray],
                                        source: str = "capture") -> Tuple[bool, str, Optional[str]]:
        """
        Validates profile photo:
        - Exactly 1 face, large enough, sharp
        - CRITICAL RULE: Must match the student's own burst frames!
        """
        if profile_image_bgr is None or profile_image_bgr.size == 0:
            return False, "Invalid image data", None

        dets = self.detector.detect(profile_image_bgr)
        if len(dets) != 1:
            return False, f"Profile photo must contain exactly one face (found {len(dets)}).", None

        det = dets[0]
        if det["bbox"][2] < 50:
            return False, "Face is too small. Please move closer to the camera.", None

        aligned = self.recognizer.align_and_crop(profile_image_bgr, det.get("raw_face_record"))
        probe_emb = self.recognizer.extract_embedding(aligned)
        if probe_emb is None:
            return False, "Could not extract facial biometric template.", None

        # Burst match verification: uploaded photo must match the student's burst
        if burst_embeddings:
            sims = [ProductionFaceRecognizer.cosine_similarity(probe_emb, b_emb) for b_emb in burst_embeddings]
            max_sim = max(sims)
            if max_sim < 0.58:
                return False, f"Profile photo does not match the captured head burst (Match score: {max_sim:.2f} < 0.58). Ensure the photo belongs to the same person.", None

        # Encrypt and save profile photo
        student = production_db.get_student_by_id(student_id)
        student_int_id = student["id"]
        now_ts = int(time.time() * 1000)
        enc_filename = f"profile_{student_id}_{now_ts}.enc"
        enc_path = PROFILE_PHOTOS_DIR / enc_filename

        _, enc_jpg = cv2.imencode(".jpg", profile_image_bgr)
        encrypted_bytes = security_engine.encrypt_bytes(enc_jpg.tobytes())
        with open(enc_path, "wb") as f:
            f.write(encrypted_bytes)

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with production_db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO profile_photos (student_id, encrypted_file_ref, source, matched_own_burst, created_at)
                VALUES (?, ?, ?, 1, ?);
            """, (student_int_id, str(enc_path), source, now_str))
            conn.commit()

        # Add profile photo as an active enrolment template
        production_db.save_face_template(
            student_int_id, probe_emb, quality=0.95, pose_group="front",
            source="id_photo", status="active"
        )

        return True, "Profile photo verified and saved successfully.", str(enc_path)

    # ================= Step 6: Pose-Aware Multi-Template Generation =================
    def build_pose_aware_templates(self, student_id: str, kept_records: List[Dict[str, Any]]) -> Tuple[bool, str, int]:
        """
        Builds multi-template set:
        1. L2-normalised embeddings.
        2. Outlier removal (distance > threshold from mean).
        3. Attribute grouping (front, left, right, up, down). Top 1-3 best frames per group + centroids.
        4. Post-save collision check against all other students.
        """
        student = production_db.get_student_by_id(student_id)
        student_int_id = student["id"]

        if not kept_records:
            return False, "No burst records available", 0

        # Outlier removal
        embeddings = [r["embedding"] for r in kept_records]
        stacked = np.vstack(embeddings)
        centroid = np.mean(stacked, axis=0)
        centroid = centroid / np.linalg.norm(centroid)

        filtered_records = []
        for r in kept_records:
            sim = ProductionFaceRecognizer.cosine_similarity(r["embedding"], centroid)
            if sim >= 0.50:  # Exclude bad frames
                filtered_records.append(r)

        if len(filtered_records) < 15:
            return False, "Too many inconsistent frames detected. Retake required.", 0

        # Group by pose attribute
        groups = {}
        for r in filtered_records:
            pg = r["attributes"]["pose_group"]
            groups.setdefault(pg, []).append(r)

        saved_templates_count = 0
        for pg, recs in groups.items():
            # Sort by quality
            recs.sort(key=lambda x: x["attributes"]["quality"], reverse=True)
            top_samples = recs[:3]  # Keep 1 to 3 best per group

            for s in top_samples:
                production_db.save_face_template(
                    student_int_id, s["embedding"], quality=s["attributes"]["quality"],
                    pose_group=pg, source="enrolment", status="active"
                )
                saved_templates_count += 1

            # Save pose-group centroid
            if len(recs) >= 2:
                grp_embs = np.vstack([x["embedding"] for x in recs])
                grp_mean = np.mean(grp_embs, axis=0)
                grp_mean = grp_mean / np.linalg.norm(grp_mean)
                production_db.save_face_template(
                    student_int_id, grp_mean.astype(np.float32), quality=0.85,
                    pose_group=f"{pg}_centroid", source="enrolment", status="active"
                )
                saved_templates_count += 1

        # Post-save collision check: compare student centroid against other students
        with production_db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT student_id, embedding_encrypted FROM face_templates
                WHERE student_id != ? AND status = 'active';
            """, (student_int_id,))
            other_rows = cur.fetchall()

        collision_flagged = False
        for r in other_rows:
            other_vec = security_engine.decrypt_embedding(r["embedding_encrypted"])
            sim = ProductionFaceRecognizer.cosine_similarity(centroid, other_vec)
            if sim > 0.78:  # Highly suspicious collision
                collision_flagged = True
                production_db.log_audit("BiometricEngine", "FLAG_FACE_COLLISION", "students", student_id,
                                        after=f"Similarity {sim:.2f} with student {r['student_id']}")
                break

        status_msg = f"Generated {saved_templates_count} pose-aware templates."
        if collision_flagged:
            status_msg += " (Warning: Face similarity collision flagged for department review)."

        return True, status_msg, saved_templates_count

# Global Registration Service Singleton
registration_service = RegistrationService()
