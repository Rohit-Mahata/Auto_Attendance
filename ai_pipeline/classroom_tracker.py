import time
import math
from collections import deque, Counter
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import TRACK_EXPIRY_SECONDS, CONFIRMATION_FRAMES

class ClassroomTracker:
    """
    Multi-Object Spatial Face Tracker for Classrooms.
    Maintains identity persistence across student movements, head turns,
    and temporary occlusions.
    """
    def __init__(self, max_distance=85.0, expiry_seconds=TRACK_EXPIRY_SECONDS, min_confirm=CONFIRMATION_FRAMES):
        self.max_distance = float(max_distance)
        self.expiry_seconds = float(expiry_seconds)
        self.min_confirm = int(min_confirm)
        self.tracks = {}
        self.track_counter = 0

    def update_tracks(self, detected_faces):
        """
        Matches detected bounding boxes to existing tracks.
        Returns matched list of:
            (track_id, track_data, detection_item)
        """
        now = time.time()
        self._purge_expired_tracks(now)

        matched_results = []
        unmatched_detections = []

        # Find closest track for each detection
        for det in detected_faces:
            x, y, w, h = det["bbox"]
            cx, cy = x + w // 2, y + h // 2

            best_tid = None
            best_dist = float("inf")

            for tid, trk in self.tracks.items():
                pcx, pcy = trk["center"]
                d = math.hypot(cx - pcx, cy - pcy)
                if d < best_dist and d <= self.max_distance:
                    best_dist = d
                    best_tid = tid

            if best_tid is not None:
                track = self.tracks[best_tid]
                track["center"] = (cx, cy)
                track["bbox"] = det["bbox"]
                track["last_seen"] = now
                track["frames"] += 1
                matched_results.append((best_tid, track, det))
            else:
                unmatched_detections.append(det)

        # Create new tracks for unmatched detections
        for det in unmatched_detections:
            self.track_counter += 1
            tid = f"desk_{self.track_counter}"
            x, y, w, h = det["bbox"]
            cx, cy = x + w // 2, y + h // 2

            new_track = {
                "track_id": tid,
                "center": (cx, cy),
                "bbox": det["bbox"],
                "first_seen": now,
                "last_seen": now,
                "frames": 1,
                "history": deque(maxlen=10),
                "confirmed_id": None,
                "confirmed_conf": 0.0,
                "unknown_count": 0
            }
            self.tracks[tid] = new_track
            matched_results.append((tid, new_track, det))

        return matched_results

    def record_vote(self, track_id, student_id, confidence, is_match):
        if track_id not in self.tracks:
            return

        track = self.tracks[track_id]
        track["history"].append({
            "student_id": student_id if is_match else None,
            "confidence": confidence,
            "is_match": is_match,
            "timestamp": time.time()
        })

        if not is_match or not student_id:
            track["unknown_count"] += 1
        else:
            track["unknown_count"] = 0

    def get_confirmed_identity(self, track_id):
        """
        Determines confirmed identity using temporal voting across recent frames.
        Returns: (confirmed_student_id, avg_confidence, is_confirmed: bool)
        """
        if track_id not in self.tracks:
            return None, 0.0, False

        track = self.tracks[track_id]
        history = list(track["history"])

        # Check valid positive votes
        positive_votes = [v for v in history if v["is_match"] and v["student_id"]]
        if not positive_votes:
            # If recently confirmed, maintain grace period of 5 frames
            if track["confirmed_id"] and track["unknown_count"] < 5:
                return track["confirmed_id"], track["confirmed_conf"], True
            track["confirmed_id"] = None
            return None, 0.0, False

        counts = Counter(v["student_id"] for v in positive_votes)
        top_id, count = counts.most_common(1)[0]

        if count >= self.min_confirm:
            confs = [v["confidence"] for v in positive_votes if v["student_id"] == top_id]
            avg_conf = round(sum(confs) / len(confs), 1) if confs else 0.0
            track["confirmed_id"] = top_id
            track["confirmed_conf"] = avg_conf
            track["unknown_count"] = 0
            return top_id, avg_conf, True

        # Grace period fallback
        if track["confirmed_id"] and track["unknown_count"] < 5:
            return track["confirmed_id"], track["confirmed_conf"], True

        return None, 0.0, False

    def _purge_expired_tracks(self, current_time):
        expired = [
            tid for tid, trk in self.tracks.items()
            if (current_time - trk["last_seen"]) > self.expiry_seconds
        ]
        for tid in expired:
            del self.tracks[tid]
