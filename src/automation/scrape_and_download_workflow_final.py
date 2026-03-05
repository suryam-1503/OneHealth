from playwright.sync_api import sync_playwright, Page, expect
from pathlib import Path
import time
from datetime import datetime

from src.login.onehealth_login import run_login
from src.onehealth_home.page_size import set_page_size
from src.onehealth_home.open_documents import documents_reporting
from src.gsheet.gsheet_client import get_uhc_file_sheet
from src.gsheet.gsheet_writer import (
    bulk_update_uhc_file_status,
    get_practices_from_sheet,
)

# =========================
# CONSTANTS (FIXED)
# =========================

TABLE_ROWS = "tbody tr[role='row']"
NEXT_BTN = "button[aria-label='next page']"
PREV_BTN = "button[aria-label='previous page']"
BREADCRUMB = "span[data-testid='folderpath_0']"

COL_MAP = {
    "Appeals and Disputes": 1,
    "Claim Letters": 2,
    "Overpayment Documents": 3,
    "Prior Auth Letters": 4,
}

# =========================
# GENERIC WAITS
# =========================


def wait_for_practice_table(page: Page):
    page.wait_for_selector("tbody tr[role='row']", timeout=30_000)


def wait_for_document_table(page: Page):
    page.wait_for_selector(
        "tbody tr, div:has-text('No documents found')", timeout=45_000
    )


# =========================
# NAVIGATION HELPERS
# =========================


def go_to_first_page(page: Page):
    while True:
        prev = page.locator(PREV_BTN).first
        if prev.is_disabled():
            break
        prev.click()
        time.sleep(1)


def click_breadcrumb(page: Page):
    """
    Clicks the main section breadcrumb safely after download
    """
    try:
        # Re-locate the breadcrumb AFTER download completes
        crumb = page.locator(BREADCRUMB).first

        # Wait until visible & clickable
        expect(crumb).to_be_visible(timeout=15_000)
        crumb.click()

        # Wait for the page to load and table to be available
        page.wait_for_timeout(2000)
        
        # Check if the table is visible before waiting for it
        # Use a more specific selector to avoid strict mode violations
        table_visible = page.locator("tbody tr[role='row']").first.is_visible()
        if table_visible:
            wait_for_practice_table(page)
        else:
            # If table is not visible, wait a bit more and try again
            page.wait_for_timeout(3000)
            if page.locator("tbody tr[role='row']").first.is_visible():
                wait_for_practice_table(page)
        
        time.sleep(1.5)  # optional buffer
        print("Breadcrumb clicked successfully")
    except Exception as e:
        print(f"Failed to click breadcrumb: {e}")
        # If breadcrumb fails, try to navigate back manually
        try:
            page.go_back()
            page.wait_for_timeout(2000)
            if page.locator("tbody tr[role='row']").first.is_visible():
                wait_for_practice_table(page)
        except:
            pass


# =========================
# PHASE 1 — SCRAPE + WRITE
# =========================


def wait_for_table(page: Page):
    page.wait_for_selector("tbody#sub-folders-data-table", timeout=45_000)


def wait_for_rows_to_load(page: Page, table_locator: str, timeout: int = 30_000):
    """
    Wait until table rows are fully loaded and stable.
    """
    start = time.time()
    previous_count = -1

    while True:
        rows = page.locator(table_locator)
        current_count = rows.count()
        if current_count == previous_count and current_count > 0:
            break  # row count stabilized
        previous_count = current_count
        if (time.time() - start) * 1000 > timeout:
            break
        page.wait_for_timeout(500)
    return page.locator(table_locator)


# =========================
# Scrape all practice names
# =========================
def scrape_all_practice_names(page: Page, sheet, section_name: str):
    print(f"\n--- Scraping ALL practices for {section_name} ---")

    set_page_size(page, 20)
    wait_for_table(page)
    rows = wait_for_rows_to_load(page, TABLE_ROWS)

    practices = []
    page_num = 1

    while True:
        print(f" Scraping page {page_num}")

        rows = wait_for_rows_to_load(page, TABLE_ROWS)
        total_rows = rows.count()

        for i in range(total_rows):
            row = rows.nth(i)

            # clickable practice
            btn = row.locator("button#folder-level-select-link")
            # non-clickable practice
            span = row.locator("span:not([aria-hidden])")

            if btn.count():
                name = btn.inner_text().strip()
            elif span.count():
                name = span.inner_text().strip()
            else:
                continue

            if name and name not in practices:
                practices.append(name)

        next_btn = page.locator(NEXT_BTN).first
        if next_btn.is_disabled():
            break

        next_btn.click()
        wait_for_practice_table(page)
        set_page_size(page, 20)  # keep page size consistent
        page_num += 1

    print(f" Total practices scraped: {len(practices)}")

    # Push to sheet
    if sheet and practices:
        col = COL_MAP[section_name]
        sheet.update(range_name=f"{chr(64 + col)}2", values=[[p] for p in practices])
        print(" All practices pushed to Google Sheet")

    return practices


# =========================
# Download logic
# =========================
def download_files_for_practice(
    page: Page, practice_name: str, section_name: str
) -> bool:

    print(f" Entered practice: {practice_name}")
    wait_for_document_table(page)
    set_page_size(page, 50)

    select_all = page.locator("input.abyss-data-table-selection[type='checkbox']").first
    expect(select_all).to_be_visible(timeout=15_000)
    if not select_all.is_checked():
        select_all.click()
        page.wait_for_timeout(500)

    checked_boxes = page.locator(
        "input.abyss-data-table-selection[type='checkbox']:checked"
    )
    file_count = checked_boxes.count()
    if file_count == 0:
        print(" No files selected")
        return False

    bulk_actions = page.locator("[data-testid*='bulk-actions-dropdown']").first
    expect(bulk_actions).to_be_visible(timeout=10_000)
    bulk_actions.click()
    
    # Wait for the dropdown menu to appear
    page.wait_for_timeout(2000)

    download_item = page.locator("div[role='menuitem']:has-text('Download')").first
    expect(download_item).to_be_visible(timeout=10_000)
    
    # Click the download item
    download_item.click()
    
    # Wait for the download to start
    page.wait_for_timeout(2000)

    all_saved = True

    # Handle multiple downloads
    downloads = []
    
    # Wait for downloads to complete
    try:
        # Wait for the first download to start
        download1 = page.wait_for_event("download", timeout=30000)
        downloads.append(download1)
        
        # Wait for additional downloads (up to 10 seconds for more downloads)
        start_time = time.time()
        while time.time() - start_time < 10:
            try:
                download = page.wait_for_event("download", timeout=2000)
                downloads.append(download)
            except:
                break
                
    except Exception as e:
        print(f"Error waiting for downloads: {e}")

    # Process all captured downloads
    for i, download in enumerate(downloads):
        print(f"Downloaded file {i+1} of {len(downloads)}")
        saved = save_download(download, practice_name, section_name, i)
        if not saved:
            all_saved = False
    
    return all_saved


from pathlib import Path
from datetime import datetime


def save_download(
    download, practice_name: str, section_name: str, file_index: int = 0
) -> bool:
    try:
        safe_name = "".join(c if c not in r'<>:"/\\|?*' else "_" for c in practice_name)

        # Generate dynamic year and date folder
        today = datetime.today()
        year_folder = today.strftime("%Y")
        date_folder = today.strftime("%m %d %Y")

        # Google Drive path
        base = Path(
            r"G:\Shared drives\Reimbursement and Inventory Analysis\UHC Vault\Completed"
        ) / year_folder / date_folder / safe_name / section_name

        base.mkdir(parents=True, exist_ok=True)

        # Get original filename
        original_filename = download.suggested_filename

        name_parts = original_filename.rsplit(".", 1)
        if len(name_parts) == 2:
            file_extension = name_parts[1]
            file_without_ext = name_parts[0]
        else:
            file_extension = ""
            file_without_ext = original_filename

        # Handle multiple files
        if file_index > 0:
            filename = f"{practice_name} - {file_without_ext}_{file_index}.{file_extension}"
        else:
            filename = f"{practice_name} - {file_without_ext}.{file_extension}"

        file_path = base / filename
        download.save_as(str(file_path))

        print(f"{practice_name} file downloaded: {file_path}")
        return True

    except Exception as e:
        print(f"Save failed: {e}")
        return False

# =========================
# PHASE 2 — COMPARE + DOWNLOAD
# =========================


def process_section(page: Page, section_name: str, sheet):

    print(f"\n=== Processing {section_name} ===")

    # Open the section
    page.locator(f"a:has-text('{section_name}')").click()
    page.wait_for_load_state("networkidle")

    set_page_size(page, 20)

    # Scrape all practice names into the sheet
    scrape_all_practice_names(page, sheet, section_name)

    sheet_practices = get_practices_from_sheet(sheet, section_name)
    print(f"{len(sheet_practices)} practices loaded from sheet")

    # Store updates here for bulk update
    batch_updates = {}
    
    # Track if we've encountered non-clickable practices
    encountered_non_clickable = False
    
    # Process practices in the order they appear in the Google Sheet
    for practice in sheet_practices:
        print(f"Processing {practice} (from sheet order)")

        # If we've already found non-clickable practices, skip all remaining
        if encountered_non_clickable:
            print(f"Skipping {practice} (non-clickable pattern detected)")
            status = "FILE NOT FOUND"
            batch_updates[practice] = status
            
            # Update every 10 practices
            if sheet and len(batch_updates) >= 10:
                print(f"Bulk updating {len(batch_updates)} practices...")
                try:
                    bulk_update_uhc_file_status(sheet, section_name, batch_updates)
                    batch_updates.clear()
                except Exception as e:
                    print(f"Sheet bulk update failed: {e}")
            continue

        # Navigate to first page and set page size
        go_to_first_page(page)
        wait_for_practice_table(page)
        set_page_size(page, 20)

        # Find and click the practice
        practice_found = False
        page_num = 1

        while not practice_found:
            rows = page.locator(TABLE_ROWS)
            total_rows = rows.count()

            for i in range(total_rows):
                row = rows.nth(i)

                btn = row.locator("button#folder-level-select-link")
                span = row.locator("span:not([aria-hidden])")

                if btn.count() > 0:
                    row_practice = btn.inner_text().strip()
                    clickable = True
                elif span.count() > 0:
                    row_practice = span.inner_text().strip()
                    clickable = False
                else:
                    continue

                if row_practice == practice:
                    practice_found = True
                    print(f"Found {practice}")

                    if clickable:
                        if not btn.is_enabled():
                            print(f"Cannot open {practice}")
                            status = "FILE NOT FOUND"
                        else:
                            try:
                                btn.click(timeout=5000)
                                page.wait_for_timeout(2000)

                                success = download_files_for_practice(
                                    page, practice, section_name
                                )
                                status = "FILE DOWNLOADED" if success else "FILE NOT FOUND"

                            except Exception as e:
                                print(f"Failed for {practice}: {e}")
                                status = "FILE NOT FOUND"

                            finally:
                                click_breadcrumb(page)
                                set_page_size(page, 20)
                                wait_for_practice_table(page)
                    else:
                        print(f"Non-clickable practice: {practice}")
                        status = "FILE NOT FOUND"
                        encountered_non_clickable = True  # Mark that we found non-clickable practices

                    # Store result for bulk update
                    batch_updates[practice] = status

                    # Update every 10 practices
                    if sheet and len(batch_updates) >= 10:
                        print(f"Bulk updating {len(batch_updates)} practices...")
                        try:
                            bulk_update_uhc_file_status(sheet, section_name, batch_updates)
                            batch_updates.clear()
                        except Exception as e:
                            print(f"Sheet bulk update failed: {e}")

                    break

            if practice_found:
                break

            # Move to next page if practice not found
            next_btn = page.locator(NEXT_BTN).first
            if next_btn.is_disabled() or not next_btn.is_visible():
                print(f"Practice {practice} not found in {section_name}")
                status = "FILE NOT FOUND"
                
                # Store result for bulk update
                batch_updates[practice] = status
                
                # Update every 10 practices
                if sheet and len(batch_updates) >= 10:
                    print(f"Bulk updating {len(batch_updates)} practices...")
                    try:
                        bulk_update_uhc_file_status(sheet, section_name, batch_updates)
                        batch_updates.clear()
                    except Exception as e:
                        print(f"Sheet bulk update failed: {e}")
                break

            next_btn.click()
            wait_for_practice_table(page)
            set_page_size(page, 20)
            page_num += 1

    # Update remaining practices
    if sheet and batch_updates:
        print(f"\nUpdating remaining {len(batch_updates)} practices...")
        try:
            bulk_update_uhc_file_status(sheet, section_name, batch_updates)
        except Exception as e:
            print(f"Sheet bulk update failed: {e}")

    print("All practices processed and sheet updated.")


# =========================
# MASTER WORKFLOW
# =========================


# def scrape_and_download_workflow_final():
#     with sync_playwright() as playwright:
#         print("Starting browser...")
#         page = run_login(playwright, headless=False)
#         print(" Logged in")

#         sheet = get_uhc_file_sheet()
#         if not sheet:
#             print(" Sheet not available (downloads only)")

#         documents_reporting(page)
#         page.wait_for_timeout(3000)

#         process_section(page, "Appeals and Disputes", sheet)
#         process_section(page, "Claim Letters", sheet)
#         process_section(page, "Overpayment Documents", sheet)
#         process_section(page, "Prior Auth Letters", sheet)

#         print("\n✓ Workflow completed successfully")


# if __name__ == "__main__":
#     scrape_and_download_workflow_final()
