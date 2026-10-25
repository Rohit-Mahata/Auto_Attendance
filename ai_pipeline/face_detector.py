import os
import cv2
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import YUNET_MODEL_FILE, DEFAULT_DETECTION_CONFIDENCE

class FaceDetector:
    """
    Deep Learning Multi-Face Detector for Classroom Environments.
    Uses OpenCV YuNet ONNX with 5-point facial landmark alignment.
    Capable of detecting tilted, occluded, and distant faces down to 10x10 px.
    """
    def __init__(self, score_threshold=DEFAULT_DETECTION_CONFIDENCE, nms_threshold=0.3, top_k=50):
        self.score_threshold = float(score_threshold)
        self.nms_threshold = float(nms_threshold)
        self.top_k = int(top_k)
        self.detector = None
        self.model_loaded = False
        self.input_size = (640, 480)
        self.haar_fallback = None

        self._init_detector()

    def _init_detector(self):
        model_str = str(YUNET_MODEL_FILE)
        if os.path.exists(model_str):
            try:
                self.detector = cv2.FaceDetectorYN.create(
                    model_str,
                    "",
                    self.input_size,
                    self.score_threshold,
                    self.nms_threshold,
                    self.top_k
                )
                self.model_loaded = True
                print("[FaceDetector] Deep Learning YuNet detector initialized successfully (fixed 640x480).")
            except Exception as e:
                print(f"[FaceDetector] Error loading YuNet: {e}")
                self.model_loaded = False

        if not self.model_loaded:
            cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            self.haar_fallback = cv2.CascadeClassifier(cascade_path)
            print("[FaceDetector] Fallback to Haar Cascade.")

    def set_score_threshold(self, score):
        self.score_threshold = float(score)
        if self.detector:
            self.detector.setScoreThreshold(self.score_threshold)

    def detect(self, frame_bgr):
        """
        Detects all faces in frame using fixed 640x480 canonical input.
        Returns: list of dicts with scaled bboxes and landmarks.
        """
        if frame_bgr is None or frame_bgr.size == 0:
            return []

        orig_h, orig_w = frame_bgr.shape[:2]
        det_w, det_h = self.input_size

        if (orig_w, orig_h) != (det_w, det_h):
            resized = cv2.resize(frame_bgr, (det_w, det_h))
        else:
            resized = frame_bgr

        scale_x = orig_w / float(det_w)
        scale_y = orig_h / float(det_h)

        if self.model_loaded and self.detector:
            faces = None
            try:
                _, faces = self.detector.detect(resized)
            except Exception:
                faces = None

            if faces is None or len(faces) == 0:
                return []

            results = []
            for face in faces:
                x = max(0, int(face[0] * scale_x))
                y = max(0, int(face[1] * scale_y))
                bw = min(orig_w - x, int(face[2] * scale_x))
                bh = min(orig_h - y, int(face[3] * scale_y))
                score = float(face[14])

                # 5 landmarks scaled to original frame
                landmarks = []
                face_scaled = face.copy()
                face_scaled[0] = x
                face_scaled[1] = y
                face_scaled[2] = bw
                face_scaled[3] = bh

                for i in range(5):
                    lx = float(face[4 + 2 * i] * scale_x)
                    ly = float(face[5 + 2 * i] * scale_y)
                    landmarks.append((int(lx), int(ly)))
                    face_scaled[4 + 2 * i] = lx
                    face_scaled[5 + 2 * i] = ly

                face_scaled = np.ascontiguousarray(face_scaled.astype(np.float32))

                results.append({
                    "bbox": [x, y, bw, bh],
                    "score": score,
                    "landmarks": landmarks,
                    "raw_face_record": face_scaled
                })
            return results

        # Fallback Haar Cascade
        elif self.haar_fallback:
            gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
            raw_boxes = self.haar_fallback.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=4, minSize=(30, 30)
            )
            results = []
            for (x, y, bw, bh) in raw_boxes:
                results.append({
                    "bbox": [int(x), int(y), int(bw), int(bh)],
                    "score": 0.75,
                    "landmarks": None,
                    "raw_face_record": None
                })
            return results

        return []
