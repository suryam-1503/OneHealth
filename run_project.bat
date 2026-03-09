@echo off

pip install -r requirements.txt

playwright install

python -m uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload

pause