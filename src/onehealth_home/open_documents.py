from playwright.sync_api import Page, expect
from src.utils.logger import setup_logger


logger = setup_logger(__name__)

def documents_reporting(page: Page):
    """
    Navigate to Documents & Reporting section with fallback options
    Handles different page structures and locator changes
    """
    logger.info("Starting navigation to Documents & Reporting")

    # Try multiple possible locators for Documents & Reporting link
    possible_locators = [
        "[data-testid='documents-and-reporting-link']",
        "a:has-text('Documents and Reporting')",
        "a:has-text('Documents & Reporting')",
        "a[href*='documents']",
        "a[href*='reporting']",
        "button:has-text('Documents and Reporting')",
        "button:has-text('Documents & Reporting')",
        "text=Documents and Reporting",
        "text=Documents & Reporting"
    ]

    docs_reporting = None
    for locator in possible_locators:
        try:
            docs_reporting = page.locator(locator)
            if docs_reporting.count() > 0:
                logger.info(f"Found Documents & Reporting using locator: {locator}")
                break
        except Exception as e:
            logger.debug(f"Locator {locator} not found: {e}")
            continue

    if not docs_reporting or docs_reporting.count() == 0:
        logger.error("Could not find Documents & Reporting link with any locator")
        # Try to find any link that might lead to documents
        try:
            docs_reporting = page.locator("a[href*='document']").first
            if docs_reporting.count() > 0:
                logger.info("Found document-related link as fallback")
        except:
            pass

    if not docs_reporting or docs_reporting.count() == 0:
        logger.error("Documents & Reporting navigation failed - link not found")
        raise Exception("Could not locate Documents & Reporting section")

    try:
        expect(docs_reporting).to_be_visible(timeout=30000)
        expect(docs_reporting).to_be_enabled()
        docs_reporting.click()
        logger.info("Clicked Documents & Reporting link")
    except Exception as e:
        logger.error(f"Failed to click Documents & Reporting: {e}")
        # Try clicking without expectation checks as fallback
        try:
            docs_reporting.click(timeout=10000)
            logger.info("Clicked Documents & Reporting with fallback method")
        except Exception as e2:
            logger.error(f"Fallback click also failed: {e2}")
            raise Exception("Could not click Documents & Reporting link")

    page.wait_for_load_state("networkidle")
    logger.info("Documents & Reporting page loaded")

    # ───── Document Library ─────
    possible_library_locators = [
        "button:has(span:text('Document Library'))",
        "button:has-text('Document Library')",
        "a:has-text('Document Library')",
        "text=Document Library",
        "button:has(span:contains('Document'))",
        "button:has(span:contains('Library'))"
    ]

    document_library = None
    for locator in possible_library_locators:
        try:
            document_library = page.locator(locator)
            if document_library.count() > 0:
                logger.info(f"Found Document Library using locator: {locator}")
                break
        except Exception as e:
            logger.debug(f"Document Library locator {locator} not found: {e}")
            continue

    if not document_library or document_library.count() == 0:
        logger.error("Could not find Document Library button")
        # Try to find any button that might be the document library
        try:
            document_library = page.locator("button").filter(has_text="Document").first
            if document_library.count() > 0:
                logger.info("Found Document-related button as fallback")
        except:
            pass

    if not document_library or document_library.count() == 0:
        logger.error("Document Library navigation failed - button not found")
        raise Exception("Could not locate Document Library")

    try:
        expect(document_library).to_be_visible(timeout=30000)
        expect(document_library).to_be_enabled()
        document_library.click()
        logger.info("Clicked Document Library button")
    except Exception as e:
        logger.error(f"Failed to click Document Library: {e}")
        # Try clicking without expectation checks as fallback
        try:
            document_library.click(timeout=10000)
            logger.info("Clicked Document Library with fallback method")
        except Exception as e2:
            logger.error(f"Fallback click also failed: {e2}")
            raise Exception("Could not click Document Library button")

    page.wait_for_load_state("networkidle")
    logger.info("Document Library page loaded successfully")
