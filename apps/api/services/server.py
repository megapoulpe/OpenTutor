"""Portable API entry point; psycopg async requires SelectorEventLoop on Windows."""
import asyncio
import os
import sys
import subprocess
from pathlib import Path


def main():
    if sys.platform == "win32":
        for stream in (sys.stdout, sys.stderr):
            if hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8")
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    from config import settings
    if settings.database_url.startswith("postgresql"):
        subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"],
                       cwd=Path(__file__).resolve().parents[1], check=True)
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", "8000")), loop="asyncio")


if __name__ == "__main__":
    main()
