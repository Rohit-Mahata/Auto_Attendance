import sqlite3
import os
from datetime import datetime
from config import DB_PATH

class DatabaseEngine:
    def __init__(self, db_path=DB_PATH):
        self.db_path = str(db_path)
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Students Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS students (
                    student_id TEXT PRIMARY KEY,
                    roll_no TEXT UNIQUE,
                    name TEXT NOT NULL,
                    department TEXT,
                    course TEXT,
                    year TEXT,
                    semester TEXT,
                    gender TEXT,
                    email TEXT,
                    phone TEXT,
                    enrolled_date TEXT,
                    photo_sample_count INTEGER DEFAULT 0,
                    has_embedding INTEGER DEFAULT 0
                )
            """)

            # Attendance Logs Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS attendance_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    roll_no TEXT,
                    classroom_id TEXT DEFAULT 'Classroom-101',
                    date TEXT NOT NULL,
                    time TEXT NOT NULL,
                    confidence REAL,
                    camera_source TEXT,
                    status TEXT DEFAULT 'Present',
                    FOREIGN KEY(student_id) REFERENCES students(student_id)
                )
            """)

            # CCTV Cameras Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cctv_cameras (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    classroom TEXT NOT NULL,
                    rtsp_url TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1
                )
            """)

            # System Settings Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)

            conn.commit()
            self._seed_default_settings(cursor, conn)

    def _seed_default_settings(self, cursor, conn):
        defaults = {
            "min_confidence": "65",
            "detection_model": "yunet_sface",
            "default_camera": "0",
            "classroom_name": "Classroom-A1",
            "auto_attendance_cooldown": "300",  # 5 minutes
            "liveness_check": "1",
            "theme": "dark_modern"
        }
        for k, v in defaults.items():
            cursor.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES (?, ?)", (k, v))
        conn.commit()

    # ================= Student Operations =================
    def get_all_students(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM students ORDER BY student_id ASC")
            return [dict(row) for row in cursor.fetchall()]

    def get_student(self, student_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM students WHERE student_id = ?", (student_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def upsert_student(self, student_data):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO students (
                    student_id, roll_no, name, department, course,
                    year, semester, gender, email, phone, enrolled_date,
                    photo_sample_count, has_embedding
                ) VALUES (
                    :student_id, :roll_no, :name, :department, :course,
                    :year, :semester, :gender, :email, :phone, :enrolled_date,
                    :photo_sample_count, :has_embedding
                )
                ON CONFLICT(student_id) DO UPDATE SET
                    roll_no = excluded.roll_no,
                    name = excluded.name,
                    department = excluded.department,
                    course = excluded.course,
                    year = excluded.year,
                    semester = excluded.semester,
                    gender = excluded.gender,
                    email = excluded.email,
                    phone = excluded.phone,
                    photo_sample_count = excluded.photo_sample_count,
                    has_embedding = excluded.has_embedding
            """, student_data)
            conn.commit()

    def update_student_biometric_status(self, student_id, sample_count, has_embedding=1):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE students
                SET photo_sample_count = ?, has_embedding = ?
                WHERE student_id = ?
            """, (sample_count, has_embedding, student_id))
            conn.commit()

    def delete_student(self, student_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM students WHERE student_id = ?", (student_id,))
            conn.commit()

    # ================= Attendance Operations =================
    def mark_attendance(self, student_id, name, roll_no, confidence=95.0, classroom="Classroom-A1", camera="Cam-01"):
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M:%S")

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Check if student was already marked today in this classroom
            cursor.execute("""
                SELECT id FROM attendance_logs
                WHERE student_id = ? AND date = ? AND classroom_id = ?
            """, (student_id, date_str, classroom))
            existing = cursor.fetchone()

            if existing:
                return False, "Already marked today"

            cursor.execute("""
                INSERT INTO attendance_logs (
                    student_id, name, roll_no, classroom_id,
                    date, time, confidence, camera_source, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Present')
            """, (student_id, name, roll_no, classroom, date_str, time_str, confidence, camera))
            conn.commit()
            return True, f"Attendance marked for {name}"

    def get_attendance_logs(self, date=None, classroom=None, student_query=None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM attendance_logs WHERE 1=1"
            params = []

            if date:
                query += " AND date = ?"
                params.append(date)
            if classroom:
                query += " AND classroom_id = ?"
                params.append(classroom)
            if student_query:
                query += " AND (name LIKE ? OR roll_no LIKE ? OR student_id LIKE ?)"
                like_term = f"%{student_query}%"
                params.extend([like_term, like_term, like_term])

            query += " ORDER BY id DESC"
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_attendance_summary(self, date=None):
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(DISTINCT student_id) FROM students")
            total_students = cursor.fetchone()[0] or 0

            cursor.execute("SELECT COUNT(DISTINCT student_id) FROM attendance_logs WHERE date = ?", (date,))
            present_students = cursor.fetchone()[0] or 0

            absent_students = max(0, total_students - present_students)
            rate = round((present_students / total_students * 100), 1) if total_students > 0 else 0.0

            return {
                "date": date,
                "total": total_students,
                "present": present_students,
                "absent": absent_students,
                "attendance_rate": rate
            }

    # ================= Settings Operations =================
    def get_setting(self, key, default=""):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM system_settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row["value"] if row else default

    def set_setting(self, key, value):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO system_settings (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """, (key, str(value)))
            conn.commit()

# Singleton
db = DatabaseEngine()
