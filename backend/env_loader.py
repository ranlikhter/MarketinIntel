"""
Shared environment loading for backend processes.
"""

from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


@lru_cache(maxsize=1)
def load_backend_env() -> None:
    """
    Load local backend environment files once.

    Load order is specific to general so local-only secrets win:
    1. backend/.env.local
    2. backend/.env
    3. repo/.env.local
    4. repo/.env
    """
    backend_dir = Path(__file__).resolve().parent
    repo_dir = backend_dir.parent

    candidates = [
        backend_dir / ".env.local",
        backend_dir / ".env",
        repo_dir / ".env.local",
        repo_dir / ".env",
    ]

    for env_file in candidates:
        if env_file.exists():
            load_dotenv(env_file, override=False)
