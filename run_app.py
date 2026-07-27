import os
import sys
import subprocess

root = r"c:\Users\ChamithSe\OneDrive - MAS Holdings (Pvt) Ltd\THRED DB\OneDrive_2026-07-27 (1)"
os.chdir(root)
cmd = [sys.executable, '-m', 'streamlit', 'run', 'app.py', '--server.headless', 'true', '--server.address', '127.0.0.1', '--server.port', '8501']
print('Running:', cmd)
subprocess.call(cmd)
