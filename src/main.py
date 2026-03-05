import signal
import os
from fastapi import FastAPI
from pydantic import BaseModel
import threading
from src.automation.app import run_automation  # import your main function

app = FastAPI(title="OneHealth Automation API")


# # Request model
# class SectionsRequest(BaseModel):
#     uhc_file_mode: bool = False

automation_running = False


@app.post("/start")
def run_sections():
    global automation_running, automation_thread

    if automation_running:
        return {"status": "already running"}

    automation_running = True

    def task():
        global automation_running
        try:
            run_automation(headless=False)
        finally:
            automation_running = False

    automation_thread = threading.Thread(target=task, daemon=True)
    automation_thread.start()

    return {"status": "started", "message": "Automation started successfully"}


@app.post("/stop")
def stop_automation():
    global automation_running

    if not automation_running:
        return {"status": "not running", "message": "Automation is already stopped"}

    automation_running = False

    return {"status": "stopping", "message": "Automation stop signal sent"}


@app.get("/status")
async def get_automation_status():

    if automation_running:
        return {"status": "running", "message": "Automation is currently running"}
    return {"status": "Automation not running"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)
