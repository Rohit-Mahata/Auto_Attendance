import os
import sys
import urllib.request
from pathlib import Path

# Add parent directory to sys.path for config import
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import (
    YUNET_MODEL_FILE,
    SFACE_MODEL_FILE,
    YUNET_DOWNLOAD_URL,
    SFACE_DOWNLOAD_URL
)

def download_file(url, target_path, progress_callback=None):
    target_path = Path(target_path)
    if target_path.exists() and target_path.stat().st_size > 1000:
        return True

    print(f"[AI Model Downloader] Fetching {target_path.name} from {url}...")
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = target_path.with_suffix(".tmp")

    try:
        def reporthook(count, block_size, total_size):
            if progress_callback and total_size > 0:
                percent = min(100, int(count * block_size * 100 / total_size))
                progress_callback(percent, target_path.name)

        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        with urllib.request.urlopen(req, timeout=30) as response, open(temp_path, "wb") as out_file:
            total_size = int(response.info().get("Content-Length", -1))
            downloaded = 0
            block_size = 64 * 1024
            while True:
                buffer = response.read(block_size)
                if not buffer:
                    break
                downloaded += len(buffer)
                out_file.write(buffer)
                if progress_callback and total_size > 0:
                    percent = min(100, int(downloaded * 100 / total_size))
                    progress_callback(percent, target_path.name)

        temp_path.replace(target_path)
        print(f"[AI Model Downloader] Successfully downloaded {target_path.name}")
        return True
    except Exception as e:
        print(f"[AI Model Downloader] Download failed for {target_path.name}: {e}")
        if temp_path.exists():
            temp_path.unlink()
        return False

def ensure_models_available(progress_callback=None):
    """
    Ensures both YuNet (Face Detector) and SFace (Face Recognizer) are downloaded.
    Returns (has_yunet, has_sface).
    """
    has_yunet = download_file(YUNET_DOWNLOAD_URL, YUNET_MODEL_FILE, progress_callback)
    has_sface = download_file(SFACE_DOWNLOAD_URL, SFACE_MODEL_FILE, progress_callback)
    return has_yunet, has_sface

if __name__ == "__main__":
    ensure_models_available(lambda p, name: print(f"{name}: {p}%"))
