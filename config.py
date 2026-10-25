import os
from pathlib import Path

# Base Paths
ROHIT_DIR = Path(__file__).resolve().parent
DATA_DIR = ROHIT_DIR / "data"
STUDENTS_DIR = DATA_DIR / "students"
MODELS_DIR = ROHIT_DIR / "ai_pipeline" / "models"
DB_PATH = DATA_DIR / "production_attendance.db"
PRODUCTION_DB_PATH = DB_PATH
EMBEDDINGS_PATH = DATA_DIR / "embeddings.json"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
STUDENTS_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# Model filenames
YUNET_MODEL_FILE = MODELS_DIR / "face_detection_yunet_2023mar.onnx"
SFACE_MODEL_FILE = MODELS_DIR / "face_recognition_sface_2021dec.onnx"

# Official OpenCV Model Zoo URLs
YUNET_DOWNLOAD_URL = (
    "https://github.com/opencv/opencv_zoo/raw/main/models/"
    "face_detection_yunet/face_detection_yunet_2023mar.onnx"
)
SFACE_DOWNLOAD_URL = (
    "https://github.com/opencv/opencv_zoo/raw/main/models/"
    "face_recognition_sface/face_recognition_sface_2021dec.onnx"
)

# AI Recognition Thresholds
DEFAULT_DETECTION_CONFIDENCE = 0.65  # YuNet score threshold (0.0 to 1.0)
DEFAULT_COSINE_SIMILARITY_THRESHOLD = 0.58  # SFace cosine similarity threshold (0.0 to 1.0)
DEFAULT_MAX_DISTANCE_LBPH = 65.0  # Fallback LBPH distance

# Classroom Tracking Parameters
TRACK_EXPIRY_SECONDS = 3.0  # Time to keep unseen face track alive
CONFIRMATION_FRAMES = 3     # Consecutive matching frames to confirm attendance

# CCTV Stream Defaults
DEFAULT_CAMERA_SOURCE = "0"  # 0 for webcam or rtsp://...
RTSP_TRANSPORT_TCP = True
AUTO_RECONNECT_INTERVAL = 5.0
