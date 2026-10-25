# Auto Attendance Intelligence System 🎓👁️

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![OpenCV](https://img.shields.io/badge/OpenCV-YuNet%20%2B%20SFace-green.svg)](https://opencv.org/)
[![Flask](https://img.shields.io/badge/Backend-Flask-lightgrey.svg)](https://flask.palletsprojects.com/)
[![Database](https://img.shields.io/badge/Database-SQLite3-orange.svg)](https://www.sqlite.org/)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

An intelligent, production-ready biometric attendance management system powered by deep learning face detection (**YuNet**) and biometric feature recognition (**SFace**). The application supports standard webcams, Android IP camera streams over Wi-Fi, multi-role authentication (HOD & Faculty), real-time present/absent tracking, review queue verification with desk seating plans, and immutable attendance database storage.

---

## ⚡ Instant Standalone Executable (Zero Tools / No Python Needed)

You can share the pre-packaged standalone bundle with anyone so they can run the system immediately **without installing Python, OpenCV, or any libraries**:

1. **Share the ZIP file**:
   - Send `dist/AutoAttendance_Standalone.zip` (located inside `dist/` after building, or download from GitHub releases).
2. **Double-click `AutoAttendance.exe`**:
   - Unzip the archive and directly double-click **`AutoAttendance.exe`**.
   - It runs instantly on any 64-bit Windows machine and opens the web application automatically in their browser!

---

## 🚀 1-Click Quickstart from Source (Developers)

If running from the source code repository:

1. **Clone or Download** this repository onto any PC:
   ```bash
   git clone https://github.com/Rohit-Mahata/Auto_Attendance.git
   ```
2. **Double-click** `Launch_Attendance_App.bat` (or `run.bat`).
   - *The launcher automatically detects Python, installs any missing packages from `requirements.txt`, creates a convenient **Desktop Shortcut**, launches the server, and automatically opens your browser to `http://127.0.0.1:5055/index.html`.*

3. **To re-build the standalone `.exe` anytime**:
   ```bash
   python build_exe.py
   ```

## 🔑 Default Sign-in Credentials

| Role | User ID | Password | Role Selector | Capabilities |
| :--- | :--- | :--- | :--- | :--- |
| **HOD (Admin)** | `HOD01` | `admin` | **HOD** | Faculty Account Creation, Academic Term Settings, Student Records, Department Analytics |
| **Faculty Member** | `FAC104` | `faculty` | **Faculty** | Live Attendance Sessions, Face Recognition Camera, Candidate Review Queue, Desk Seating Plan, Attendance Submission |

*(Additional Faculty accounts can be created directly by the HOD from the HOD Management Portal).*

---

## 🌟 Key Features

- **Deep Learning Biometric Pipeline**:
  - **YuNet**: Ultra-fast face detector evaluated with high precision across varying classroom lighting conditions.
  - **SFace**: Deep facial embedding engine producing normalized 128-dimensional vectors compared via cosine distance.
- **Real-Time Live Presence Tracking**:
  - Live face recognition immediately matches enrolled students and dynamically updates the **Present Students** and **Absent Students** lists in real-time.
  - Presence is only logged when the instructor clicks **Start Attendance Session**.
- **Android IP Camera Ingestion**:
  - Turn any smartphone into a wireless classroom camera using the `ip_camera_stream.py` module.
  - Features low-latency MJPEG stream processing and automated TCP pre-flight reachability checks.
- **Desk Seating Plan & Review Queue**:
  - Unclear or low-confidence face crops are sent to the **Review Queue** where instructors can review the student's physical classroom seating location before confirming presence.
  - Interactive candidate confirmation with 1-click manual overrides.
- **Audit Logging & Safe Storage**:
  - All submitted sessions are saved atomically to the SQLite database (`attendance_records`) with cryptographic audit logs.

---

## 📱 How to Use Your Android Phone as an IP Camera

1. Connect your Android phone and PC to the **same Wi-Fi network** (or connect your PC to your phone's mobile hotspot).
2. Download and install **"IP Webcam"** (by Pavel Khlebovich) from Google Play Store on your phone.
3. Open the app, scroll to the bottom, and tap **"Start server"**.
4. The app will display an IP address on your phone screen, for example:
   ```text
   http://192.168.1.100:8080   or   https://192.0.0.8:4444
   ```
5. In the Attendance Web App:
   - Navigate to **Camera Settings** (or click the IP Camera option).
   - Enter your phone's **IP Address** (e.g., `192.168.1.100`) and **Port** (e.g., `8080`).
   - Click **Save & Connect**. The live video stream from your phone will immediately begin streaming into the face recognition system!

---

## 🛠️ Manual Installation (Cross-Platform / Developers)

If you prefer running via command line:

```bash
# 1. Clone repository
git clone https://github.com/Rohit-Mahata/Auto_Attendance.git
cd Auto_Attendance

# 2. (Optional) Create virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
# source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Launch Application
python main.py
```

Open your browser to: **`http://127.0.0.1:5055/index.html`**

---

## 📁 Project Architecture

```text
Auto_Attendance/
├── Launch_Attendance_App.bat    # 1-click launcher & auto-installer for Windows
├── run.bat                     # Quick launch script
├── create_shortcut.py          # Script to create Desktop shortcut
├── requirements.txt            # Python dependencies
├── .gitignore                  # Git ignore rules for clean repository
├── main.py                     # Main application entrypoint
├── app.py                      # Flask REST API and live recognition controller
├── ip_camera_stream.py         # Android IP Camera streaming engine & TCP checker
├── cctv_stream.py              # CCTV stream ingestion wrapper
├── build_exe.py                # Standalone Windows executable packager
├── ai_pipeline/                # Deep learning face detection & recognition
│   ├── face_detector.py        # YuNet detector implementation
│   ├── face_recognizer.py      # SFace embedding extractor & matcher
│   └── models/                 # Pretrained ONNX weights (YuNet & SFace)
├── data/                       # Local database, biometric templates, and config
│   ├── production_attendance.db# SQLite database
│   ├── camera_config.json      # Camera configuration settings
│   └── biometric_vault/        # Encrypted biometric reference vectors
├── db/
│   └── database.py             # Database models, schemas, and queries
├── ui_app/                     # Modern Web UI (Glassmorphic dark interface)
│   ├── index.html              # Frontend layout and views
│   ├── app.js                  # Frontend state management & live polling
│   └── style.css               # Modern responsive styling
└── README.md                   # Documentation
```

---

## 👥 Authors & Contributors

- **Rohit Mahata** — [GitHub](https://github.com/Rohit-Mahata)
