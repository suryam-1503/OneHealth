from playwright.sync_api import sync_playwright
from src.gsheet.gsheet_client import get_uhc_file_sheet
from src.login.onehealth_login import run_login
from src.onehealth_home.open_documents import documents_reporting
from src.automation.scrape_and_download_workflow_final import process_section
from src.utils.logger import setup_logger
from src.gsheet.gsheet_writer import clear_sheet

import threading
import time

logger = setup_logger(__name__)

# Stop signal
stop_event = threading.Event()

# Global browser objects
playwright_instance = None
page = None


def check_stop_flag():
    """Check if automation should stop"""
    return stop_event.is_set()


def stop_automation():
    """Stop automation and close browser"""
    global stop_event, page, playwright_instance

    stop_event.set()
    logger.info("Stop signal sent to automation")

    try:
        if page:
            logger.info("Closing browser page...")
            page.context.close()
            page = None

        if playwright_instance:
            playwright_instance.stop()
            playwright_instance = None

    except Exception as e:
        logger.error(f"Error closing browser: {e}")


def safe_wait(seconds):
    """Wait but allow stop check"""
    for _ in range(seconds * 10):
        if check_stop_flag():
            logger.info("Stopping during wait")
            return
        time.sleep(0.1)


def run_automation(headless=False):

    global stop_event, playwright_instance, page

    stop_event.clear()

    try:

        logger.info("Starting browser...")

        playwright_instance = sync_playwright().start()

        page = run_login(playwright_instance, headless=headless)

        logger.info("Logged in")

        if check_stop_flag():
            return

        sheet = get_uhc_file_sheet()

        if not sheet:
            logger.info("Sheet not available (downloads only)")
        else:
            clear_sheet(sheet)    
            logger.info("Google Sheet cleared for new run")
            

        documents_reporting(page)

        safe_wait(3)

        if check_stop_flag():
            return

        process_section(page, "Appeals and Disputes", sheet)

        if check_stop_flag():
            return

        safe_wait(2)

        process_section(page, "Claim Letters", sheet)

        if check_stop_flag():
            return

        safe_wait(2)
        
        process_section(page, "HouseCalls Documentation", sheet)

        if check_stop_flag():
            return
        safe_wait(2)

        process_section(page, "Overpayment Documents", sheet)

        if check_stop_flag():
            return

        safe_wait(2)

        process_section(page, "Prior Auth Letters", sheet)

        logger.info("Workflow completed successfully")

    except Exception as e:
        logger.error(f"Automation error: {e}")

    finally:

        try:
            if page:
                page.context.close()

            if playwright_instance:
                playwright_instance.stop()

        except Exception as e:
            logger.error(f"Cleanup error: {e}")