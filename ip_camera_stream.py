"""
Android IP Camera Stream Integration Module
------------------------------------------
Connects to video streams broadcasted by Android phones over Wi-Fi/LAN (such as
the 'IP Webcam' app, 'DroidCam', RTSP Camera, or any HTTP/RTSP stream).

Features:
- Fast TCP pre-flight reachability test (never blocks the UI or main thread).
- Dual ingestion engine:
    1. Direct OpenCV VideoCapture with low-latency buffer settings.
    2. Fallback pure-Python HTTP MJPEG boundary parser (ensures 100% compatibility
       with Android IP Webcam apps regardless of Windows OpenCV ffmpeg build quirks).
    3. Fast snapshot fallback (/shot.jpg) for unstable Wi-Fi networks.
- Thread-safe zero-latency frame buffer (always serves the latest real-time frame).
- Standalone CLI preview with live face detection for quick camera testing.
"""

import sys
import os
import time
import socket
import json
import threading
import argparse
import urllib.request
import urllib.parse
import ssl
from pathlib import Path
import numpy as np
import cv2

# Global unverified SSL context for camera streams using self-signed certificates
SSL_UNVERIFIED_CTX = ssl._create_unverified_context()

# Project root path resolution
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CONFIG_FILE = DATA_DIR / "camera_config.json"


def load_ip_camera_config():
    """Load saved IP camera settings from disk."""
    default_cfg = {
        "source_type": "webcam",      # 'webcam', 'ip_camera', or 'cctv'
        "ip": "192.168.1.100",
        "port": 8080,
        "path": "/video",
        "custom_url": "",
        "auto_reconnect": True,
        "last_tested": None,
        "last_status": "Idle"
    }
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                default_cfg.update(saved)
    except Exception as e:
        print(f"[IPCam] Warning loading camera config: {e}")
    return default_cfg


def save_ip_camera_config(config_data):
    """Save IP camera settings to disk."""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        current = load_ip_camera_config()
        current.update(config_data)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=2)
        return True
    except Exception as e:
        print(f"[IPCam] Error saving camera config: {e}")
        return False


def test_ip_port_reachability(ip, port, timeout=1.5):
    """
    Fast pre-flight TCP socket check. Returns True if IP and port are reachable,
    preventing long blocking timeouts in OpenCV.
    """
    try:
        host = str(ip).strip()
        # Clean protocol prefix if accidentally included in IP
        if "://" in host:
            parsed = urllib.parse.urlparse(host)
            host = parsed.hostname or host
            if parsed.port:
                port = parsed.port

        port = int(port)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            s.connect((host, port))
            return True
    except Exception:
        return False


def build_ip_camera_url(ip, port=8080, path="/video", username="", password=""):
    """
    Builds a properly formatted URL for Android IP Camera streams.
    Handles HTTP, HTTPS, and RTSP Android camera apps.
    """
    raw = str(ip).strip()
    scheme = "http"
    host = raw
    if "://" in raw:
        parsed = urllib.parse.urlparse(raw)
        scheme = parsed.scheme or "http"
        host = parsed.hostname or raw
        if parsed.port:
            port = parsed.port
        if parsed.path and parsed.path not in ("/", ""):
            path = parsed.path

    clean_path = str(path).strip()
    if clean_path.lower() in ("auto", "none", "", "/video") and (scheme == "https" or int(port) == 4444):
        clean_path = "/video/mjpeg"
    elif clean_path.lower() in ("auto", "none", ""):
        clean_path = "/video/mjpeg"
    elif not clean_path.startswith("/"):
        clean_path = "/" + clean_path

    port_clean = int(port)
    auth = ""
    if username:
        if password:
            auth = f"{urllib.parse.quote(username)}:{urllib.parse.quote(password)}@"
        else:
            auth = f"{urllib.parse.quote(username)}@"

    return f"{scheme}://{auth}{host}:{port_clean}{clean_path}"


def get_local_wifi_ip():
    """Detect local IPv4 address on active Wi-Fi or primary network interface."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def _probe_single_mjpeg_url(url, timeout=2.5):
    """Attempt to decode at least one JPEG frame from an HTTP/HTTPS MJPEG stream."""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "*/*"
        })
        kwargs = {}
        if url.lower().startswith("https://"):
            kwargs["context"] = SSL_UNVERIFIED_CTX

        with urllib.request.urlopen(req, timeout=timeout, **kwargs) as resp:
            data = b""
            t0 = time.time()
            while time.time() - t0 < timeout:
                chunk = resp.read(4096)
                if not chunk:
                    break
                data += chunk
                a = data.find(b"\xff\xd8")
                b = data.find(b"\xff\xd9")
                if a != -1 and b != -1 and b > a:
                    jpg = data[a:b+2]
                    img = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                    if img is not None and img.size > 0:
                        h, w = img.shape[:2]
                        return True, w, h
    except Exception:
        pass
    return False, 0, 0


def _probe_single_opencv_url(url, is_rtsp=False, timeout=2.0):
    """Attempt to grab a frame via OpenCV."""
    cap = None
    try:
        if is_rtsp or url.lower().startswith("rtsp://"):
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
            cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
        else:
            cap = cv2.VideoCapture(url)

        if cap and cap.isOpened():
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            t0 = time.time()
            while time.time() - t0 < timeout:
                ret, frame = cap.read()
                if ret and frame is not None and frame.size > 0:
                    h, w = frame.shape[:2]
                    cap.release()
                    return True, w, h
                time.sleep(0.04)
    except Exception:
        pass
    finally:
        if cap:
            try:
                cap.release()
            except Exception:
                pass
    return False, 0, 0


def test_ip_camera_stream(ip, port=8080, path="/video", custom_url="", timeout=3.0):
    """
    Resilient, Multi-Format Android IP Camera stream tester with Auto-Detection.
    Tests reachability, auto-probes common Android streaming protocols (IP Webcam,
    DroidCam, RTSP, MJPEG), and returns detected format & resolution.
    """
    local_wifi_ip = get_local_wifi_ip()
    target_url = custom_url.strip() if custom_url and custom_url.strip() else build_ip_camera_url(ip, port, path)

    # 1. Parse target host, port, and scheme
    parsed = urllib.parse.urlparse(target_url)
    scheme = parsed.scheme or ("https" if "https://" in str(ip).lower() else "http")
    host = parsed.hostname or str(ip).strip().replace("https://", "").replace("http://", "").split("/")[0].split(":")[0]
    port_to_check = parsed.port or int(port or 8080)

    # 2. Fast TCP pre-flight socket test
    is_open = test_ip_port_reachability(host, port_to_check, timeout=1.5)
    if not is_open:
        return {
            "success": False,
            "url": target_url,
            "local_wifi_ip": local_wifi_ip,
            "message": (
                f"Cannot connect to {host}:{port_to_check}. "
                f"Your computer is on Wi-Fi IP '{local_wifi_ip}'. "
                f"Please ensure phone is on the same Wi-Fi and verify the IP shown on phone."
            ),
            "resolution": [0, 0],
            "fps": 0.0
        }

    # 3. Construct candidate URLs to probe
    candidates = []
    clean_path = "/video/mjpeg" if str(path).strip().lower() in ("auto", "", "none") else str(path).strip()
    if not clean_path.startswith("/"):
        clean_path = "/" + clean_path

    if custom_url and custom_url.strip():
        candidates.append((custom_url.strip(), "Custom URL", False))
    else:
        schemes_to_try = [scheme] if scheme == "https" else ["http", "https"]
        for s in schemes_to_try:
            candidates.append((f"{s}://{host}:{port_to_check}/video/mjpeg", f"{s.upper()} (/video/mjpeg)", False))
            if clean_path != "/video/mjpeg":
                candidates.append((f"{s}://{host}:{port_to_check}{clean_path}", f"{s.upper()} ({clean_path})", False))
            candidates.append((f"{s}://{host}:{port_to_check}/video", f"{s.upper()} (/video)", False))
            candidates.append((f"{s}://{host}:{port_to_check}/mjpegfeed", f"{s.upper()} (/mjpegfeed)", False))
            candidates.append((f"{s}://{host}:{port_to_check}/videofeed", f"{s.upper()} (/videofeed)", False))
            candidates.append((f"{s}://{host}:{port_to_check}/shot.jpg", f"{s.upper()} (/shot.jpg)", False))
        candidates.append((f"rtsp://{host}:{port_to_check}/h264_pcm.sdp", "RTSP (h264_pcm.sdp)", True))
        candidates.append((f"rtsp://{host}:{port_to_check}/live", "RTSP (/live)", True))
        candidates.append((f"rtsp://{host}:{port_to_check}/", "RTSP Root (/)", True))

    # 4. Probe candidates
    for cand_url, cand_name, is_rtsp in candidates:
        if not cand_url:
            continue
        cand_str = str(cand_url).strip()
        try:
            # A. Try MJPEG probe for HTTP and HTTPS
            if not is_rtsp and (cand_str.startswith("http://") or cand_str.startswith("https://")):
                ok, w, h = _probe_single_mjpeg_url(cand_str, timeout=1.5)
                if ok:
                    det_path = urllib.parse.urlparse(cand_str).path or clean_path
                    return {
                        "success": True,
                        "url": cand_str,
                        "local_wifi_ip": local_wifi_ip,
                        "detected_path": det_path,
                        "message": f"Connected via {cand_name}! Resolution: {w}x{h}",
                        "resolution": [w, h],
                        "fps": 30.0
                    }

            # B. Try OpenCV probe for RTSP streams
            if is_rtsp or cand_str.startswith("rtsp://"):
                ok, w, h = _probe_single_opencv_url(cand_str, is_rtsp=True, timeout=1.5)
                if ok:
                    det_path = urllib.parse.urlparse(cand_str).path or clean_path
                    return {
                        "success": True,
                        "url": cand_str,
                        "local_wifi_ip": local_wifi_ip,
                        "detected_path": det_path,
                        "message": f"Connected via {cand_name}! Resolution: {w}x{h}",
                        "resolution": [w, h],
                        "fps": 30.0
                    }
        except Exception:
            continue

    # If port is open but none of the standard formats could be decoded
    return {
        "success": False,
        "url": target_url,
        "local_wifi_ip": local_wifi_ip,
        "message": (
            f"Port {port_to_check} is open on {host}, but video stream could not be decoded. "
            "Please ensure you clicked 'Start Server' in your camera app and check if authentication or a custom URL is required."
        ),
        "resolution": [0, 0],
        "fps": 0.0
    }


class AndroidIPCameraStream:
    """
    High-Performance, Thread-Safe Android IP Camera Client.
    Maintains a dedicated background worker thread that constantly flushes
    network buffers to provide 0ms latency live frames to attendance AI.
    """
    def __init__(self, ip="192.168.1.100", port=8080, path="/video", custom_url=""):
        self.ip = str(ip).strip()
        self.port = int(port)
        self.path = str(path).strip()
        self.custom_url = str(custom_url).strip()
        self.url = self.custom_url if self.custom_url else build_ip_camera_url(self.ip, self.port, self.path)

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
        self.status_message = "Initialized"
        self.reconnect_attempts = 0

    def start(self):
        """Starts the background capture loop."""
        if self.is_running:
            return True

        self.status_message = f"Connecting to {self.url}..."
        parsed = urllib.parse.urlparse(self.url)
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == "https" else (80 if parsed.scheme == "http" else 554))

        # Quick pre-flight socket test
        if host and not test_ip_port_reachability(host, port, timeout=1.5):
            self.status_message = f"Unreachable: {host}:{port}. Check phone Wi-Fi connection."
            return False

        # Start background worker
        self.is_running = True
        self.thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.thread.start()

        # Wait up to 2 seconds for initial frame
        t0 = time.time()
        while time.time() - t0 < 2.0:
            if self.grabbed and self.frame is not None:
                self.status_message = "Live streaming active"
                return True
            time.sleep(0.05)

        return True

    def _worker_loop(self):
        """Continuously pulls frames in background to prevent buffer latency."""
        while self.is_running:
            # 1. If HTTP or HTTPS MJPEG, use the resilient pure Python MJPEG stream reader
            if self.url.lower().startswith("http://") or self.url.lower().startswith("https://"):
                self._http_mjpeg_fallback_loop()
                if not self.is_running:
                    break

            # 2. If RTSP or if MJPEG reader didn't connect, attempt OpenCV capture
            try:
                if self.url.lower().startswith("rtsp://"):
                    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
                    self.cap = cv2.VideoCapture(self.url, cv2.CAP_FFMPEG)
                else:
                    self.cap = cv2.VideoCapture(self.url)

                if self.cap and self.cap.isOpened():
                    try:
                        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    except Exception:
                        pass

                    self.status_message = "Streaming active"
                    fail_count = 0

                    while self.is_running and self.cap.isOpened():
                        ret, frame = self.cap.read()
                        if not ret or frame is None:
                            fail_count += 1
                            if fail_count > 30:
                                break
                            time.sleep(0.03)
                            continue

                        fail_count = 0
                        with self.lock:
                            self.frame = frame
                            self.grabbed = True
                            self.last_frame_time = time.time()
                            self.fps_counter += 1

                        # Compute real FPS every 1 second
                        now = time.time()
                        if now - self.fps_timer >= 1.0:
                            self.fps = round(self.fps_counter / max(0.1, (now - self.fps_timer)), 1)
                            self.fps_counter = 0
                            self.fps_timer = now

                    if self.cap:
                        self.cap.release()
            except Exception as e:
                self.status_message = f"Capture loop notice: {e}"

            if not self.is_running:
                break

            # Reconnection backoff
            self.reconnect_attempts += 1
            self.status_message = f"Reconnecting to phone (attempt {self.reconnect_attempts})..."
            time.sleep(1.0)

    def _http_mjpeg_fallback_loop(self):
        """
        Pure Python MJPEG stream parser for Android IP Webcam apps.
        Directly reads HTTP/HTTPS multipart boundaries and decodes JPEG bytes.
        Supports self-signed SSL certificates without verification errors.
        """
        try:
            req = urllib.request.Request(self.url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "Accept": "*/*"
            })
            kwargs = {}
            if self.url.lower().startswith("https://"):
                kwargs["context"] = SSL_UNVERIFIED_CTX

            try:
                stream = urllib.request.urlopen(req, timeout=3.5, **kwargs)
            except urllib.error.HTTPError as he:
                if he.code == 404 and self.url.endswith("/video"):
                    self.url = self.url + "/mjpeg"
                    req = urllib.request.Request(self.url, headers={"User-Agent": "Mozilla/5.0", "Accept": "*/*"})
                    stream = urllib.request.urlopen(req, timeout=3.5, **kwargs)
                else:
                    raise

            with stream:
                bytes_data = b""
                fail_streak = 0
                self.status_message = "Live streaming active"
                while self.is_running and fail_streak < 25:
                    chunk = stream.read(4096)
                    if not chunk:
                        fail_streak += 1
                        time.sleep(0.02)
                        continue
                    bytes_data += chunk
                    a = bytes_data.find(b"\xff\xd8")  # JPEG start
                    b = bytes_data.find(b"\xff\xd9")  # JPEG end
                    if a != -1 and b != -1 and b > a:
                        jpg = bytes_data[a:b+2]
                        bytes_data = bytes_data[b+2:]
                        img = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                        if img is not None and img.size > 0:
                            fail_streak = 0
                            with self.lock:
                                self.frame = img
                                self.grabbed = True
                                self.last_frame_time = time.time()
                                self.fps_counter += 1

                            now = time.time()
                            if now - self.fps_timer >= 1.0:
                                self.fps = round(self.fps_counter / max(0.1, (now - self.fps_timer)), 1)
                                self.fps_counter = 0
                                self.fps_timer = now
        except Exception as e:
            self.status_message = f"Stream notice: {e}"

    def read(self):
        """Thread-safe fetch of the latest available video frame."""
        with self.lock:
            if not self.grabbed or self.frame is None:
                return False, None
            # Return fresh copy
            return True, self.frame.copy()

    def get_fps(self):
        return self.fps

    def stop(self):
        """Gracefully disconnects and stops background thread."""
        self.is_running = False
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


# =====================================================================
# Standalone CLI Tester for Android Phone Camera
# =====================================================================
def run_cli_preview(ip, port, path, custom_url=""):
    """
    Opens an interactive OpenCV preview window displaying the phone stream,
    real-time FPS, and basic face detection for verification.
    """
    print("\n" + "=" * 60)
    print("  NORTHFIELD UNIVERSITY — ANDROID IP CAMERA TESTER")
    print("=" * 60)

    url = custom_url.strip() if custom_url else build_ip_camera_url(ip, port, path)
    print(f"Connecting to stream: {url}")
    print("Testing connection...")

    test_res = test_ip_camera_stream(ip, port, path, custom_url=custom_url)
    if not test_res["success"]:
        print(f"[FAIL] {test_res['message']}")
        print("\nTroubleshooting Tips:")
        print("1. Open the 'IP Webcam' app on your Android phone.")
        print("2. Scroll to the bottom and tap 'Start Server'.")
        print("3. Ensure both this laptop and your phone are connected to the SAME Wi-Fi.")
        print(f"4. Double check the IP ({ip}) and Port ({port}) displayed on the phone screen.")
        return

    print(f"[SUCCESS] {test_res['message']}")
    print("Starting live preview window (Press 'Q' or ESC in preview window to exit)...")

    cam = AndroidIPCameraStream(ip=ip, port=port, path=path, custom_url=custom_url)
    cam.start()

    window_name = f"Android IP Camera Stream [{ip}:{port}] - Press 'Q' to Exit"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    # Simple face detector for visual verification
    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    face_cascade = cv2.CascadeClassifier(cascade_path) if os.path.exists(cascade_path) else None

    try:
        while True:
            ret, frame = cam.read()
            if not ret or frame is None:
                # Standby frame
                standby = np.zeros((480, 640, 3), dtype=np.uint8)
                standby[:] = (30, 30, 35)
                cv2.putText(standby, "Buffering Android Phone Stream...", (100, 240),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
                cv2.imshow(window_name, standby)
                if cv2.waitKey(30) & 0xFF in (27, ord('q'), ord('Q')):
                    break
                continue

            display = frame.copy()
            h, w = display.shape[:2]

            # Detect faces for visual feedback
            if face_cascade:
                gray = cv2.cvtColor(display, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray, 1.2, 5, minSize=(60, 60))
                for (fx, fy, fw, fh) in faces:
                    cv2.rectangle(display, (fx, fy), (fx + fw, fy + fh), (0, 255, 120), 2)
                    cv2.putText(display, "Face Detected", (fx, fy - 8),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 120), 2)

            # HUD Overlay
            fps = cam.get_fps()
            cv2.rectangle(display, (10, 10), (380, 80), (15, 20, 25), -1)
            cv2.rectangle(display, (10, 10), (380, 80), (46, 160, 67), 1)
            cv2.putText(display, f"Source: Android IP Camera ({ip}:{port})", (20, 34),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (240, 240, 240), 1)
            cv2.putText(display, f"FPS: {fps:.1f} | Res: {w}x{h}", (20, 56),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 120), 1)
            cv2.putText(display, "Press 'Q' to return", (20, 72),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (160, 160, 160), 1)

            cv2.imshow(window_name, display)
            key = cv2.waitKey(15) & 0xFF
            if key in (27, ord('q'), ord('Q')):
                break
    finally:
        cam.stop()
        cv2.destroyAllWindows()
        print("Camera preview closed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Android IP Camera Stream Client for Northfield University")
    parser.add_argument("--ip", type=str, default="", help="Android phone IP address (e.g. 192.168.1.15)")
    parser.add_argument("--port", type=int, default=8080, help="Stream port (default: 8080)")
    parser.add_argument("--path", type=str, default="/video", help="Stream path (default: /video)")
    parser.add_argument("--url", type=str, default="", help="Full custom stream URL")
    args = parser.parse_args()

    cfg = load_ip_camera_config()
    target_ip = args.ip.strip() if args.ip.strip() else cfg.get("ip", "192.168.1.100")
    target_port = args.port if args.port != 8080 or not cfg.get("port") else cfg.get("port", 8080)
    target_path = args.path if args.path != "/video" or not cfg.get("path") else cfg.get("path", "/video")

    if not args.ip and not args.url:
        print("\n=== Android IP Camera Setup ===")
        print(f"Computer Wi-Fi IP: {get_local_wifi_ip()}")
        print(f"Configured Phone IP: {target_ip}")
        print(f"Configured Port: {target_port}")
        if sys.stdin.isatty():
            try:
                user_input_ip = input(f"Enter phone IP address [press Enter to keep '{target_ip}']: ").strip()
                if user_input_ip:
                    target_ip = user_input_ip

                user_input_port = input(f"Enter stream port [press Enter to keep '{target_port}']: ").strip()
                if user_input_port and user_input_port.isdigit():
                    target_port = int(user_input_port)

                save_ip_camera_config({"ip": target_ip, "port": target_port, "path": target_path})
            except (EOFError, KeyboardInterrupt):
                pass
        else:
            print(f"Using saved configuration: {target_ip}:{target_port}")

    run_cli_preview(target_ip, target_port, target_path, custom_url=args.url)
