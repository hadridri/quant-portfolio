"""Spyder: open this file and press F5, the app opens in the browser."""
import subprocess
import sys
from pathlib import Path

subprocess.run([sys.executable, "-m", "streamlit", "run", "streamlit_app.py"], cwd=Path(__file__).resolve().parent)
