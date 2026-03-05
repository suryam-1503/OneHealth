from playwright.sync_api import sync_playwright
from src.gsheet.gsheet_client import get_uhc_file_sheet
from src.login.onehealth_login import run_login
from src.onehealth_home.open_documents import documents_reporting
from automation.scrape_and_download_workflow_final import process_section



def run_automation(headless=False):
  with sync_playwright() as playwright:
        print("Starting browser...")
        page = run_login(playwright, headless=False)
        print(" Logged in")

        sheet = get_uhc_file_sheet()
        if not sheet:
            print(" Sheet not available (downloads only)")

        documents_reporting(page)
        page.wait_for_timeout(3000)

        process_section(page, "Appeals and Disputes", sheet)
        page.wait_for_timeout(2000)
        process_section(page, "Claim Letters", sheet)
        page.wait_for_timeout(2000)
        process_section(page,"Overpayment Documents",sheet)
        page.wait_for_timeout(2000)
        process_section(page,"Prior Auth Letters",sheet)
        page.wait_for_timeout(2000)

        print("\n✓ Workflow completed successfully")


    



    

        
