import subprocess
import threading
import webbrowser
import time
import sys
import os

def open_browser():
    time.sleep(2)  # Wait for server to start
    url = 'http://127.0.0.1:8000'
    # Open in Microsoft Edge
    try:
        edge_path = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
        if not os.path.exists(edge_path):
            edge_path = r'C:\Program Files\Microsoft\Edge\Application\msedge.exe'
        webbrowser.register('edge', None, webbrowser.BackgroundBrowser(edge_path))
        webbrowser.get('edge').open(url)
    except Exception:
        # Fallback to default browser
        webbrowser.open(url)

# Open browser in background thread
threading.Thread(target=open_browser).start()

# Run the Django dev server
os.chdir(os.path.dirname(os.path.abspath(__file__)))
subprocess.run([sys.executable, 'manage.py', 'runserver'])