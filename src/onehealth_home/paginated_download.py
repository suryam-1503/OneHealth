from datetime import datetime
from pathlib import Path
from playwright.sync_api import Page, expect
from src.utils.logger import setup_logger
import time

logger = setup_logger(__name__)

try:
    from OneHealth.src.automation.app import check_stop_flag
except ImportError:

    def check_stop_flag():
        return False


def get_status_column_index(page: Page) -> int:
    try:
        headers = page.locator("div[role='columnheader']")

        for i in range(headers.count()):
            text = headers.nth(i).inner_text().strip().lower()

            if "status" in text:
                logger.info(f"Status column found at index: {i}")
                return i

        logger.error("Status column not found")
        return -1

    except Exception as e:
        logger.error(f"Error finding status column: {e}")
        return -1


# def download_files_with_pagination(page: Page, practice_name: str, section_name: str) -> bool:

#     logger.info(f"Starting paginated download for {practice_name}")

#     try:
#         # Wait for document table to load
#         page.wait_for_selector("tbody tr", timeout=30000)

#         page_count = 1

#         while True:
#             if check_stop_flag():
#                 logger.info("Automation stopped by user request")
#                 return False

#             logger.info(f"Processing page {page_count}")

#             # IMPROVED CHECKBOX DETECTION WITH RETRY LOGIC
#             checkbox = None
#             max_checkbox_retries = 3
#             checkbox_retry_delay = 2000

#             for retry in range(max_checkbox_retries):
#                 try:
#                     # Try multiple possible checkbox selectors
#                     checkbox_selectors = [
#                         "input.abyss-data-table-selection[type='checkbox']",
#                         "input[type='checkbox'][class*='selection']",
#                         "input[type='checkbox']",
#                         "tbody tr:first-child input[type='checkbox']"
#                     ]

#                     for selector in checkbox_selectors:
#                         checkbox = page.locator(selector).first
#                         if checkbox.count() > 0:
#                             expect(checkbox).to_be_visible(timeout=5000)
#                             break

#                     if checkbox and checkbox.count() > 0:
#                         break

#                 except Exception as e:
#                     logger.warning(f"Checkbox detection attempt {retry + 1} failed: {e}")
#                     if retry < max_checkbox_retries - 1:
#                         page.wait_for_timeout(checkbox_retry_delay)
#                     else:
#                         logger.error("Failed to find checkbox after multiple attempts")
#                         return False

#             if not checkbox or checkbox.count() == 0:
#                 logger.error("No checkbox found on page")
#                 return False

#             # Ensure checkbox is checked
#             if not checkbox.is_checked():
#                 checkbox.click()
#                 page.wait_for_timeout(1000)

#             logger.info("All files selected")

#             # BULK ACTIONS
#             bulk_actions = page.locator("[data-testid*='bulk-actions-dropdown']").first

#             try:
#                 expect(bulk_actions).to_be_visible(timeout=15000)
#                 bulk_actions.click()
#                 page.wait_for_timeout(1500)
#             except Exception as e:
#                 logger.error(f"Bulk actions button not found: {e}")
#                 return False

#             # DOWNLOAD BUTTON
#             download_item = page.locator("div[role='menuitem']:has-text('Download')").first

#             try:
#                 expect(download_item).to_be_visible(timeout=15000)
#                 logger.info("Starting bulk download...")
#                 download_item.click()
#             except Exception as e:
#                 logger.error(f"Download button not found: {e}")
#                 return False

#             downloads = []

#             try:
#                 # FIRST DOWNLOAD
#                 first_download = page.wait_for_event("download", timeout=30000)
#                 downloads.append(first_download)
#                 logger.info("First download detected")

#                 # ESTIMATE DOWNLOAD TIMEOUT BASED ON EXPECTED FILE COUNT
#                 # Wait longer for pages with many files
#                 estimated_files = 50  # Conservative estimate for large pages
#                 base_timeout = 20  # Base timeout in seconds
#                 estimated_timeout = min(base_timeout + (estimated_files * 0.5), 60)  # Max 60 seconds

#                 logger.info(f"Waiting up to {estimated_timeout} seconds for additional downloads")

#                 start_time = time.time()

#                 # CAPTURE ADDITIONAL DOWNLOADS WITH EXTENDED TIMEOUT
#                 while time.time() - start_time < estimated_timeout:
#                     try:
#                         download = page.wait_for_event("download", timeout=3000)  # Reduced individual timeout
#                         downloads.append(download)
#                         logger.info(f"Additional download detected ({len(downloads)})")

#                         # If we've downloaded a lot of files, extend timeout slightly
#                         if len(downloads) >= 20:
#                             estimated_timeout = min(estimated_timeout + 5, 90)  # Max 90 seconds total
#                             logger.info(f"Extended timeout to {estimated_timeout} seconds due to high file count")

#                     except:
#                         # No more downloads within timeout window
#                         break

#                 # VERIFY WE ACTUALLY DOWNLOADED FILES
#                 if len(downloads) == 0:
#                     logger.warning("No downloads detected")
#                     return False

#                 logger.info(f"Total downloads captured: {len(downloads)}")

#             except Exception as e:
#                 logger.error(f"Download capture error: {e}")
#                 return False

#             # SAVE ALL DOWNLOADS
#             for i, download in enumerate(downloads):
#                 save_download(download, practice_name, section_name, i)

#             logger.info(f"{len(downloads)} files downloaded from page {page_count}")

#             # CHECK NEXT PAGE
#             next_btn = page.locator("button[aria-label='next page']").first

#             if next_btn.get_attribute("aria-disabled") == "true":
#                 logger.info("Reached last page")
#                 break

#             logger.info("Moving to next page")

#             next_btn.click()

#             # IMPROVED PAGE NAVIGATION WAIT
#             try:
#                 page.wait_for_selector("tbody tr", timeout=25000)
#                 page.wait_for_timeout(3000)  # Increased wait time for page stabilization
#             except Exception as e:
#                 logger.error(f"Page navigation failed: {e}")
#                 return False

#             page_count += 1

#         return True

#     except Exception as e:
#         logger.error(f"Pagination download failed: {e}")
#         return False


# def save_download(download, practice_name: str, section_name: str, file_index: int = 0) -> bool:
#     try:
#         safe_name = "".join(c if c not in r'<>:"/\\|?*' else "_" for c in practice_name)

#         today = datetime.today()
#         year_folder = today.strftime("%Y")
#         date_folder = today.strftime("%m %d %Y")

#         base = (
#             Path(
#                 r"G:\Shared drives\Reimbursement and Inventory Analysis\UHC Vault\Completed"
#             )
#             / year_folder
#             / date_folder
#             / safe_name
#             / section_name
#         )

#         base.mkdir(parents=True, exist_ok=True)

#         original_filename = download.suggested_filename

#         name_parts = original_filename.rsplit(".", 1)

#         if len(name_parts) == 2:
#             file_without_ext, file_extension = name_parts
#         else:
#             file_without_ext = original_filename
#             file_extension = ""

#         if file_index > 0:
#             filename = f"{practice_name} - {file_without_ext}_{file_index}.{file_extension}"
#         else:
#             filename = f"{practice_name} - {file_without_ext}.{file_extension}"

#         file_path = base / filename

#         download.save_as(str(file_path))

#         logger.info(f"{practice_name} file downloaded: {file_path}")

#         return True

#     except Exception as e:
#         logger.error(f"Save failed: {e}")
#         return False
