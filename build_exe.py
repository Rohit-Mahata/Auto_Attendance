"""
Automated Build Script for Standalone AutoAttendance Windows Executable
Packages the entire Python runtime, OpenCV, Flask, models, and UI into a standalone application.
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

def build():
    print("=" * 70)
    print("      BUILDING STANDALONE AUTO ATTENDANCE EXECUTABLE (.EXE)")
    print("=" * 70)
    
    dist_dir = BASE_DIR / "dist"
    build_dir = BASE_DIR / "build"
    
    # PyInstaller arguments
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=AutoAttendance",
        "--onedir",  # Standalone folder for fastest startup and highest reliability
        "--noconfirm",
        "--clean",
        f"--add-data={BASE_DIR / 'ui_app'};ui_app",
        f"--add-data={BASE_DIR / 'ai_pipeline' / 'models'};ai_pipeline/models",
        "--hidden-import=cryptography",
        "--hidden-import=sqlite3",
        "--hidden-import=cv2",
        "--hidden-import=numpy",
        "--hidden-import=flask",
        "--hidden-import=urllib.request",
        "--hidden-import=urllib.parse",
        "--hidden-import=ssl",
        str(BASE_DIR / "main.py")
    ]
    
    print("\n[1/3] Running PyInstaller build...")
    result = subprocess.run(cmd, cwd=str(BASE_DIR))
    if result.returncode != 0:
        print("\n[ERROR] PyInstaller build failed!")
        return False
        
    output_app_dir = dist_dir / "AutoAttendance"
    print(f"\n[2/3] PyInstaller build completed at: {output_app_dir}")
    
    # Copy essential data folder into the output directory so default DB and configs are available
    target_data_dir = output_app_dir / "data"
    source_data_dir = BASE_DIR / "data"
    print(f"\n[3/3] Copying default database and config to {target_data_dir}...")
    if source_data_dir.exists():
        if target_data_dir.exists():
            shutil.rmtree(target_data_dir)
        shutil.copytree(source_data_dir, target_data_dir)
        
    # Create an AutoAttendance.zip archive for easy sharing
    zip_path = dist_dir / "AutoAttendance_Standalone"
    print(f"\n[*] Creating standalone ZIP package: {zip_path}.zip...")
    shutil.make_archive(str(zip_path), 'zip', root_dir=str(dist_dir), base_dir="AutoAttendance")
    
    print("\n" + "=" * 70)
    print("                      BUILD SUCCESSFUL!")
    print("=" * 70)
    print(f"Standalone Executable: {output_app_dir / 'AutoAttendance.exe'}")
    print(f"Shareable ZIP Package: {zip_path}.zip")
    print("Anyone can unzip and run AutoAttendance.exe without Python or any tools!")
    print("=" * 70)
    return True

if __name__ == "__main__":
    success = build()
    sys.exit(0 if success else 1)
