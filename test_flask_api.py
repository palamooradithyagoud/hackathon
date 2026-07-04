"""
Flask Integration Test Suite.
Verifies routes and responses using Flask's built-in testing client.
"""

import json
import unittest
import os
from server import app

# Ensure we simulate a clean/vercel context or local context properly
os.environ["VERCEL"] = "1"  # Force Vercel mode to test path fallbacks safely

class FlaskAPITestCase(unittest.TestCase):
    
    def setUp(self):
        # Set up Flask test client
        self.client = app.test_client()
        app.config["TESTING"] = True

    def test_01_index_page(self):
        """Test serving index.html."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"<!DOCTYPE html>", response.data)

    def test_02_stats_endpoint(self):
        """Test GET /api/stats."""
        response = self.client.get("/api/stats")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn("chunk_count", data)
        self.assertIn("paper_count", data)
        self.assertIn("total_queries", data)

    def test_03_chat_endpoint(self):
        """Test POST /api/chat."""
        payload = {
            "query": "Who works on plant disease detection?",
            "role": "student"
        }
        response = self.client.post("/api/chat", json=payload)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn("intent", data)
        self.assertIn("response_text", data)
        self.assertIn("data", data)

    def test_04_recommend_endpoint(self):
        """Test POST /api/recommend."""
        payload = {
            "query": "IoT healthcare",
            "role": "faculty"
        }
        response = self.client.post("/api/recommend", json=payload)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["intent"], "recommend")
        self.assertIn("response_text", data)

    def test_05_collaborate_endpoint(self):
        """Test POST /api/collaborate."""
        payload = {
            "faculty_a": "Shirina Samreen",
            "faculty_b": "Akhil Jabbar Meerja"
        }
        response = self.client.post("/api/collaborate", json=payload)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["faculty_a"], "Shirina Samreen")
        self.assertEqual(data["faculty_b"], "Akhil Jabbar Meerja")
        self.assertIn("synergy_reason", data)

    def test_06_logs_endpoint(self):
        """Test GET /api/logs."""
        response = self.client.get("/api/logs?role=student")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIsInstance(data, list)

    def test_07_invalid_json_payload(self):
        """Test validation error with incomplete payload on POST /api/chat."""
        payload = {
            "query_wrong_key": "test"
        }
        response = self.client.post("/api/chat", json=payload)
        self.assertEqual(response.status_code, 422)

if __name__ == "__main__":
    unittest.main()
