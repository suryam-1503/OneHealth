from playwright.sync_api import sync_playwright
from src.gsheet.gsheet_client import get_uhc_file_sheet
from src.login.onehealth_login import run_login
from src.onehealth_home.open_documents import documents_reporting
from src.automation.scrape_and_download_workflow_final import process_section
from src.utils.logger import setup_logger
import threading
import time

logger = setup_logger(__name__)

# Global flag for stopping automation
stop_automation_flag = threading.Event()

def check_stop_flag():
    """Check if automation should be stopped"""
    return stop_automation_flag.is_set()

def run_automation(headless=False):
    global stop_automation_flag
    stop_automation_flag.clear()  # Reset stop flag
    
    playwright_instance = None
    browser = None
    context = None
    page = None
    
    try:
        logger.info("Starting browser...")
        playwright_instance = sync_playwright().start()
        page = run_login(playwright_instance, headless=False)
        logger.info(" Logged in")

        sheet = get_uhc_file_sheet()
        if not sheet:
            logger.info(" Sheet not available (downloads only)")

        documents_reporting(page)
        page.wait_for_timeout(3000)

        # Check stop flag before each section
        if check_stop_flag():
            logger.info("Automation stopped by user request")
            return

        process_section(page, "Appeals and Disputes", sheet)
        if check_stop_flag():
            logger.info("Automation stopped by user request")
            return
            
        page.wait_for_timeout(2000)

        if check_stop_flag():
            logger.info("Automation stopped by user request")
            return

        process_section(page, "Claim Letters", sheet)
        if check_stop_flag():
            logger.info("Automation stopped by user request")
            return
            
        page.wait_for_timeout(2000)

        if check_stop_flag():
            logger.info("Automation stopped by user request")
            return

        process_section(page, "Overpayment Documents", sheet)
        if check_stop_flag():
            logger.info("Automation stopped by user request")
            return
            
        page.wait_for_timeout(2000)

        if check_stop_flag():
            logger.info("Automation stopped by user request")
            return

        process_section(page, "Prior Auth Letters", sheet)
        if check_stop_flag():
            logger.info("Automation stopped by user request")
            return
            
        page.wait_for_timeout(2000)

        logger.info("\n✓ Workflow completed successfully")
        
    except Exception as e:
        logger.error(f"Automation error: {e}")
        raise
    finally:
        # Clean up resources
        try:
            if page and hasattr(page, 'context'):
                page.context.close()
            if context:
                context.close()
            if browser:
                browser.close()
            if playwright_instance:
                playwright_instance.stop()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

def stop_automation():
    """Set the stop flag to terminate automation"""
    global stop_automation_flag
    stop_automation_flag.set()
    logger.info("Stop signal sent to automation")
