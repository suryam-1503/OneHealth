from fastapi import FastAPI
import threading
import signal
import os
import sys
from src.automation.app import run_automation, stop_automation  # import your main function and stop function
from src.utils.logger import setup_logger

app = FastAPI(title="OneHealth Automation API")

logger = setup_logger(__name__)

# Global variables for process management
automation_running = False
automation_thread = None
automation_process = None

@app.post("/start")
def run_sections():
    global automation_running, automation_thread, automation_process

    if automation_running:
        return {"status": "already running"}

    automation_running = True
    automation_process = os.getpid()  # Store current process ID

    def task():
        global automation_running
        try:
            run_automation(headless=False)
        except Exception as e:
            logger.error(f"Automation error: {e}")
        finally:
            automation_running = False

    automation_thread = threading.Thread(target=task, daemon=True)
    automation_thread.start()

    return {"status": "started", "message": "Automation started successfully"}


@app.post("/stop")
def stop_automation_endpoint():
    global automation_running, automation_thread, automation_process

    if not automation_running:
        return {"status": "not running", "message": "Automation is already stopped"}

    # First, try graceful shutdown using the stop function
    try:
        stop_automation()
        logger.info("Graceful stop signal sent to automation")
    except Exception as e:
        logger.error(f"Error during graceful shutdown: {e}")
    
    # Then set the running flag to false
    automation_running = False
    
    # Force terminate the process if it exists and graceful shutdown didn't work
    if automation_process and automation_process != os.getpid():
        try:
            os.kill(automation_process, signal.SIGTERM)
            logger.info("Sent SIGTERM to automation process")
        except ProcessLookupError:
            logger.warning("Process already terminated")
        except Exception as e:
            logger.error(f"Error terminating process: {e}")
    
    # Also try to terminate current process if we're in the same process
    if automation_process == os.getpid():
        try:
            # Try graceful shutdown first
            if automation_thread and automation_thread.is_alive():
                # Set thread to daemon to allow it to be killed
                automation_thread.daemon = True
        except Exception as e:
            logger.error(f"Error during thread cleanup: {e}")

    return {"status": "stopping", "message": "Automation stop signal sent and process terminated"}


@app.get("/status")
async def get_automation_status():
    if automation_running:
        return {"status": "running", "message": "Automation is currently running"}
    return {"status": "stopped", "message": "Automation not running"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)
