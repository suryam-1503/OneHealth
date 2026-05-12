from playwright.sync_api import Page
from src.utils.logger import setup_logger


logger = setup_logger(__name__)


def ensure_status_column_visible(page: Page) -> bool:
    """
    Check if Status column exists without scrolling.
    Returns True if Status column is found, False otherwise.
    No scrolling is performed to save time.
    """
    try:
        # Simply check if any column header contains "Status" text
        # No scrolling - just check what's already visible
        headers = page.locator("div[role='columnheader']")
        header_count = headers.count()

        for j in range(header_count):
            try:
                text = headers.nth(j).text_content().strip().lower()
                if "status" in text:
                    logger.info(f"Status column found at position {j}")
                    return True
            except Exception:
                continue

        logger.info("Status column not found in visible headers - skipping status check")
        return False
    except Exception as e:
        logger.warning(f"Could not check for Status column: {e}")
        return False
