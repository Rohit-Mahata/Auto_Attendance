import os
import time
import socket
import threading
import urllib.parse
import cv2

def is_host_reachable(url_or_host, default_port=554, timeout=1.5):
    """Fast pre-flight check to prevent OpenCV from blocking for 30s on unreachable hosts."""
    try:
        url_str = str(url_or_host).strip()
        if "://" in url_str:
            parsed = urllib.parse.urlparse(url_str)
            host = parsed.hostname
            port = parsed.port or (443 if parsed.scheme == "https" else (554 if parsed.scheme == "rtsp" else 80))
        else:
            host = url_str
            port = default_port

        if not host:
            return False

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            s.connect((host, port))
            return True
    except Exception:
        return False

class ThreadedCCTVStream:
    """
    High-Performance Asynchronous RTSP / CCTV / Webcam stream reader.
    Continuously grabs the latest frame in a dedicated background thread,
    preventing network buffer latency drift.
    """
    def __init__(self, source="0"):
        self.raw_source = source
        self.source = self._normalize_source(source)
        self.cap = None
        self.grabbed = False
        self.frame = None
        self.is_running = False
        self.lock = threading.Lock()
        self.thread = None
        self.last_frame_time = 0.0
        self.fps = 0.0
        self.fps_counter = 0
        self.fps_timer = time.time()
        self.status_message = "Idle"

    def _normalize_source(self, src):
        if isinstance(src, int):
            return src
        s = str(src).strip()
        if s.isdigit():
            return int(s)
        if s.lower() in ("ipcam", "ip_camera", "android", "phone"):
            try:
                from ip_camera_stream import load_ip_camera_config, build_ip_camera_url
                cfg = load_ip_camera_config()
                if cfg.get("custom_url"):
                    return cfg["custom_url"]
                return build_ip_camera_url(cfg.get("ip", "192.168.1.100"), cfg.get("port", 8080), cfg.get("path", "/video"))
            except Exception:
                return "http://192.168.1.100:8080/video"
        return s

    def start(self):
        if self.is_running:
            return True

        self.status_message = "Connecting to camera source..."
        # If network camera, verify host reachability first
        if isinstance(self.source, str) and ("://" in self.source):
            if not is_host_reachable(self.source):
                self.status_message = f"Camera unreachable: {self.source}"
                return False

        # If HTTP or HTTPS IP camera stream, use the resilient AndroidIPCameraStream engine
        if isinstance(self.source, str) and (self.source.lower().startswith("http://") or self.source.lower().startswith("https://")):
            from ip_camera_stream import AndroidIPCameraStream
            self._ipcam_delegate = AndroidIPCameraStream(custom_url=self.source)
            ok = self._ipcam_delegate.start()
            self.is_running = ok
            self.status_message = self._ipcam_delegate.status_message
            return ok

        if isinstance(self.source, int):
            # Windows DirectShow backend for instant webcam capture
            self.cap = cv2.VideoCapture(self.source, cv2.CAP_DSHOW)
            if not self.cap.isOpened():
                self.cap = cv2.VideoCapture(self.source)
        elif isinstance(self.source, str) and self.source.lower().startswith("rtsp://"):
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
            self.cap = cv2.VideoCapture(self.source, cv2.CAP_FFMPEG)
        else:
            self.cap = cv2.VideoCapture(self.source)

        if not self.cap or not self.cap.isOpened():
            self.status_message = f"Failed to open video source: {self.source}"
            return False

        try:
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except Exception:
            pass

        self.is_running = True
        self.status_message = "Streaming active"
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
        return True

    def _capture_loop(self):
        while self.is_running and self.cap and self.cap.isOpened():
            try:
                ret, frame = self.cap.read()
                if not ret or frame is None:
                    time.sleep(0.02)
                    continue

                with self.lock:
                    self.frame = frame
                    self.grabbed = True
                    self.last_frame_time = time.time()
                    self.fps_counter += 1
            except Exception:
                time.sleep(0.03)
                continue

            # Compute real FPS every 1 second
            now = time.time()
            if now - self.fps_timer >= 1.0:
                self.fps = round(self.fps_counter / max(0.1, (now - self.fps_timer)), 1)
                self.fps_counter = 0
                self.fps_timer = now

        self.is_running = False

    def read(self):
        if getattr(self, "_ipcam_delegate", None):
            return self._ipcam_delegate.read()
        with self.lock:
            if not self.grabbed or self.frame is None:
                return False, None
            return True, self.frame.copy()

    def get_fps(self):
        if getattr(self, "_ipcam_delegate", None):
            return self._ipcam_delegate.get_fps()
        return self.fps

    def stop(self):
        self.is_running = False
        if getattr(self, "_ipcam_delegate", None):
            try:
                self._ipcam_delegate.stop()
            except Exception:
                pass
            self._ipcam_delegate = None

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
        self.cap = None
        self.grabbed = False
        self.frame = None
        self.status_message = "Disconnected"
