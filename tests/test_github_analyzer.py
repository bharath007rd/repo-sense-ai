"""
tests/test_github_analyzer.py
Unit tests for github_utils.py and github_analyzer.py using mocked API responses.
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from github_utils import parse_github_url, get_auth_headers
from github_analyzer import (
    get_repository_metadata,
    get_repository_tree,
    identify_important_files,
    fetch_file_content,
    analyze_repository
)

class TestGitHubUtils(unittest.TestCase):
    
    def test_parse_github_url_valid(self):
        self.assertEqual(parse_github_url("https://github.com/octocat/Hello-World"), ("octocat", "Hello-World"))
        self.assertEqual(parse_github_url("https://github.com/octocat/Hello-World.git"), ("octocat", "Hello-World"))

    def test_parse_github_url_invalid(self):
        with self.assertRaises(ValueError):
            parse_github_url("https://gitlab.com/octocat/Hello-World")
        with self.assertRaises(ValueError):
            parse_github_url("")

    @patch.dict(os.environ, {"GITHUB_TOKEN": "mock_token_123"})
    def test_get_auth_headers_with_token(self):
        headers = get_auth_headers()
        self.assertEqual(headers["Authorization"], "Bearer mock_token_123")


class TestGitHubAnalyzer(unittest.TestCase):

    @patch("github_analyzer.requests.get")
    def test_get_repository_metadata_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "name": "Hello-World",
            "full_name": "octocat/Hello-World",
            "description": "Test repo",
            "default_branch": "main",
            "language": "Python",
            "stargazers_count": 10,
            "forks_count": 2,
            "html_url": "https://github.com/octocat/Hello-World",
            "size": 1024
        }
        mock_get.return_value = mock_response

        meta = get_repository_metadata("octocat", "Hello-World")
        self.assertEqual(meta["name"], "Hello-World")
        self.assertEqual(meta["language"], "Python")

    def test_identify_important_files(self):
        tree = [
            {"path": "README.md", "type": "blob"},
            {"path": "requirements.txt", "type": "blob"},
            {"path": "src/main.py", "type": "blob"},
            {"path": "assets/logo.png", "type": "blob"}
        ]
        result = identify_important_files(tree)
        self.assertEqual(result["readme"], "README.md")
        self.assertIn("requirements.txt", result["dependencies"])
        self.assertIn("src/main.py", result["source_files"])
        self.assertNotIn("assets/logo.png", result["source_files"])

    def test_fetch_file_content_binary_skip(self):
        content = fetch_file_content("octocat", "Hello-World", "logo.png")
        self.assertIn("Skipped", content)


if __name__ == "__main__":
    unittest.main()