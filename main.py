"""
Northfield University of Technology — Attendance Intelligence
Main Entry Point (Web-based Native Experience)
"""
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app import launch

if __name__ == "__main__":
    launch()

