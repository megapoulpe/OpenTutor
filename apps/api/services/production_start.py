"""Migrate before accepting requests; failures prevent a partial startup."""
import subprocess
import sys
from services.server import main

if __name__ == "__main__":
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)
    main()
