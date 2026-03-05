from playwright.sync_api import Page, expect

def documents_reporting(page: Page):

    # ───── Documents & Reporting ─────
    docs_reporting = page.locator("[data-testid='documents-and-reporting-link']")
    expect(docs_reporting).to_be_visible(timeout=30000)
    expect(docs_reporting).to_be_enabled()
    docs_reporting.click()

    page.wait_for_load_state("networkidle")

    # ───── Document Library ─────
    document_library = page.locator(
        "button:has(span:text('Document Library'))"
    )

    expect(document_library).to_be_visible(timeout=30000)
    expect(document_library).to_be_enabled()
    document_library.click()

    page.wait_for_load_state("networkidle")  