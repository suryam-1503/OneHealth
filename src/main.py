from fastapi import FastAPI
from fastapi.responses import JSONResponse
import threading

from src.automation.app import run_automation, stop_automation, check_stop_flag
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

app = FastAPI(title="OneHealth Automation API")

automation_thread = None
automation_running = False


@app.get("/")
def root():
    return {"message": "OneHealth Automation API Running"}


@app.post("/start")
def start_automation():
    global automation_thread, automation_running

    if automation_running:
        return JSONResponse(content={"status": "already running"}, status_code=400)

    def task():
        global automation_running
        try:
            run_automation(headless=False)
        finally:
            automation_running = False

    automation_running = True

    automation_thread = threading.Thread(target=task)
    automation_thread.daemon = True
    automation_thread.start()

    logger.info("Automation started")

    return {"status": "started"}


@app.post("/stop")
def stop_automation_api():
    global automation_running

    if not automation_running:
        return {"status": "not running"}

    stop_automation()
    automation_running = False

    logger.info("Automation stopping")

    return {"status": "stopping"}


@app.get("/status")
def automation_status():

    if automation_running and not check_stop_flag():
        return {"status": "running"}

    return {"status": "stopped"}


#  Append this at the bottom
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="localhost", port=8000)
