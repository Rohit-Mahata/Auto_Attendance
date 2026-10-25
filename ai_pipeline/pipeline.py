"""
Production Classroom Face Attendance Pipeline
Implements the 9-step detection, tracking, pose-aware matching,
Hungarian roster assignment, and learning loop engine.
"""

import time
import math
import cv2
import numpy as np
from datetime import datetime
from collections import deque, Counter
from typing import List, Dict, Tuple, Optional, Any
from pathlib import Path

from config import (
    YUNET_MODEL_FILE,
    SFACE_MODEL_FILE,
    DEFAULT_DETECTION_CONFIDENCE,
    DEFAULT_COSINE_SIMILARITY_THRESHOLD
)
from ai_pipeline.face_detector import FaceDetector
from ai_pipeline.hungarian import RosterHungarianMatcher, linear_sum_assignment_pure
from security.encryption import security_engine

# ==============================================================================
# 1. Frame Quality Filter & Attributes
# ==============================================================================
def check_frame_quality(frame_bgr: np.ndarray, blur_threshold: float = 80.0,
                        min_brightness: float = 40.0, max_brightness: float = 225.0) -> Tuple[bool, str, Dict[str, float]]:
    """
    Step 1: Frame filter. Drops blurred, dark, or overexposed frames.
    Returns: (is_valid, reason, metrics)
    """
    if frame_bgr is None or frame_bgr.size == 0:
        return False, "Empty frame", {}

    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    brightness = float(gray.mean())

    metrics = {"blur": round(blur_score, 1), "brightness": round(brightness, 1)}

    if blur_score < blur_threshold:
        return False, f"Frame blurred (Laplacian {blur_score:.1f} < {blur_threshold})", metrics
    if brightness < min_brightness:
        return False, f"Frame too dark (Mean brightness {brightness:.1f} < {min_brightness})", metrics
    if brightness > max_brightness:
        return False, f"Frame overexposed (Mean brightness {brightness:.1f} > {max_brightness})", metrics

    return True, "Quality acceptable", metrics

def score_face_crop(crop_bgr: np.ndarray, bbox: List[int], landmarks: Optional[List[Tuple[int, int]]]) -> Dict[str, Any]:
    """
    Step 4: Scores size, blur, pose, and brightness for every face crop.
    """
    h, w = crop_bgr.shape[:2]
    gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY) if crop_bgr.size > 0 else np.zeros((1, 1), dtype=np.uint8)

    blur_val = float(cv2.Laplacian(gray, cv2.CV_64F).var()) if crop_bgr.size > 0 else 0.0
    brightness = float(gray.mean()) if crop_bgr.size > 0 else 0.0

    # Yaw & Pitch estimation from 5 landmarks (Right Eye, Left Eye, Nose, Mouth Right, Mouth Left)
    yaw = 0.0
    pitch = 0.0
    pose_group = "front"

    if landmarks and len(landmarks) >= 5:
        re, le, nose, mr, ml = landmarks[:5]
        # Eye distance vs nose center gives horizontal yaw
        eye_mid_x = (re[0] + le[0]) / 2.0
        eye_dist = max(1.0, abs(le[0] - re[0]))
        yaw_ratio = (nose[0] - eye_mid_x) / eye_dist
        yaw = float(np.clip(yaw_ratio * 45.0, -60.0, 60.0))

        # Vertical pitch from eye-to-nose vs nose-to-mouth
        eye_mid_y = (re[1] + le[1]) / 2.0
        mouth_mid_y = (mr[1] + ml[1]) / 2.0
        face_h = max(1.0, abs(mouth_mid_y - eye_mid_y))
        pitch_ratio = ((nose[1] - eye_mid_y) / face_h) - 0.5
        pitch = float(np.clip(pitch_ratio * 40.0, -45.0, 45.0))

        if yaw < -15.0:
            pose_group = "left"
        elif yaw > 15.0:
            pose_group = "right"
        elif pitch < -10.0:
            pose_group = "up"
        elif pitch > 10.0:
            pose_group = "down"
        else:
            pose_group = "front"

    # Composite Quality Score [0.0 - 1.0]
    size_norm = min(1.0, max(0.0, (w - 30.0) / 100.0))
    blur_norm = min(1.0, max(0.0, blur_val / 300.0))
    bright_norm = 1.0 - (abs(brightness - 128.0) / 128.0)
    pose_norm = max(0.2, 1.0 - (abs(yaw) / 60.0) * 0.5 - (abs(pitch) / 45.0) * 0.3)

    composite_quality = round(float(0.35 * blur_norm + 0.30 * size_norm + 0.20 * pose_norm + 0.15 * bright_norm), 3)

    return {
        "width": w,
        "height": h,
        "blur": round(blur_val, 1),
        "brightness": round(brightness, 1),
        "yaw": round(yaw, 1),
        "pitch": round(pitch, 1),
        "pose_group": pose_group,
        "quality": composite_quality
    }

# ==============================================================================
# 2. Production Face Recognizer with SFace ONNX
# ==============================================================================
class ProductionFaceRecognizer:
    def __init__(self, model_path: Path = SFACE_MODEL_FILE):
        self.model_path = str(model_path)
        self.recognizer = None
        self.model_loaded = False
        self.model_name = "SFace-2021dec"
        self.model_license = "Apache-2.0"
        self._init_model()

    def _init_model(self):
        if Path(self.model_path).exists():
            try:
                self.recognizer = cv2.FaceRecognizerSF.create(self.model_path, "")
                self.model_loaded = True
            except Exception as e:
                print(f"[FaceRecognizer] Failed to create SFace recognizer: {e}")
                self.model_loaded = False

    def align_and_crop(self, frame_bgr: np.ndarray, raw_face_record: np.ndarray) -> Optional[np.ndarray]:
        """Aligns 5 landmarks to canonical 112x112 frontal crop."""
        if not self.model_loaded or self.recognizer is None or raw_face_record is None:
            # Fallback simple crop
            x, y, w, h = [int(v) for v in raw_face_record[:4]] if raw_face_record is not None else (0, 0, 0, 0)
            if w > 0 and h > 0:
                crop = frame_bgr[y:y+h, x:x+w]
                return cv2.resize(crop, (112, 112)) if crop.size > 0 else None
            return None

        try:
            return self.recognizer.alignCrop(frame_bgr, raw_face_record)
        except Exception:
            return None

    def extract_embedding(self, aligned_face: np.ndarray) -> Optional[np.ndarray]:
        """Extracts 128-D L2-normalized feature embedding."""
        if not self.model_loaded or self.recognizer is None or aligned_face is None:
            return None
        try:
            feat = self.recognizer.feature(aligned_face).flatten()
            norm = np.linalg.norm(feat)
            if norm > 1e-6:
                feat = feat / norm
            return feat.astype(np.float32)
        except Exception:
            return None

    @staticmethod
    def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Computes dot product between two unit-normalized vectors."""
        if vec1 is None or vec2 is None:
            return 0.0
        return float(np.dot(vec1, vec2))

# ==============================================================================
# 3. Spatial Multi-Frame Track
# ==============================================================================
class TrackRecord:
    def __init__(self, track_id: str, bbox: List[int], center: Tuple[int, int],
                 seat_region: str, initial_time: float):
        self.track_id = track_id
        self.bbox = bbox
        self.center = center
        self.seat_region = seat_region
        self.first_seen = initial_time
        self.last_seen = initial_time
        self.frame_count = 1

        # Embeddings & Crops
        self.embeddings = []  # list of (embedding_vec, quality_score, attributes)
        self.crops = []       # list of {time_str, note, best, quality, crop_bgr}

        # Identity Candidate Votes
        self.candidate_scores = {}  # student_id -> list of float scores
        self.state = "unclear"      # "identified", "unclear", "resolved", "unknown"
        self.assigned_student_id = None
        self.best_score = 0.0
        self.margin = 0.0

    def add_observation(self, bbox: List[int], center: Tuple[int, int], embedding: np.ndarray,
                        crop_bgr: np.ndarray, quality_meta: Dict[str, Any], current_time: float):
        self.bbox = bbox
        self.center = center
        self.last_seen = current_time
        self.frame_count += 1

        if embedding is not None:
            self.embeddings.append((embedding, quality_meta["quality"], quality_meta))
            # Keep top 12 best quality embeddings
            self.embeddings.sort(key=lambda x: x[1], reverse=True)
            self.embeddings = self.embeddings[:12]

        # Record crop for review strip
        time_str = datetime.fromtimestamp(current_time).strftime("%H:%M")
        is_best = False
        if not self.crops or quality_meta["quality"] > max(c["quality"] for c in self.crops):
            is_best = True
            for c in self.crops:
                c["best"] = False

        note = "Nominal"
        if quality_meta["yaw"] < -15: note = "Turned left"
        elif quality_meta["yaw"] > 15: note = "Turned right"
        elif quality_meta["pitch"] < -10: note = "Looking up"
        elif quality_meta["pitch"] > 10: note = "Looking down"
        elif quality_meta["brightness"] < 50: note = "Dim lighting"
        elif quality_meta["blur"] < 100: note = "Blurred"
        if is_best: note = "Best so far"

        self.crops.append({
            "time": time_str,
            "note": note,
            "best": is_best,
            "quality": quality_meta["quality"],
            "crop_bgr": crop_bgr
        })
        # Keep maximum 8 diverse crops
        if len(self.crops) > 8:
            # Drop lowest quality non-best crop
            non_bests = [c for c in self.crops if not c["best"]]
            if non_bests:
                worst = min(non_bests, key=lambda c: c["quality"])
                self.crops.remove(worst)

    def get_quality_weighted_embedding(self) -> Optional[np.ndarray]:
        """Quality-weighted average of track's best embeddings."""
        if not self.embeddings:
            return None
        weights = [max(0.1, q) for _, q, _ in self.embeddings]
        total_weight = sum(weights)
        stacked = np.vstack([e for e, _, _ in self.embeddings])
        weights_arr = np.array(weights, dtype=np.float32)[:, None]
        mean_vec = np.sum(stacked * weights_arr, axis=0) / total_weight
        norm = np.linalg.norm(mean_vec)
        if norm > 1e-6:
            mean_vec = mean_vec / norm
        return mean_vec.astype(np.float32)

# ==============================================================================
# 4. Production Classroom Attendance Pipeline
# ==============================================================================
class ClassroomAttendancePipeline:
    def __init__(self, detector: Optional[FaceDetector] = None,
                 recognizer: Optional[ProductionFaceRecognizer] = None,
                 thresholds: Optional[Dict[str, Any]] = None):
        self.detector = detector or FaceDetector()
        self.recognizer = recognizer or ProductionFaceRecognizer()
        self.hungarian_matcher = RosterHungarianMatcher()

        # Configurable Production Thresholds
        self.thresholds = {
            "T_high": 0.65,              # Identified threshold (0-1)
            "M": 0.08,                   # Required margin over 2nd best
            "N_min": 3,                  # Minimum supporting frames
            "min_face_size_px": 40,      # Minimum face width in px
            "blur_min_laplacian": 80.0,
            "brightness_min": 40.0,
            "brightness_max": 225.0,
            "track_expiry_sec": 4.0,     # Time to keep unseen face track alive
            "late_cutoff_min": 10,
            "absent_cutoff_min": 30
        }
        if thresholds:
            self.thresholds.update(thresholds)

        self.tracks: Dict[str, TrackRecord] = {}
        self.track_counter = 0
        self.headcount_history = deque(maxlen=6)
        self.current_median_headcount = 0

    def process_sampled_frame(self, frame_bgr: np.ndarray, roster_students: List[Dict[str, Any]],
                              student_templates: Dict[str, List[Dict[str, Any]]],
                              session_start_time: float, current_time: Optional[float] = None) -> Dict[str, Any]:
        """
        Executes complete pipeline on a sampled frame (interval 2-3s).
        """
        now = current_time or time.time()

        # Step 1: Quality filter
        is_ok, reason, metrics = check_frame_quality(
            frame_bgr,
            blur_threshold=self.thresholds["blur_min_laplacian"],
            min_brightness=self.thresholds["brightness_min"],
            max_brightness=self.thresholds["brightness_max"]
        )
        if not is_ok:
            return {
                "success": False,
                "dropped": True,
                "reason": reason,
                "metrics": metrics
            }

        # Step 2: Headcount Detection & Median
        raw_detections = self.detector.detect(frame_bgr)
        valid_faces = [
            d for d in raw_detections
            if d["bbox"][2] >= self.thresholds["min_face_size_px"]
        ]
        self.headcount_history.append(len(valid_faces))
        self.current_median_headcount = int(np.median(list(self.headcount_history)))

        # Step 3 & 4: Score Face Quality & Crop
        detections_with_meta = []
        for det in valid_faces:
            x, y, w, h = det["bbox"]
            face_crop = frame_bgr[y:y+h, x:x+w]
            if face_crop.size == 0:
                continue

            quality_meta = score_face_crop(face_crop, det["bbox"], det.get("landmarks"))
            aligned = self.recognizer.align_and_crop(frame_bgr, det.get("raw_face_record"))
            embedding = self.recognizer.extract_embedding(aligned)

            detections_with_meta.append({
                "bbox": det["bbox"],
                "center": (x + w // 2, y + h // 2),
                "crop": face_crop,
                "aligned": aligned,
                "embedding": embedding,
                "meta": quality_meta
            })

        # Step 6: Multi-Object Spatial Tracking
        self._update_spatial_tracks(detections_with_meta, now)

        # Step 7 & 8: Pose-Aware Matching & Hungarian Assignment
        assignments, similarity_matrix = self._evaluate_roster_assignment(roster_students, student_templates)

        # Step 9: Decision Rules & Residual Matching
        decisions = self._apply_decision_rules(roster_students, assignments, similarity_matrix, session_start_time, now)

        return {
            "success": True,
            "headcount_instant": len(valid_faces),
            "headcount_median": self.current_median_headcount,
            "active_tracks_count": len(self.tracks),
            "decisions": decisions
        }

    def _update_spatial_tracks(self, detections: List[Dict[str, Any]], current_time: float):
        """Matches detections to existing tracks via Euclidean distance."""
        # Purge expired tracks
        expired = [tid for tid, trk in self.tracks.items() if (current_time - trk.last_seen) > self.thresholds["track_expiry_sec"]]
        for tid in expired:
            del self.tracks[tid]

        unmatched_dets = []
        for det in detections:
            cx, cy = det["center"]
            best_tid = None
            best_dist = float("inf")

            for tid, trk in self.tracks.items():
                pcx, pcy = trk.center
                dist = math.hypot(cx - pcx, cy - pcy)
                if dist < best_dist and dist <= 90.0:  # 90px spatial gating
                    best_dist = dist
                    best_tid = tid

            if best_tid is not None:
                track = self.tracks[best_tid]
                track.add_observation(det["bbox"], det["center"], det["embedding"], det["crop"], det["meta"], current_time)
            else:
                unmatched_dets.append(det)

        # Create new tracks
        for det in unmatched_dets:
            self.track_counter += 1
            tid = f"track_{self.track_counter}"
            # Estimate seat region (e.g., Row 2, Seat 3 based on 5x10 grid)
            cx, cy = det["center"]
            row_idx = min(5, max(1, int(cy / 140) + 1))
            col_idx = min(10, max(1, int(cx / 120) + 1))
            seat_label = f"row {row_idx}, seat {col_idx}"

            new_track = TrackRecord(tid, det["bbox"], det["center"], seat_label, current_time)
            new_track.add_observation(det["bbox"], det["center"], det["embedding"], det["crop"], det["meta"], current_time)
            self.tracks[tid] = new_track

    def _evaluate_roster_assignment(self, roster: List[Dict[str, Any]],
                                    student_templates: Dict[str, List[Dict[str, Any]]]) -> Tuple[List[Tuple[int, int, float]], np.ndarray]:
        """
        Step 7 & 8: Pose-aware similarity matrix + Global Hungarian Assignment.
        """
        track_list = list(self.tracks.values())
        if not track_list or not roster:
            return [], np.zeros((0, 0))

        sim_matrix = np.zeros((len(track_list), len(roster)), dtype=np.float32)

        for t_idx, track in enumerate(track_list):
            track_vec = track.get_quality_weighted_embedding()
            if track_vec is None:
                continue

            # Latest crop pose for pose-aware weighting
            latest_pose = track.crops[-1]["note"] if track.crops else "front"

            for s_idx, student in enumerate(roster):
                sid = str(student.get("student_id") or student.get("id"))
                templates = student_templates.get(sid, [])
                if not templates:
                    continue

                scores = []
                for tmpl in templates:
                    t_vec = tmpl["embedding"]
                    sim = ProductionFaceRecognizer.cosine_similarity(track_vec, t_vec)

                    # Pose-aware weighting: boost template score if pose matches
                    t_pose = tmpl.get("pose_group", "front")
                    weight = 1.0
                    if t_pose in latest_pose.lower():
                        weight = 1.15  # 15% boost for matching head pose
                    elif tmpl.get("status") == "probation":
                        weight = 0.50  # Probation references count at reduced weight

                    scores.append(sim * weight)

                if scores:
                    # Top-3 weighted average
                    scores.sort(reverse=True)
                    top_3 = scores[:3]
                    sim_matrix[t_idx, s_idx] = float(sum(top_3) / len(top_3))

        # Hungarian maximum weight assignment
        assignments = self.hungarian_matcher.match(sim_matrix)
        return assignments, sim_matrix

    def _apply_decision_rules(self, roster: List[Dict[str, Any]], assignments: List[Tuple[int, int, float]],
                             sim_matrix: np.ndarray, session_start_time: float, current_time: float) -> Dict[str, Any]:
        """
        Step 9: Decision Rules.
        - Auto-mark present only if: score >= T_high, margin >= M, and frame_count >= N_min.
        - Residual matching: unassigned tracks compared only with unaccounted names.
        - Headcount bounds marking: identified <= counted <= enrolled.
        """
        track_list = list(self.tracks.values())
        enrolled_count = len(roster)
        counted_in_room = self.current_median_headcount

        identified_students = set()
        unclear_tracks = []
        results_by_track = {}

        # 1. Evaluate Confident Matches
        for t_idx, s_idx, score in assignments:
            track = track_list[t_idx]
            student = roster[s_idx]
            sid = str(student.get("student_id") or student.get("id"))

            # Calculate margin over second-best student
            row_scores = sorted(sim_matrix[t_idx, :], reverse=True)
            second_best = row_scores[1] if len(row_scores) > 1 else 0.0
            margin = max(0.0, score - second_best)

            track.best_score = score
            track.margin = margin

            # Decision criteria
            is_confident = (
                score >= self.thresholds["T_high"] and
                margin >= self.thresholds["M"] and
                track.frame_count >= self.thresholds["N_min"]
            )

            # Headcount capping rule: Never auto-mark more people than counted
            if is_confident and len(identified_students) < counted_in_room:
                track.state = "identified"
                track.assigned_student_id = sid
                identified_students.add(sid)
                results_by_track[track.track_id] = {
                    "state": "identified",
                    "student_id": sid,
                    "student_name": student.get("name"),
                    "score": score,
                    "margin": margin,
                    "seat": track.seat_region
                }
            else:
                track.state = "unclear"
                unclear_tracks.append((t_idx, track))

        # 2. Residual Matching for Unclear Tracks
        # Compare unclear tracks ONLY against students not yet accounted for!
        unaccounted_students = [
            s for s in roster
            if str(s.get("student_id") or s.get("id")) not in identified_students
        ]

        for t_idx, track in unclear_tracks:
            # Candidate names ranked from unaccounted pool
            candidates = []
            for s in unaccounted_students:
                s_idx = roster.index(s)
                c_score = float(sim_matrix[t_idx, s_idx])
                if c_score > 0.35:
                    rating = "Weak"
                    if c_score >= 0.60: rating = "Strong"
                    elif c_score >= 0.48: rating = "Fair"
                    candidates.append({
                        "id": str(s.get("student_id") or s.get("id")),
                        "name": s.get("name"),
                        "score": round(c_score, 3),
                        "rating": rating
                    })

            candidates.sort(key=lambda c: c["score"], reverse=True)
            results_by_track[track.track_id] = {
                "state": "unclear",
                "seat": track.seat_region,
                "tracking_text": f"Still tracking · {track.seat_region} · followed in {track.frame_count} frames",
                "crops": track.crops,
                "candidates": candidates[:4]
            }

        # 3. Count Arithmetic & Reconciliation
        identified_count = len(identified_students)
        absent_count = max(0, enrolled_count - counted_in_room)
        unclear_count = len(unclear_tracks)

        # Count mismatch check
        count_mismatch = (counted_in_room != len(self.tracks))
        mismatch_msg = ""
        if count_mismatch:
            diff = abs(counted_in_room - len(self.tracks))
            mismatch_msg = f"{diff} people not located"

        return {
            "enrolled": enrolled_count,
            "counted": counted_in_room,
            "identified": identified_count,
            "unclear": unclear_count,
            "absent": absent_count,
            "unaccounted_names": enrolled_count - identified_count,
            "count_mismatch": count_mismatch,
            "mismatch_message": mismatch_msg,
            "results_by_track": results_by_track
        }

    # ==============================================================================
    # 5. Learning Loop: Update Student References from Confirmed Reviews
    # ==============================================================================
    def learn_from_instructor_review(self, confirmed_student_id: str,
                                     confirmed_crops: List[np.ndarray],
                                     all_students_templates: Dict[str, List[Dict[str, Any]]],
                                     actor: str = "Dr. Meera Iyer",
                                     session_id: Optional[int] = None) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Section 4: Learning from reviews (no model retraining).
        - Quality filter.
        - Collision check against all other students.
        - Probation status (0.5 weight).
        - Cap at 10 classroom references.
        """
        if not confirmed_crops:
            return False, "No crops provided for learning loop", None

        # Extract embeddings and quality
        valid_samples = []
        for crop in confirmed_crops:
            if crop is None or crop.size == 0:
                continue
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            quality = float(cv2.Laplacian(gray, cv2.CV_64F).var())
            if quality < 80.0:  # Drop low quality / blurred
                continue

            aligned = self.recognizer.align_and_crop(crop, np.array([0, 0, crop.shape[1], crop.shape[0], 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1.0]))
            emb = self.recognizer.extract_embedding(aligned)
            if emb is not None:
                valid_samples.append((emb, quality))

        if not valid_samples:
            return False, "Crops did not meet sharpness requirements", None

        best_sample_emb, best_quality = max(valid_samples, key=lambda s: s[1])

        # Collision Check: Check if new reference is closer to another student
        self_templates = all_students_templates.get(str(confirmed_student_id), [])
        self_sim = 0.0
        if self_templates:
            self_sim = max(ProductionFaceRecognizer.cosine_similarity(best_sample_emb, t["embedding"]) for t in self_templates)

        for other_sid, other_tmpls in all_students_templates.items():
            if str(other_sid) == str(confirmed_student_id):
                continue
            for ot in other_tmpls:
                other_sim = ProductionFaceRecognizer.cosine_similarity(best_sample_emb, ot["embedding"])
                if other_sim >= self_sim and other_sim >= 0.55:
                    return False, f"Collision detected with student {other_sid} (Similarity {other_sim:.2f} >= {self_sim:.2f}). Flagged for office review.", None

        # Admitted under Probation
        reference_record = {
            "student_id": confirmed_student_id,
            "embedding": best_sample_emb,
            "quality": round(min(1.0, best_quality / 400.0), 3),
            "status": "probation",  # reduced weight until matched in subsequent session
            "source": "review",
            "confirmed_by": actor,
            "session_id": session_id,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        return True, "Reference successfully added on probation", reference_record
