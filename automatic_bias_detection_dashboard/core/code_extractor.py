"""Extract source code from a GitHub repo URL or uploaded zip file."""

from __future__ import annotations

import io
import re
import zipfile
from pathlib import PurePosixPath

import httpx

# File extensions to include
CODE_EXTENSIONS = {
    ".py", ".ipynb", ".r", ".R", ".jl",  # languages
    ".yaml", ".yml", ".toml", ".json", ".cfg", ".ini",  # config
    ".sh", ".bash",  # scripts
}

# Files/dirs to skip
SKIP_PATTERNS = {
    "__pycache__", ".git", "node_modules", ".venv", "venv",
    ".egg-info", "dist", "build", ".tox",
}

MAX_FILE_SIZE = 50_000  # chars per file
MAX_TOTAL_SIZE = 120_000  # total chars for all code


async def extract_code_from_github(repo_url: str) -> str | None:
    """Download and extract code from a GitHub repo URL.

    Supports URLs like:
    - https://github.com/user/repo
    - https://github.com/user/repo/tree/main
    """
    # Normalize URL to get the zip download link
    match = re.match(r"https?://github\.com/([^/]+)/([^/]+)(?:/tree/([^/]+))?", repo_url)
    if not match:
        return None

    owner, repo, branch = match.groups()
    branch = branch or "main"
    zip_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/{branch}.zip"

    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
            resp = await client.get(zip_url)
            if resp.status_code != 200:
                # Try 'master' if 'main' failed
                if branch == "main":
                    zip_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/master.zip"
                    resp = await client.get(zip_url)
                if resp.status_code != 200:
                    return None

            return extract_code_from_zip(resp.content)
    except Exception:
        return None


def extract_code_from_zip(zip_bytes: bytes) -> str:
    """Extract relevant source code files from a zip archive."""
    parts: list[str] = []
    total_size = 0

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        # Sort files for consistent ordering
        names = sorted(zf.namelist())

        for name in names:
            if zf.getinfo(name).file_size == 0:
                continue

            path = PurePosixPath(name)

            # Skip directories and non-code files
            if any(skip in path.parts for skip in SKIP_PATTERNS):
                continue
            if path.suffix not in CODE_EXTENSIONS:
                continue

            try:
                content = zf.read(name).decode("utf-8", errors="replace")
            except Exception:
                continue

            # Truncate large files
            if len(content) > MAX_FILE_SIZE:
                content = content[:MAX_FILE_SIZE] + "\n... [truncated]"

            # Strip the top-level directory (repo-branch/) from path
            display_path = "/".join(path.parts[1:]) if len(path.parts) > 1 else str(path)

            chunk = f"=== FILE: {display_path} ===\n{content}\n\n"

            if total_size + len(chunk) > MAX_TOTAL_SIZE:
                parts.append(f"... [remaining files truncated, total code exceeds {MAX_TOTAL_SIZE} chars]")
                break

            parts.append(chunk)
            total_size += len(chunk)

    return "".join(parts) if parts else ""
