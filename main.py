"""
Entrypoint to run the SFCC Promotion Management Agent Streamlit application.
"""

import sys
import subprocess


def main():
    """Launch Streamlit application."""
    cmd = [sys.executable, "-m", "streamlit", "run", "app.py"]
    subprocess.run(cmd)


if __name__ == "__main__":
    main()
