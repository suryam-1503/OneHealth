from playwright.sync_api import Page, expect, TimeoutError
from src.utils.env_data import EnvData
import tkinter as tk
from src.utils.logger import setup_logger


logger = setup_logger(__name__)


def hold_for_manual_otp():
    root = tk.Tk()
    root.title("OTP Required")
    root.geometry("420x140")

    label = tk.Label(
        root,
        text=(
            " OTP REQUIRED\n\n"
            "1. Enter OTP in browser\n"
            "2. Click Continue\n"
            "3. Close this window"
        ),
        font=("Arial", 11),
        justify="center",
    )
    label.pack(expand=True, padx=20, pady=20)

    root.mainloop()


def close_ad_if_present(page: Page, timeout: int = 5000):
    try:
        close_icon = page.locator("i.material-icons", has_text="close").first
        close_icon.wait_for(state="visible", timeout=timeout)
        close_icon.click()
        logger.info(" Ad popup closed")
    except TimeoutError:

        pass


def run_login(playwright, headless=False):

    browser = playwright.chromium.launch(
        headless=headless,
        args=[
            "--disable-notifications",
            "--disable-popup-blocking",
            "--disable-automation",
            "--no-sandbox",
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--disable-dev-shm-usage",
        ],
    )

    context = browser.new_context()
    page = context.new_page()

    logger.info("Opening site...")

    # Retry loading site
    for attempt in range(5):
        try:
            page.goto(EnvData.BASE_URL, wait_until="domcontentloaded", timeout=120_000)

            if page.locator("text=This site can’t be reached").is_visible(timeout=3000):
                raise Exception("Site not reachable")

            logger.info("Site loaded successfully")
            break

        except Exception as e:
            logger.info(f"Network issue: {e}")
            logger.info("Refreshing page...")
            page.reload()
            page.wait_for_timeout(5000)

    page.wait_for_timeout(2000)

    close_ad_if_present(page)

    # ───── SIGN IN ─────
    sign_in = page.locator("#signin-btn-wrapper-tt a")
    expect(sign_in).to_be_visible(timeout=30000)

    with page.expect_navigation(wait_until="domcontentloaded"):
        sign_in.click()

    page.wait_for_timeout(3000)

    username = EnvData.ONEHEALTH_USERNAME.strip()
    password = EnvData.ONEHEALTH_PASSWORD.strip()

    page.locator("#username").fill(username)
    page.wait_for_timeout(3000)

    page.locator("#btnLogin").click()

    password_input = page.locator("input[type='password']")
    password_input.type(password)

    with page.expect_navigation(wait_until="domcontentloaded", timeout=30000):
        page.locator("#btnLogin").click()

    # ───── OTP OR HOME DETECTION ─────
    logger.info("Waiting for OTP or Home page...")

    otp_button = page.locator("#textMsg")
    home_indicator = page.locator("[data-testid='documents-and-reporting-link']")

    try:
        page.wait_for_function(
            """
            () =>
              document.querySelector('#textMsg') ||
              document.querySelector('[data-testid="documents-and-reporting-link"]')
            """,
            timeout=20000,
        )

        if otp_button.is_visible():
            logger.info("OTP REQUIRED")

            otp_button.click()
            logger.info("Enter OTP manually in browser")

            hold_for_manual_otp()

            expect(home_indicator).to_be_visible(timeout=30000)
            logger.info("Login successful (after OTP)")

        else:
            expect(home_indicator).to_be_visible(timeout=30000)
            logger.info("Login successful (no OTP)")

    except TimeoutError:
        page.pause()
        raise RuntimeError("Login failed: neither OTP nor Home detected")

    return page
