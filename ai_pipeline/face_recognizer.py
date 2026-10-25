import os
import json
import cv2
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import (
    SFACE_MODEL_FILE,
    EMBEDDINGS_PATH,
    DEFAULT_COSINE_SIMILARITY_THRESHOLD
)

class FaceRecognizer:
    """
    Deep Learning Facial Feature Extractor & Cosine Matcher for Classroom Attendance.
    Uses OpenCV SFace ONNX model to extract 128-dimensional normalized embeddings.
    """
    def __init__(self, similarity_threshold=DEFAULT_COSINE_SIMILARITY_THRESHOLD):
        self.similarity_threshold = float(similarity_threshold)
        self.recognizer = None
        self.model_loaded = False
        self.student_embeddings = {}  # student_id -> np.ndarray of shape (128,)

        self._init_recognizer()
        self.load_enrolled_embeddings()

    def _init_recognizer(self):
        model_str = str(SFACE_MODEL_FILE)
        if os.path.exists(model_str):
            try:
                self.recognizer = cv2.FaceRecognizerSF.create(model_str, "")
                self.model_loaded = True
                print("[FaceRecognizer] Deep Learning SFace recognizer initialized.")
            except Exception as e:
                print(f"[FaceRecognizer] Error loading SFace: {e}")
                self.model_loaded = False

    def load_enrolled_embeddings(self):
        if not EMBEDDINGS_PATH.exists():
            self.student_embeddings = {}
            return

        try:
            with open(EMBEDDINGS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.student_embeddings = {
                    sid: np.array(vec, dtype=np.float32)
                    for sid, vec in data.items()
                }
            print(f"[FaceRecognizer] Loaded {len(self.student_embeddings)} enrolled student biometric profiles.")
        except Exception as e:
            print(f"[FaceRecognizer] Error loading embeddings from {EMBEDDINGS_PATH}: {e}")
            self.student_embeddings = {}

    def save_enrolled_embeddings(self):
        try:
            serializable = {
                sid: vec.tolist()
                for sid, vec in self.student_embeddings.items()
            }
            with open(EMBEDDINGS_PATH, "w", encoding="utf-8") as f:
                json.dump(serializable, f, indent=2)
            print(f"[FaceRecognizer] Saved {len(self.student_embeddings)} student embeddings to disk.")
        except Exception as e:
            print(f"[FaceRecognizer] Error saving embeddings: {e}")

    def align_and_crop(self, frame_bgr, raw_face_record):
        """
        Aligns the face using 5 landmarks to canonical 112x112 frontal geometry.
        Crucial for CCTV where camera is angled above students.
        """
        if not self.model_loaded or self.recognizer is None or raw_face_record is None:
            # Fallback simple crop
            x, y, w, h = [int(v) for v in raw_face_record[:4]] if raw_face_record is not None else (0,0,0,0)
            if w > 0 and h > 0:
                crop = frame_bgr[y:y+h, x:x+w]
                return cv2.resize(crop, (112, 112)) if crop.size > 0 else None
            return None

        try:
            aligned_face = self.recognizer.alignCrop(frame_bgr, raw_face_record)
            return aligned_face
        except Exception as e:
            print(f"[FaceRecognizer] AlignCrop failed: {e}")
            return None

    def extract_feature(self, aligned_face):
        """
        Extracts 128-dimensional L2-normalized embedding vector.
        """
        if not self.model_loaded or self.recognizer is None or aligned_face is None:
            return None

        try:
            if not isinstance(aligned_face, np.ndarray) or aligned_face.size == 0:
                return None

            if aligned_face.shape[0] != 112 or aligned_face.shape[1] != 112:
                aligned_face = cv2.resize(aligned_face, (112, 112))

            if aligned_face.dtype != np.uint8:
                aligned_face = aligned_face.astype(np.uint8)

            aligned_face = np.ascontiguousarray(aligned_face)

            feat = self.recognizer.feature(aligned_face)
            if feat is None:
                return None
            feat = feat.flatten()
            norm = np.linalg.norm(feat)
            if norm > 1e-6:
                feat = feat / norm
            return feat
        except Exception:
            try:
                self._init_recognizer()
            except Exception:
                pass
            return None

    def enroll_student(self, student_id, feature_vectors):
        """
        Calculates normalized centroid embedding from multiple sample vectors.
        """
        if not feature_vectors:
            return False

        student_id_str = str(student_id).strip()
        stacked = np.vstack(feature_vectors)
        mean_vector = np.mean(stacked, axis=0)
        norm = np.linalg.norm(mean_vector)
        if norm > 1e-6:
            mean_vector = mean_vector / norm

        self.student_embeddings[student_id_str] = mean_vector.astype(np.float32)
        self.save_enrolled_embeddings()
        return True

    def delete_enrolled_student(self, student_id):
        student_id_str = str(student_id).strip()
        if student_id_str in self.student_embeddings:
            del self.student_embeddings[student_id_str]
            self.save_enrolled_embeddings()

    def match_probe(self, probe_feature, min_threshold=None):
        """
        Evaluates probe against enrolled student database via Cosine Similarity.
        Returns: (best_student_id, confidence_percent, is_match)
        """
        if probe_feature is None or not self.student_embeddings:
            return None, 0.0, False

        if min_threshold is None:
            min_threshold = self.similarity_threshold

        best_sid = None
        best_sim = -1.0

        for sid, ref_vec in self.student_embeddings.items():
            # Cosine similarity between two unit vectors is their dot product
            sim = float(np.dot(probe_feature, ref_vec))
            if sim > best_sim:
                best_sim = sim
                best_sid = sid

        conf_pct = round(max(0.0, min(100.0, best_sim * 100.0)), 1)
        if best_sid is not None and best_sim >= min_threshold:
            return best_sid, conf_pct, True

        return None, conf_pct, False
