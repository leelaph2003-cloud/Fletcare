@echo off
start /min "" cmd /c "cd /d C:\Users\shivaleela\Downloads\Fleet care\Fleet care\frontend\static && python -m http.server 8001"

start /min "" cmd /c "cd /d C:\Users\shivaleela\Downloads\Fleet care\Fleet care\backend && python manage.py runserver 8000"

timeout /t 4 /nobreak >nul

start "" "http://127.0.0.1:8000"