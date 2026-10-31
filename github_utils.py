"""
github_utils.py
Utility functions for parsing GitHub URLs and configuring API requests.
"""

import os
import re
from typing import Tuple, Dict

def parse_github_url(url: str) -> Tuple[str, str]:
    """
    Parses a public GitHub repository URL and extracts the owner and repository name.
    """
    if not isinstance(url, str) or not url.strip():
        raise ValueError("Repository URL must be a non-empty string.")
    
    cleaned_url = url.strip().rstrip("/")
    if cleaned_url.endswith(".git"):
        cleaned_url = cleaned_url[:-4]
        
    pattern = r"^(?:https?://)?(?:www\.)?github\.com/([^/]+)/([^/]+)(?:/.*)?$"
    match = re.match(pattern, cleaned_url, re.IGNORECASE)
    
    if not match:
        raise ValueError(f"Invalid GitHub repository URL: '{url}'. Expected format: https://github.com/owner/repo")
        
    owner, repo = match.groups()
    if not owner or not repo:
        raise ValueError(f"Could not extract owner and repository from URL: '{url}'")
        
    return owner, repo

def get_auth_headers() -> Dict[str, str]:
    """
    Constructs authorization and headers for GitHub REST API requests securely.
    """
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers