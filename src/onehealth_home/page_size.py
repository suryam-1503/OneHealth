from playwright.sync_api import TimeoutError, expect
from src.utils.logger import setup_logger
logger = setup_logger(__name__)
def set_page_size(page, size: int):
    """
    Set the page size for better pagination performance.
    Enhanced to handle different page structures and be more robust.
    """
    # Try multiple possible page size selectors
    page_size_selectors = [
        "button[role='combobox'].abyss-pagination-page-size-select-input",
        "button.abyss-pagination-page-size-select-input",
        "button[data-testid*='page-size']",
        "button[aria-label*='page size']",
        "select.abyss-pagination-page-size-select-input",
        "select[data-testid*='page-size']"
    ]
    
    page_size_btn = None
    
    # Find the page size control
    for selector in page_size_selectors:
        page_size_btn = page.locator(selector)
        if page_size_btn.count() > 0:
            try:
                expect(page_size_btn).to_be_visible(timeout=3000)
                logger.info(f"Found page size control: {selector}")
                break
            except:
                page_size_btn = None
    
    if not page_size_btn or page_size_btn.count() == 0:
        logger.warning(f"No page size control found, skipping page size setting")
        return False

    try:
        # Wait for the page size button to be visible and clickable
        expect(page_size_btn).to_be_visible(timeout=5000)
        expect(page_size_btn).to_be_enabled(timeout=5000)
        
        page_size_btn.click()
        page.wait_for_timeout(500)  # Increased wait time

        # Try to find the specific size option first
        size_option_selectors = [
            f"div[role='option']:has-text('{size}')",
            f"li:has-text('{size}')",
            f"option:has-text('{size}')",
            f"div:has-text('{size}')",
            f"span:has-text('{size}')"
        ]
        
        size_option = None
        for option_selector in size_option_selectors:
            size_option = page.locator(option_selector)
            if size_option.count() > 0:
                try:
                    expect(size_option.first).to_be_visible(timeout=2000)
                    logger.info(f"Found size option: {option_selector}")
                    break
                except:
                    size_option = None
        
        if size_option and size_option.count() > 0:
            # Click the specific size option
            size_option.first.click()
            logger.info(f"Set page size to {size} using option selector")
        else:
            # Fallback to keyboard navigation
            logger.info(f"Size {size} not found as option, using keyboard navigation")
            
            # Navigate to the desired size using arrow keys
            # This is more reliable than fixed number of presses
            max_attempts = 15  # Increased attempts
            for _ in range(max_attempts):
                page.keyboard.press("ArrowDown")
                page.wait_for_timeout(300)  # Increased wait time
                
                # Check if we've reached the desired size
                current_selection_selectors = [
                    "div[role='option'][aria-selected='true']",
                    "li[aria-selected='true']",
                    "option[selected]",
                    "div[aria-selected='true']"
                ]
                
                current_selection = None
                for sel in current_selection_selectors:
                    current_selection = page.locator(sel)
                    if current_selection.count() > 0:
                        break
                
                if current_selection and current_selection.count() > 0:
                    current_text = current_selection.first.inner_text().strip()
                    if current_text == str(size):
                        break
            
            page.keyboard.press("Enter")
        
        page.wait_for_timeout(2000)  # Increased wait time for page to update

        logger.info(f"Successfully set page size to {size}")
        return True

    except Exception as e:
        logger.error(f"Could not set page size to {size}: {e}")
        return False
