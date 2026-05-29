import subprocess
import threading
import webbrowser
import time
import sys
import os

def open_browser():
    time.sleep(2)  # Wait for server to start
    webbrowser.open('http://127.0.0.1:8000')

# Open browser in background thread
threading.Thread(target=open_browser).start()

# Run the Django dev server
os.chdir(os.path.dirname(os.path.abspath(__file__)))
subprocess.run([sys.executable, 'manage.py', 'runserver'])