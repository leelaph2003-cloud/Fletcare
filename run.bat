@echo off
echo Starting Fleet Care...
start http://127.0.0.1:8000/
python backend/manage.py runserver
