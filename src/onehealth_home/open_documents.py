from playwright.sync_api import Page
from src.utils.logger import setup_logger


logger = setup_logger(__name__)


def documents_reporting(page: Page):
    """
    Simple navigation to Documents & Reporting -> Document Library
    """
    logger.info("Starting navigation to Documents & Reporting")

    # Step 1: Click the Documents & Reporting menu button
    docs_button = page.locator("[data-testid='documents-and-reporting-link']")
    
    if docs_button.count() == 0:
        logger.error("Documents & Reporting button not found")
        raise Exception("Could not locate Documents & Reporting button")
    
    docs_button.click()
    logger.info("Clicked Documents & Reporting button")
    
    # Wait 2-3 seconds for menu to open
    page.wait_for_timeout(1000)
    
    # Step 2: Click Document Library from the menu
    doc_library = page.locator("button:has(span:text('Document Library'))")
    
    if doc_library.count() == 0:
        logger.error("Document Library button not found")
        raise Exception("Could not locate Document Library button")
    
    doc_library.click()
    logger.info("Clicked Document Library button")
    
    # Wait for page to load
    
    page.wait_for_timeout(2000)
    logger.info("Document Library page loaded successfully")