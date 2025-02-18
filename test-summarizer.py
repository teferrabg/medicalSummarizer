import unittest
from unittest.mock import patch, MagicMock
import json
import os
import tempfile
from fastapi.testclient import TestClient
from main import app, summarize_text, read_text_file, get_text_files

client = TestClient(app)

class TestMedicalSummarizer(unittest.TestCase):
    
    def setUp(self):
        # Create a temporary directory and sample files for testing
        self.temp_dir = tempfile.mkdtemp()
        self.sample_files = [
            os.path.join(self.temp_dir, "note1.txt"),
            os.path.join(self.temp_dir, "note2.txt")
        ]
        
        # Create sample medical notes
        for file_path in self.sample_files:
            with open(file_path, 'w') as f:
                f.write("Sample medical note for testing.")
    
    def tearDown(self):
        # Clean up temporary files
        for file_path in self.sample_files:
            if os.path.exists(file_path):
                os.remove(file_path)
        if os.path.exists(self.temp_dir):
            os.rmdir(self.temp_dir)
    
    def test_health_endpoint(self):
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
    
    def test_read_text_file(self):
        content = read_text_file(self.sample_files[0])
        self.assertEqual(content, "Sample medical note for testing.")
    
    def test_get_text_files(self):
        files = get_text_files(self.temp_dir)
        self.assertEqual(len(files), 2)
        self.assertTrue(all(f.endswith('.txt') for f in files))
    
    def test_invalid_directory(self):
        response = client.post("/summarize", json={
            "directory": "nonexistent_directory",
            "role": "physician",
            "format": "brief"
        })
        self.assertEqual(response.status_code, 500)
    
    @patch("main.openai.ChatCompletion.create")
    def test_summarize_endpoint(self, mock_openai):
        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message = {"content": "Test summary. Critical Findings Finding 1"}
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        mock_response.usage.total_tokens = 150
        mock_openai.return_value = mock_response
        
        # Test request
        response = client.post("/summarize", json={
            "directory": self.temp_dir,
            "role": "physician",
            "format": "brief",
            "highlight_critical": True
        })
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(isinstance(data, list))
        self.assertEqual(len(data), 2)  # Should have processed both test files
        
        for summary in data:
            self.assertIn("summary_id", summary)
            self.assertIn("file_name", summary)
            self.assertEqual(summary["summary"], "Test summary.")
            self.assertEqual(summary["critical_findings"], ["Finding 1"])
            self.assertIn("metadata", summary)
            self.assertEqual(summary["metadata"]["role"], "physician")
            self.assertEqual(summary["metadata"]["format"], "brief")
    
    def test_feedback_endpoint(self):
        feedback_data = {
            "summary_id": "test_id_123",
            "rating": 4,
            "comments": "Good summary"
        }
        
        response = client.post("/feedback", json=feedback_data)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn("feedback_id", response.json())

if __name__ == "__main__":
    unittest.main()
