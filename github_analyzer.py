import os

"""
github_analyzer.py
Core module for retrieving and analyzing GitHub repository metadata, file trees,
and source file contents for RepoSense AI.
"""

import base64
import logging
from typing import Dict, List, Any
import requests


from github_utils import parse_github_url, get_auth_headers

logger = logging.getLogger(__name__)

MAX_FILE_SIZE_BYTES = 1024 * 1024
BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".pdf", ".zip", ".tar",
    ".gz", ".exe", ".dll", ".so", ".bin", ".mp3", ".mp4", ".mov", ".woff",
    ".woff2", ".ttf", ".eot", ".pyc", ".lock", ".sqlite", ".db"
}

def get_repository_metadata(owner: str, repo: str) -> Dict[str, Any]:
    """Retrieves repository metadata from the GitHub REST API."""
    url = f"https://api.github.com/repos/{owner}/{repo}"
    headers = get_auth_headers()
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 404:
            raise ValueError(f"Repository '{owner}/{repo}' not found or is private.")
        if response.status_code == 403 and "rate limit" in response.text.lower():
            raise RuntimeError("GitHub API rate limit exceeded. Please provide a GITHUB_TOKEN environment variable.")
            
        response.raise_for_status()
        data = response.json()
        
        return {
            "name": data.get("name"),
            "full_name": data.get("full_name"),
            "description": data.get("description"),
            "default_branch": data.get("default_branch", "main"),
            "language": data.get("language"),
            "stars": data.get("stargazers_count", 0),
            "forks": data.get("forks_count", 0),
            "html_url": data.get("html_url"),
            "size_kb": data.get("size", 0)
        }
    except requests.RequestException as e:
        if isinstance(e, (ValueError, RuntimeError)):
            raise e
        raise RuntimeError(f"Failed to fetch repository metadata: {str(e)}")

def get_repository_tree(owner: str, repo: str, branch: str = "main") -> List[Dict[str, Any]]:
    """Retrieves the recursive folder and file structure tree of the repository."""
    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
    headers = get_auth_headers()
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        return data.get("tree", [])
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to fetch repository tree: {str(e)}")

def identify_important_files(tree: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Identifies key configuration files and source files from the file tree."""
    readme = None
    dependency_files = []
    source_files = []
    
    dependency_filenames = {"requirements.txt", "package.json", "pyproject.toml", "cargo.toml", "go.mod", "pom.xml", "dockerfile"}
    source_extensions = {".py", ".js", ".ts", ".java", ".cpp", ".c", ".go", ".rs", ".rb", ".php", ".cs", ".html", ".css"}
    
    for item in tree:
        if item.get("type") != "blob":
            continue
            
        path = item.get("path", "")
        filename = path.split("/")[-1].lower()
        
        if filename.startswith("readme."):
            if not readme or filename == "readme.md":
                readme = path
                
        if filename in dependency_filenames:
            dependency_files.append(path)
            
        _, ext = os.path.splitext(filename)
        if ext in source_extensions:
            parts = path.split("/")
            if not any(p in {"node_modules", "venv", ".git", "dist", "build", "__pycache__"} for p in parts):
                source_files.append(path)
                
    return {
        "readme": readme,
        "dependencies": dependency_files,
        "source_files": source_files
    }

def fetch_file_content(owner: str, repo: str, file_path: str) -> str:
    """Retrieves and decodes content of a specific text file, preventing binary downloads."""
    import os
    _, ext = os.path.splitext(file_path.lower())
    if ext in BINARY_EXTENSIONS:
        return "[Skipped: Binary or asset file]"
        
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}"
    headers = get_auth_headers()
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("size", 0) > MAX_FILE_SIZE_BYTES:
            return "[Skipped: File size exceeds 1MB limit]"
            
        encoding = data.get("encoding")
        content = data.get("content", "")
        
        if encoding == "base64":
            decoded_bytes = base64.b64decode(content)
            try:
                return decoded_bytes.decode("utf-8")
            except UnicodeDecodeError:
                return "[Skipped: Non-UTF-8 binary content]"
        return content
    except Exception as e:
        logger.warning(f"Could not fetch content for {file_path}: {str(e)}")
        return f"[Error fetching file content: {str(e)}]"

def analyze_repository(url: str, max_source_files: int = 5) -> Dict[str, Any]:
    """Master orchestrator function for complete repository data ingestion."""
    owner, repo = parse_github_url(url)
    metadata = get_repository_metadata(owner, repo)
    default_branch = metadata.get("default_branch", "main")
    
    tree = get_repository_tree(owner, repo, default_branch)
    important_files = identify_important_files(tree)
    
    file_contents = {}
    if important_files["readme"]:
        file_contents[important_files["readme"]] = fetch_file_content(owner, repo, important_files["readme"])
        
    for dep_file in important_files["dependencies"]:
        file_contents[dep_file] = fetch_file_content(owner, repo, dep_file)
        
    fetched_count = 0
    for src_file in important_files["source_files"]:
        if src_file in file_contents:
            continue
        if fetched_count >= max_source_files:
            break
        file_contents[src_file] = fetch_file_content(owner, repo, src_file)
        fetched_count += 1
        
    return {
        "owner": owner,
        "repo": repo,
        "metadata": metadata,
        "file_structure": [item.get("path") for item in tree if item.get("path")],
        "important_files": important_files,
        "file_contents": file_contents
    }