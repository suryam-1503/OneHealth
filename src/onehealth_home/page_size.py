

from playwright.sync_api import TimeoutError, expect

def set_page_size(page, size: int):

    page_size_btn = page.locator(
        "button[role='combobox'].abyss-pagination-page-size-select-input"
    )

    try:
        
        expect(page_size_btn).to_be_visible(timeout=5000)
        page_size_btn.click()
        page.wait_for_timeout(300)

        #  Always press TAB 4 times
        for _ in range(4):
            page.keyboard.press("ArrowDown")
            page.wait_for_timeout(150)

        page.keyboard.press("Enter")
        page.wait_for_timeout(1000)


    except TimeoutError:
        print(f"Could not set page size to {size}")