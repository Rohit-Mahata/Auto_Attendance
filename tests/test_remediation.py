"""
Automated Comprehensive Test Suite: Amritsar Group of Colleges Attendance System
Validates all remediated bugs and requirements.
"""

import os
import sys
import unittest
import numpy as np
import uuid
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from config import DATA_DIR, EMBEDDINGS_PATH, DB_PATH
from db.database import production_db
from ai_pipeline.face_recognizer import FaceRecognizer
from app import flask_app

class TestRemediationSuite(unittest.TestCase):
    def setUp(self):
        self.app = flask_app.test_client()
        self.app.testing = True

    def test_01_canonical_database_path(self):
        """Verifies DB_PATH points to production_attendance.db."""
        self.assertEqual(DB_PATH.name, "production_attendance.db")
        self.assertTrue(EMBEDDINGS_PATH.is_absolute())

    def test_02_no_dummy_embeddings_in_recognizer_probe(self):
        """Verifies FaceRecognizer confidence mapping is monotonic."""
        rec = FaceRecognizer()
        ref = np.random.randn(128).astype(np.float32)
        ref /= np.linalg.norm(ref)
        rec.student_embeddings["TEST_SID_001"] = ref

        # Probe matching exactly
        sid, conf, match = rec.match_probe(ref, min_threshold=0.58)
        self.assertEqual(sid, "TEST_SID_001")
        self.assertTrue(match)
        self.assertAlmostEqual(conf, 100.0, delta=0.5)

        # Probe with lower cosine similarity (e.g. 0.60 vs 0.55)
        probe_high = ref * 0.70 + np.random.randn(128).astype(np.float32) * 0.30
        probe_high /= np.linalg.norm(probe_high)
        sim_high = float(np.dot(probe_high, ref))

        probe_low = ref * 0.50 + np.random.randn(128).astype(np.float32) * 0.50
        probe_low /= np.linalg.norm(probe_low)
        sim_low = float(np.dot(probe_low, ref))

        _, conf_high, _ = rec.match_probe(probe_high, min_threshold=0.50)
        _, conf_low, _ = rec.match_probe(probe_low, min_threshold=0.50)

        # Monotonicity check
        if sim_high > sim_low:
            self.assertGreaterEqual(conf_high, conf_low)

    def test_03_auth_starts_unauthenticated(self):
        """Verifies that app starts unauthenticated and requires login."""
        # Using a new client session
        client = flask_app.test_client()
        res = client.get("/api/auth/current")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertFalse(data["authenticated"])
        self.assertIsNone(data["user"])

    def test_04_auth_login_and_logout_flow(self):
        """Verifies login succeeds with correct credentials and stores session."""
        client = flask_app.test_client()

        # Login with HOD credentials
        login_res = client.post("/api/auth/login", json={
            "user_id": "HOD01",
            "password": "admin",
            "role": "hod"
        })
        self.assertEqual(login_res.status_code, 200)
        login_data = login_res.get_json()
        self.assertTrue(login_data["success"])
        self.assertEqual(login_data["user"]["role"], "hod")

        # Current auth check
        curr_res = client.get("/api/auth/current")
        curr_data = curr_res.get_json()
        self.assertTrue(curr_data["authenticated"])
        self.assertEqual(curr_data["user"]["user_id"], "HOD01")

        # Logout
        logout_res = client.post("/api/auth/logout")
        self.assertEqual(logout_res.status_code, 200)
        curr_after = client.get("/api/auth/current").get_json()
        self.assertFalse(curr_after["authenticated"])

    def test_05_hod_faculty_endpoint_credentials(self):
        """Verifies HOD faculty API returns credentials (user_id and password)."""
        res = self.app.get("/api/hod/faculty")
        self.assertEqual(res.status_code, 200)
        faculty_list = res.get_json()
        self.assertIsInstance(faculty_list, list)
        self.assertGreater(len(faculty_list), 0)

        for f in faculty_list:
            self.assertIn("employee_id", f)
            self.assertIn("user_id", f)
            self.assertIn("password", f)
            self.assertIn("assigned_subjects", f)
            self.assertIn("timetable_slots", f)
            # Ensure password is not empty
            self.assertTrue(len(f["password"]) > 0)

    def test_06_no_fabricated_attendance_kpis(self):
        """Verifies get_current_session_info does not fabricate attendance when no records exist."""
        sess_info = production_db.get_current_session_info()
        if sess_info:
            counted = sess_info["counted"]
            identified = sess_info["identified"]
            unclear = sess_info["unclear"]
            enrolled = sess_info["enrolled"]
            # Identified + unclear should equal counted
            self.assertEqual(counted, identified + unclear)
            # Unaccounted + identified + unclear should not exceed enrolled
            self.assertLessEqual(identified + unclear, enrolled)

    def test_07_no_fabricated_multi_subject_attendance(self):
        """Verifies get_student_multi_subject_attendance returns 0 when no records exist instead of fake 24/28."""
        records = production_db.get_student_multi_subject_attendance("NON_EXISTENT_STUDENT_999")
        for r in records:
            # If no attendance was ever marked, attended and total must be 0
            self.assertEqual(r["attended"], 0)
            self.assertEqual(r["total"], 0)
            self.assertEqual(r["percentage"], 0.0)

    def test_08_override_student_attendance_dynamic_session(self):
        """Verifies override_student_attendance does not fail with hardcoded session."""
        students = production_db.get_all_students()
        if students:
            sid = students[0]["student_id"]
            success, msg = production_db.override_student_attendance(sid, "present", actor="TestActor")
            self.assertTrue(success)

    def test_10_registration_validation_and_no_dummy_vectors(self):
        """Verifies registering a student does not create fake random embeddings."""
        test_sid = f"T_{uuid.uuid4().hex[:6].upper()}"
        test_roll = f"R_{uuid.uuid4().hex[:6]}"
        payload = {
            "student_id": test_sid,
            "name": "Validation Test Student",
            "roll_no": test_roll,
            "department": "Computer Science",
            "course": "B.Tech",
            "year": "2025-26",
            "semester": "5th Semester",
            "division": "CSE1"
        }
        try:
            res = self.app.post("/api/students/register", json=payload)
            self.assertEqual(res.status_code, 200)

            # Check recognizer embeddings gallery
            rec = FaceRecognizer()
            # Verify dummy embedding was NOT registered in memory or disk
            self.assertNotIn(test_sid, rec.student_embeddings)

            # Verify DB student record has has_embedding = 0
            st = production_db.get_student_by_id(test_sid)
            self.assertIsNotNone(st)
            self.assertEqual(st["has_embedding"], 0)
        finally:
            production_db.delete_student(test_sid)

    def test_11_correction_request_foreign_key_safety(self):
        """Verifies create_correction_request returns failure when course session does not exist."""
        students = production_db.get_all_students()
        if students:
            sid = students[0]["student_id"]
            ok, msg, corr_id = production_db.create_correction_request(sid, "NON_EXISTENT_COURSE_XYZ", "Need correction")
            self.assertFalse(ok)
            self.assertEqual(corr_id, 0)

    def test_12_pose_session_ttl_cleanup(self):
        """Verifies expired pose capture sessions are pruned."""
        import time
        from app import pose_capture_sessions, pose_session_timestamps, cleanup_expired_pose_sessions
        test_id = "STALE_SESSION_STUDENT"
        pose_capture_sessions[test_id] = {"front": [np.zeros(128, dtype=np.float32)]}
        pose_session_timestamps[test_id] = time.time() - 1000  # Stale: > 900 seconds ago

        cleanup_expired_pose_sessions(max_age_seconds=900)
        self.assertNotIn(test_id, pose_capture_sessions)
        self.assertNotIn(test_id, pose_session_timestamps)

    def test_13_hod_create_faculty_id(self):
        """Verifies HOD can provision a new faculty ID with user credentials."""
        new_fac_id = f"FAC_{uuid.uuid4().hex[:4].upper()}"
        payload = {
            "employee_id": new_fac_id,
            "name": "Dr. Automated Test Faculty",
            "email": "test.faculty@agc.edu.in",
            "department": "Computer Science",
            "role": "Associate Professor",
            "password": "testpassword123",
            "actor": "HOD"
        }
        try:
            res = self.app.post("/api/hod/faculty/add", json=payload)
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertTrue(data.get("success"))

            # Verify in instructors list
            fac_list = self.app.get("/api/hod/faculty").get_json()
            ids = [f["employee_id"] for f in fac_list]
            self.assertIn(new_fac_id, ids)

            # Verify user can authenticate with the new faculty credentials
            login_res = self.app.post("/api/auth/login", json={
                "user_id": new_fac_id,
                "role": "faculty",
                "password": "testpassword123"
            })
            self.assertEqual(login_res.status_code, 200)
            self.assertTrue(login_res.get_json().get("success"))
        finally:
            with production_db.get_connection() as conn:
                conn.execute("DELETE FROM instructors WHERE employee_id = ?", (new_fac_id,))
                conn.execute("DELETE FROM users WHERE user_id = ?", (new_fac_id,))
                conn.commit()

    def test_14_hod_delete_operations(self):
        """Verifies HOD can delete students, faculty, classes, subjects, and timetable slots."""
        # 1. Test Student Deletion
        del_sid = f"T_{uuid.uuid4().hex[:6].upper()}"
        self.app.post("/api/students/register", json={
            "student_id": del_sid,
            "name": "Deletable Student",
            "roll_no": f"R_{uuid.uuid4().hex[:6]}",
            "department": "Computer Science",
            "course": "B.Tech",
            "year": "2025-26",
            "semester": "5th Semester",
            "division": "CSE1"
        })
        self.assertIsNotNone(production_db.get_student_by_id(del_sid))
        del_st_res = self.app.post("/api/hod/students/delete", json={"student_id": del_sid})
        self.assertEqual(del_st_res.status_code, 200)
        self.assertTrue(del_st_res.get_json()["success"])
        self.assertIsNone(production_db.get_student_by_id(del_sid))

        # 2. Test Faculty Deletion
        del_fid = f"FAC_{uuid.uuid4().hex[:4].upper()}"
        self.app.post("/api/hod/faculty/add", json={
            "employee_id": del_fid,
            "name": "Deletable Faculty",
            "email": "del.fac@agc.edu.in",
            "department": "Computer Science",
            "role": "Lecturer",
            "password": "tempdelpassword"
        })
        del_fac_res = self.app.post("/api/hod/faculty/delete", json={"employee_id": del_fid})
        self.assertEqual(del_fac_res.status_code, 200)
        self.assertTrue(del_fac_res.get_json()["success"])
        # Verify cannot login
        login_fail = self.app.post("/api/auth/login", json={"user_id": del_fid, "role": "faculty", "password": "tempdelpassword"})
        self.assertFalse(login_fail.get_json()["success"])

        # 3. Test Class Deletion
        del_class = f"CLS_{uuid.uuid4().hex[:3].upper()}"
        self.app.post("/api/hod/classes/add", json={"class_code": del_class, "department": "Computer Science", "semester": "5th"})
        del_cls_res = self.app.post("/api/hod/classes/delete", json={"class_code": del_class})
        self.assertEqual(del_cls_res.status_code, 200)
        self.assertTrue(del_cls_res.get_json()["success"])
        classes = self.app.get("/api/hod/classes").get_json()
        self.assertNotIn(del_class, [c["class_code"] for c in classes])

        # 4. Test Subject Deletion
        del_sub = f"SUB_{uuid.uuid4().hex[:3].upper()}"
        self.app.post("/api/hod/subjects/add", json={
            "code": del_sub,
            "name": "Deletable Subject",
            "department": "Computer Science",
            "credits": 3,
            "faculty_id": "FAC104",
            "room": "Room A"
        })
        del_sub_res = self.app.post("/api/hod/subjects/delete", json={"code": del_sub})
        self.assertEqual(del_sub_res.status_code, 200)
        self.assertTrue(del_sub_res.get_json()["success"])
        subjects = self.app.get("/api/hod/subjects").get_json()
        self.assertNotIn(del_sub, [s["code"] for s in subjects])

        # 5. Test Timetable Slot Deletion
        slot_add_res = self.app.post("/api/hod/timetable/add-slot", json={
            "class_code": "CS-3A",
            "day": "Friday",
            "time_slot": "15:00 – 16:00",
            "subject_code": "CS-2104",
            "faculty_id": "FAC104",
            "room": "Room Test"
        })
        self.assertEqual(slot_add_res.status_code, 200)
        # Find the slot ID
        slots = self.app.get("/api/hod/timetable?class_code=CS-3A&day=Friday").get_json()
        slot_id = next((s["id"] for s in slots if s["time_slot"] == "15:00 – 16:00"), None)
        self.assertIsNotNone(slot_id)
        del_slot_res = self.app.post("/api/hod/timetable/delete-slot", json={"slot_id": slot_id})
        self.assertEqual(del_slot_res.status_code, 200)
        self.assertTrue(del_slot_res.get_json()["success"])

if __name__ == "__main__":
    unittest.main()



