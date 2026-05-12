from playwright.sync_api import Page, expect
from pathlib import Path
import time
from datetime import datetime
from src.login.onehealth_login import run_login
from src.onehealth_home.page_size import set_page_size
from src.onehealth_home.paginated_download import check_stop_flag
from src.gsheet.gsheet_writer import (
    bulk_update_uhc_file_status,
    get_failed_practices,
    get_practices_from_sheet,
)
from src.utils.logger import setup_logger
from src.onehealth_home.paginated_download import get_status_column_index
from src.automation.stautus_column import ensure_status_column_visible

logger = setup_logger(__name__)

# =========================l
# CONSTANTS (FIXED)
# =========================

TABLE_ROWS = "tbody tr[role='row']"
NEXT_BTN = "button[aria-label='next page']"
PREV_BTN = "button[aria-label='previous page']"
BREADCRUMB = "span[data-testid='folderpath_0']"

COL_MAP = {
    "Appeals and Disputes": 1,
    "Claim Letters": 2,
    "HouseCalls Documentation": 3,
    "Overpayment Documents": 4,
    "Prior Auth Letters": 5,
}

# =========================
# GENERIC WAITS
# =========================


def wait_for_practice_table(page: Page):
    page.wait_for_selector("tbody tr[role='row']", timeout=30_000)


def wait_for_document_table(page: Page):
    """
    Wait for document table to load with improved error handling and retry logic
    Enhanced to handle different page structures and loading states
    """
    max_retries = 5  # Increased retries
    retry_delay = 3000  # Increased delay between retries

    # Try multiple possible document table selectors
    document_selectors = [
        "tbody tr",  # Standard table rows
        "div.document-row",  # Alternative document row structure
        "div.file-row",  # Alternative file row structure
        "div[data-testid*='document']",  # Document test IDs
        "div[data-testid*='file']",  # File test IDs
        "div.abyss-data-table-row",  # Abyss table rows
        "div.grid-row",  # Grid-based rows
    ]

    # Try multiple possible "no documents" messages
    no_docs_selectors = [
        "div:has-text('No documents found')",
        "div:has-text('No files found')",
        "div:has-text('No results found')",
        "div:has-text('No items found')",
        "span:has-text('No documents found')",
        "p:has-text('No documents found')",
        "div.empty-state",
        "div.no-results",
    ]

    for attempt in range(max_retries):
        try:
            # First check if we're on a document page
            page.wait_for_timeout(2000)  # Increased delay after navigation

            # Check for loading indicators and wait for them to disappear
            loading_selectors = [
                "div:has-text('Loading')",
                ".loading-spinner",
                ".progress-bar",
                "div.loading",
                "span.loading",
                "div.spinner",
            ]

            for loading_selector in loading_selectors:
                try:
                    page.wait_for_selector(
                        loading_selector, state="hidden", timeout=3000
                    )
                    break
                except:
                    continue

            # Try to find document rows with multiple selectors
            document_found = False
            for doc_selector in document_selectors:
                try:
                    page.wait_for_selector(doc_selector, timeout=10000)
                    rows = page.locator(doc_selector)
                    if rows.count() > 0:
                        # Wait a bit more to ensure table is fully loaded
                        page.wait_for_timeout(2000)
                        logger.info(
                            f"Document table found with selector: {doc_selector}"
                        )
                        return True
                except:
                    continue

            # Check for "No documents found" message
            for no_docs_selector in no_docs_selectors:
                try:
                    no_docs = page.locator(no_docs_selector)
                    if no_docs.count() > 0:
                        logger.info(f"No documents message found: {no_docs_selector}")
                        return True
                except:
                    continue

            # If we get here, neither documents nor "no documents" message was found
            logger.warning(
                f"Attempt {attempt + 1}: No document table or empty state found"
            )

        except Exception as e:
            logger.error(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay/1000} seconds...")
                page.wait_for_timeout(retry_delay)
            else:
                logger.error("Max retries exceeded for document table wait")
                # Return False instead of raising to allow graceful handling
                return False

    return False


# =========================
# NAVIGATION HELPERS
# =========================
def go_to_first_page(page: Page):
    """
    Navigate to the first page with improved stability and error handling
    """
    max_attempts = 5
    for attempt in range(max_attempts):
        try:
            # Check if page is still valid
            if not page or not page.context:
                logger.error(f"Page context lost on attempt {attempt + 1}")
                raise Exception("Page context lost")

            prev = page.locator(PREV_BTN).first
            if prev.is_disabled():
                break

            # Wait for the button to be clickable
            expect(prev).to_be_enabled(timeout=5000)
            prev.click()

            # Wait for page navigation to complete with longer timeout
            page.wait_for_timeout(2000)

            # Verify we're still on the correct page and table is available
            try:
                # Check if we can still access the page
                page.title()  # This will throw if page is closed

                # Wait for table to be stable
                page.wait_for_selector(TABLE_ROWS, timeout=10000)

                # Verify table has rows
                if page.locator(TABLE_ROWS).count() > 0:
                    continue
                else:
                    # If table is not visible, wait a bit more
                    page.wait_for_timeout(3000)
                    if page.locator(TABLE_ROWS).count() > 0:
                        continue
                    else:
                        logger.error(
                            f"Page navigation unstable after attempt {attempt + 1}"
                        )

            except Exception as page_error:
                logger.error(
                    f"Page navigation error (attempt {attempt + 1}): {page_error}"
                )
                if (
                    "closed" in str(page_error).lower()
                    or "context" in str(page_error).lower()
                ):
                    raise Exception("Page context lost during navigation")

        except Exception as e:
            logger.error(f"Error navigating to first page (attempt {attempt + 1}): {e}")
            if attempt < max_attempts - 1:
                page.wait_for_timeout(3000)  # Increased delay between attempts
            else:
                logger.error("Failed to navigate to first page after maximum attempts")
                raise


def click_breadcrumb(page: Page):
    """
    Clicks the main section breadcrumb safely after download
    """
    try:
        # Re-locate the breadcrumb AFTER download completes
        crumb = page.locator(BREADCRUMB).first

        # Wait until visible & clickable
        expect(crumb).to_be_visible(timeout=15000)
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
        logger.info("Breadcrumb clicked successfully")
    except Exception as e:
        logger.error(f"Failed to click breadcrumb: {e}")
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
    logger.info(f"\n--- Scraping ALL practices for {section_name} ---")

    set_page_size(page, 20)
    wait_for_table(page)
    rows = wait_for_rows_to_load(page, TABLE_ROWS)

    practices = []
    page_num = 1
    stop_scraping = False

    while True:
        logger.info(f" Scraping page {page_num}")

        rows = wait_for_rows_to_load(page, TABLE_ROWS)
        total_rows = rows.count()

        for i in range(total_rows):
            row = rows.nth(i)

            icon = row.locator("span.material-symbols-rounded:has-text('circle')")

            #  STOP COMPLETELY when first non-circle appears
            if icon.count() == 0:
                logger.info("First non-circle practice found - stopping scraping")
                stop_scraping = True
                break

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

        #  break outer loop also
        if stop_scraping:
            break

        next_btn = page.locator(NEXT_BTN).first
        if next_btn.is_disabled():
            break

        next_btn.click()
        wait_for_practice_table(page)
        set_page_size(page, 20)  # Ensure page size stays at 20 after navigation
        page_num += 1

    logger.info(f" Total practices scraped: {len(practices)}")

    # Push to sheet
    if sheet and practices:
        col = COL_MAP[section_name]
        sheet.update(range_name=f"{chr(64 + col)}2", values=[[p] for p in practices])
        logger.info(" All practices pushed to Google Sheet")

    return practices


def download_files_with_pagination(
    page: Page, practice_name: str, section_name: str
) -> bool:
    logger.info(f"Starting paginated download for {practice_name}")

    try:
        page.wait_for_selector("tbody tr", timeout=30000)

        ensure_status_column_visible(page)

        downloaded_count = 0
        current_page = 1

        while True:
            if check_stop_flag():
                logger.info("Automation stopped by user request")
                return False

            logger.info(f"Processing page {current_page}")

            rows = page.locator("tbody tr")
            total_rows = rows.count()

            rows_to_download = []

            # -------------------------
            # FIND UNREAD ROWS
            # -------------------------
            for i in range(total_rows):
                try:
                    row = rows.nth(i)
                    status_div = row.locator("div[id^='read-']")

                    if status_div.count() == 0:
                        continue

                    status_text = status_div.first.text_content().strip().lower()

                    if status_text == "unread":
                        rows_to_download.append(i)

                except Exception as e:
                    logger.warning(f"Error reading row {i}: {e}")

            # -------------------------
            # SELECT + DOWNLOAD
            # -------------------------
            if rows_to_download:
                logger.info(
                    f"Found {len(rows_to_download)} unread rows on page {current_page}"
                )

                # select checkboxes
                for row_idx in rows_to_download:
                    try:
                        checkbox = rows.nth(row_idx).locator("input[type='checkbox']")
                        if checkbox.count() > 0 and not checkbox.is_checked():
                            checkbox.check()
                    except Exception as e:
                        logger.warning(f"Checkbox error: {e}")

                try:
                    bulk_actions = page.locator(
                        "[data-testid*='bulk-actions-dropdown']"
                    ).first
                    bulk_actions.click()
                    page.wait_for_timeout(1500)

                    download_item = page.locator(
                        "div[role='menuitem']:has-text('Download')"
                    ).first

                    logger.info(f"Starting download for {len(rows_to_download)} files")

                    downloads = []

                    with page.expect_download(timeout=120000) as d:
                        download_item.click()
                    downloads.append(d.value)

                    # capture remaining downloads
                    for _ in range(len(rows_to_download) - 1):
                        try:
                            with page.expect_download(timeout=10000) as d:
                                pass
                            downloads.append(d.value)
                        except:
                            break

                    # save files
                    for i, download in enumerate(downloads):
                        save_download(
                            download, practice_name, section_name, downloaded_count + i
                        )

                    downloaded_count += len(downloads)

                except Exception as e:
                    logger.error(f"Download error: {e}")

                # -------------------------
                # UNCHECK AFTER DOWNLOAD
                # -------------------------
                for row_idx in rows_to_download:
                    try:
                        checkbox = rows.nth(row_idx).locator("input[type='checkbox']")
                        if checkbox.count() > 0 and checkbox.is_checked():
                            checkbox.uncheck()
                    except:
                        pass

            # -------------------------
            # NEXT PAGE
            # -------------------------
            try:
                next_btn = page.locator("button[aria-label='next page']").first

                if not next_btn.is_visible(timeout=3000) or next_btn.is_disabled():
                    logger.info(f"Reached last page at {current_page}")
                    break

                next_btn.click()
                page.wait_for_selector("tbody tr", timeout=25000)
                page.wait_for_timeout(2000)

            except Exception as e:
                logger.error(f"Pagination error: {e}")
                break

            current_page += 1

        logger.info(f"Download complete. Total files downloaded: {downloaded_count}")
        return downloaded_count > 0

    except Exception as e:
        logger.error(f"Download failed: {e}")
        return False


# from pathlib import Path
# from datetime import datetime
# from pathlib import Path
# from datetime import datetime


def save_download(
    download, practice_name: str, section_name: str, file_index: int = 0
) -> bool:
    try:
        safe_name = "".join(c if c not in r'<>:"/\\|?*' else "_" for c in practice_name)

        # Generate dynamic year and date folder
        today = datetime.today()
        year_folder = today.strftime("%Y")
        date_folder = today.strftime("%m %d %Y")

        # Google Drive path - all files under practice folder (no section subfolder)
        base = (
            Path(
                r"G:\Shared drives\Reimbursement and Inventory Analysis\UHC Vault\Completed"
            )
            / year_folder
            / date_folder
            / safe_name
        )

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
            filename = (
                f"{practice_name} - {file_without_ext}_{file_index}.{file_extension}"
            )
        else:
            filename = f"{practice_name} - {file_without_ext}.{file_extension}"

        file_path = base / filename
        download.save_as(str(file_path))

        logger.info(f"{practice_name} file downloaded: {file_path}")
        return True

    except Exception as e:
        logger.error(f"Save failed: {e}")
        return False


# =========================
# PHASE 2 — COMPARE + DOWNLOAD
# =========================


def process_section(page: Page, section_name: str, sheet):

    logger.info(f"\n=== Processing {section_name} ===")

    if check_stop_flag():  #  stop check
        logger.info("Automation stopped before starting section")
        return

    # Open the section
    page.locator(f"a:has-text('{section_name}')").click()
    page.wait_for_load_state("networkidle")

    set_page_size(page, 20)

    # Scrape all practice names into the sheet
    scrape_all_practice_names(page, sheet, section_name)

    sheet_practices = get_practices_from_sheet(sheet, section_name)
    logger.info(f"{len(sheet_practices)} practices loaded from sheet")

    # Store updates here for bulk update
    batch_updates = {}

    # Track if we've encountered non-clickable practices
    encountered_non_clickable = False

    # Process practices in the order they appear in the Google Sheet
    for practice in sheet_practices:
        logger.info(f"Processing {practice} (from sheet order)")

        # If we've already found non-clickable practices, skip all remaining
        if encountered_non_clickable:
            logger.info(f"Skipping {practice} (non-clickable pattern detected)")
            status = "FILE NOT FOUND"
            batch_updates[practice] = status

            # Update every 10 practices
            if sheet and len(batch_updates) >= 10:
                logger.info(f"Bulk updating {len(batch_updates)} practices...")
                try:
                    bulk_update_uhc_file_status(sheet, section_name, batch_updates)
                    batch_updates.clear()
                except Exception as e:
                    logger.error(f"Sheet bulk update failed: {e}")
            continue

        # Check if we're still on the correct section page
        try:
            # Verify we're still on the correct section
            current_url = page.url
            if section_name.lower().replace(" ", "-") not in current_url.lower():
                logger.info(f"Navigation lost, returning to {section_name} section")
                # Navigate back to the section
                page.locator(f"a:has-text('{section_name}')").click()
                page.wait_for_load_state("networkidle")
                set_page_size(page, 20)
                # Navigate to first page (page size already set, no need to set again)
                go_to_first_page(page)
                wait_for_practice_table(page)
        except Exception as e:
            logger.error(f"Page navigation check failed: {e}")
            # If we can't verify the page, reload and try to navigate back
            try:
                page.reload()
                page.wait_for_load_state("networkidle")
                page.wait_for_timeout(3000)
                page.locator(f"a:has-text('{section_name}')").click()
                page.wait_for_load_state("networkidle")
                set_page_size(page, 20)
                go_to_first_page(page)
                wait_for_practice_table(page)
            except:
                logger.error(
                    f"Failed to return to {section_name} section for {practice}"
                )
                status = "FILE NOT FOUND"
                batch_updates[practice] = status
                continue

        # Navigate to first page if we are not already there or if we just returned to section
        # (Already handled in the navigation recovery blocks above)
        try:
            # Ensure we are on the first page at the start of each practice search if not already handled
            # go_to_first_page(page) # Removed redundant call here as it was causing loops
            wait_for_practice_table(page)
        except Exception as e:
            logger.error(f"Navigation failed for {practice}: {e}")
            # If navigation fails completely, mark as not found and continue
            status = "FILE NOT FOUND"
            batch_updates[practice] = status

            # Update every 10 practices
            if sheet and len(batch_updates) >= 10:
                logger.info(f"Bulk updating {len(batch_updates)} practices...")
                try:
                    bulk_update_uhc_file_status(sheet, section_name, batch_updates)
                    batch_updates.clear()
                except Exception as e:
                    logger.error(f"Sheet bulk update failed: {e}")
            continue

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

                if row_practice.lower() == practice.lower():
                    practice_found = True
                    logger.info(f"Found {practice}")

                    if clickable:
                        if not btn.is_enabled():
                            logger.info(f"Cannot open {practice}")
                            status = "FILE NOT FOUND"
                        else:
                            try:
                                btn.click(timeout=5000, force=True)
                                page.wait_for_timeout(2000)

                                success = download_files_with_pagination(
                                    page, practice, section_name
                                )
                                status = (
                                    "FILE DOWNLOADED" if success else "FILE NOT FOUND"
                                )

                            except Exception as e:
                                logger.error(f"Failed for {practice}: {e}")
                                status = "FILE NOT FOUND"

                            finally:
                                click_breadcrumb(page)
                                set_page_size(page, 20)
                                wait_for_practice_table(page)
                    else:
                        logger.info(f"Non-clickable practice: {practice}")
                        status = "FILE NOT FOUND"
                        encountered_non_clickable = (
                            True  # Mark that we found non-clickable practices
                        )

                    # Store result for bulk update
                    batch_updates[practice] = status

                    # Update every 10 practices
                    if sheet and len(batch_updates) >= 10:
                        logger.info(f"Bulk updating {len(batch_updates)} practices...")
                        try:
                            bulk_update_uhc_file_status(
                                sheet, section_name, batch_updates
                            )
                            batch_updates.clear()
                        except Exception as e:
                            logger.error(f"Sheet bulk update failed: {e}")

                    break

            if practice_found:
                break

            # Move to next page if practice not found
            next_btn = page.locator(NEXT_BTN).first
            if next_btn.is_disabled() or not next_btn.is_visible():
                logger.info(f"Practice {practice} not found in {section_name}")
                status = "FILE NOT FOUND"

                # Store result for bulk update
                batch_updates[practice] = status

                # Update every 10 practices
                if sheet and len(batch_updates) >= 10:
                    logger.info(f"Bulk updating {len(batch_updates)} practices...")
                    try:
                        bulk_update_uhc_file_status(sheet, section_name, batch_updates)
                        batch_updates.clear()
                    except Exception as e:
                        logger.error(f"Sheet bulk update failed: {e}")
                break

            next_btn.click()
            wait_for_practice_table(page)
            # set_page_size(page, 20) # Avoid redundant page size setting during pagination
            page_num += 1

    # Update remaining practices
    if sheet and batch_updates:
        logger.info(f"\nUpdating remaining {len(batch_updates)} practices...")
        try:
            bulk_update_uhc_file_status(sheet, section_name, batch_updates)
        except Exception as e:
            logger.error(f"Sheet bulk update failed: {e}")

    logger.info("All practices processed and sheet updated.")


from src.gsheet.gsheet_client import get_uhc_file_sheet
from src.utils.env_data import EnvData
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def get_practices_from_sheet(sheet, section_name: str) -> list[str]:
    """
    Get all practice names from the Google Sheet for a specific section.
    Returns list of practice names without status suffixes.
    """
    if not sheet:
        logger.info("Google Sheet not available for reading")
        return []

    logger.info(f"Reading practice names from Google Sheet for {section_name}...")

    col_mapping = {
        "Appeals and Disputes": 1,
        "Claim Letters": 2,
        "HouseCalls Documentation": 3,
        "Overpayment Documents": 4,
        "Prior Auth Letters": 5,
    }

    col = col_mapping.get(section_name, 1)
    column_values = sheet.col_values(col)
    practice_names = []

    for cell_value in column_values:
        if cell_value and cell_value.strip():
            if " - " in cell_value:
                name = cell_value.split(" - ")[0].strip()
            else:
                name = cell_value.strip()

            if name.lower() not in [
                "appeals and disputes",
                "claim letters",
                "housecalls documentation",
                "overpayment documents",
                "prior auth letters",
            ]:
                practice_names.append(name)

    logger.info(
        f"Found {len(practice_names)} practices in Google Sheet for {section_name}"
    )
    return practice_names


def bulk_update_uhc_file_status(sheet, section_name: str, updates: dict):

    if not sheet:
        logger.info("Google Sheet not available")
        return

    headers = sheet.row_values(1)

    if section_name not in headers:
        raise Exception(f"Column '{section_name}' not found in Google Sheet")

    col_index = headers.index(section_name) + 1
    col_letter = chr(64 + col_index)

    col_values = sheet.col_values(col_index)

    batch_data = []

    for i, cell_value in enumerate(col_values[1:], start=2):  # skip header row

        base_name = cell_value.split(" - ")[0].strip()

        if base_name in updates:

            status = updates[base_name]
            new_value = f"{base_name} - {status}"

            batch_data.append({"range": f"{col_letter}{i}", "values": [[new_value]]})

    if batch_data:

        sheet.batch_update(batch_data)

        logger.info(f"Bulk updated {len(batch_data)} rows")


def batch_update_practice_names(sheet, practice_names: list[str], section_name: str):
    """
    Batch update multiple practice names (names only, NO status).
    """
    if not sheet or not practice_names:
        logger.info(" No sheet or practice names to update")
        return False

    logger.info(f" Batch writing {len(practice_names)} practices into '{section_name}'")

    # Column mapping (adjust if your sheet layout changes)
    col_mapping = {
        "Appeals and Disputes": 1,
        "Claim Letters": 2,
        "HouseCalls Documentation": 3,
        "Overpayment Documents": 4,
        "Prior Auth Letters": 5,
    }

    col = col_mapping.get(section_name)
    if not col:
        raise Exception(f"Column not defined for section: {section_name}")

    start_row = 2  # after header row

    #  gspread expects VALUES FIRST, then RANGE
    values = [[name] for name in practice_names]
    range_name = f"{chr(64 + col)}{start_row}:{chr(64 + col)}{start_row + len(practice_names) - 1}"

    sheet.update(values, range_name)

    logger.info(" Practice names written to Google Sheet (no status)")
    return True


def clear_sheet(sheet):
    """
    Clear only data (keep header row intact)
    """
    try:
        # Get all values
        all_values = sheet.get_all_values()

        if len(all_values) <= 1:
            logger.info("Sheet already empty (only header present)")
            return

        # Number of rows and columns
        num_rows = len(all_values)
        num_cols = len(all_values[0])

        # Create empty data (excluding header)
        empty_data = [["" for _ in range(num_cols)] for _ in range(num_rows - 1)]

        # Clear from row 2 onwards
        range_name = f"A2:{chr(64 + num_cols)}{num_rows}"

        sheet.update(empty_data, range_name)

        logger.info("Sheet data cleared (header preserved)")

    except Exception as e:
        logger.error(f"Error clearing sheet: {e}")


def get_failed_practices(sheet, section_name):
    try:
        col_mapping = {
            "Appeals and Disputes": 1,
            "Claim Letters": 2,
            "HouseCalls Documentation": 3,
            "Overpayment Documents": 4,
            "Prior Auth Letters": 5,
        }

        col = col_mapping.get(section_name)
        column_values = sheet.col_values(col)

        failed_practices = []

        for cell in column_values[1:]:  # skip header
            if "FILE NOT FOUND" in cell:
                # name = cell.split(" - ")[0].strip()
                if " - " in cell:
                    parts = cell.rsplit(" - ", 1)
                    name = parts[0].strip()
                else:
                    name = cell.strip()
                failed_practices.append(name)

        logger.info(f"Total failed practices: {len(failed_practices)}")
        return failed_practices

    except Exception as e:
        logger.error(f"Error reading sheet: {e}")
        return []
