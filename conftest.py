import os
import pytest
import warnings

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selene import Browser, Config

from utils import attach


@pytest.fixture(scope='function')
def setup_browser(request):
    """Create a Selene Browser backed by either remote Selenoid or local Chrome.

    Behaviour:
    - If environment variable SELENOID_URL is set (or default), try to connect to remote Selenoid.
    - If remote fails, try to start a local Chrome WebDriver.
    - If no driver can be created, skip the test.

    Attachments are attempted in teardown but errors during attach are ignored to
    avoid masking test results.
    """

    # Load .env if available (optional)
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except Exception:
        # python-dotenv not installed or .env not present — continue with env
        pass

    # Prefer explicit full URL, otherwise build from components
    selenoid_url = os.getenv('SELENOID_URL')
    if not selenoid_url:
        host = os.getenv('SELENOID_HOST')
        user = os.getenv('SELENOID_USER')
        password = os.getenv('SELENOID_PASSWORD')
        port = os.getenv('SELENOID_PORT', '443')
        if host and user and password:
            selenoid_url = f"https://{user}:{password}@{host}:{port}/wd/hub"
        else:
            # fallback default kept for compatibility with older repo state
            selenoid_url = os.getenv('SELENOID_URL', 'https://user1:1234@selenoid.autotests.cloud/wd/hub')
    driver = None
    browser = None

    # Prepare options and capabilities
    options = Options()
    browser_version = os.getenv('BROWSER_VERSION', '100.0')
    try:
        options.set_capability('browserName', 'chrome')
        options.set_capability('browserVersion', browser_version)
        options.set_capability('selenoid:options', {"enableVNC": True, "enableVideo": True})
    except Exception:
        # Some selenium versions may not support set_capability; ignore
        pass

    # Try remote Selenoid first
    if selenoid_url:
        try:
            driver = webdriver.Remote(command_executor=selenoid_url, options=options)
        except WebDriverException as e:
            warnings.warn(f"Cannot start remote webdriver at {selenoid_url}: {e}")
            driver = None

    # Fallback to local Chrome using webdriver-manager (import lazily)
    if driver is None:
        try:
            # Add recommended options for CI/headless if requested
            headless = os.getenv('HEADLESS', 'true').lower() in ('1', 'true', 'yes')
            if headless:
                options.add_argument('--headless=new')
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
            # Ensure window size for headless runs
            options.add_argument('--window-size=1920,1080')

            try:
                # Try webdriver-manager if available
                from webdriver_manager.chrome import ChromeDriverManager  # lazy import
                service = ChromeService(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=options)
            except Exception as e_wdm:
                warnings.warn(f"webdriver-manager not available or failed: {e_wdm}; trying chromedriver from PATH")
                # Try to use chromedriver from PATH
                try:
                    driver = webdriver.Chrome(options=options)
                except WebDriverException as e_path:
                    warnings.warn(f"Cannot start local Chrome webdriver from PATH: {e_path}")
                    driver = None
        except WebDriverException as e:
            warnings.warn(f"Cannot start local Chrome webdriver: {e}")
            driver = None

    if driver is None:
        pytest.skip(
            "No webdriver available (tried remote Selenoid and local Chrome).\n"
            "To run browser tests locally: 1) install requirements: python3 -m pip install -r requirements.txt\n"
            "2) install Google Chrome and ensure `chromedriver` is in PATH, or keep `webdriver-manager` in requirements.\n"
            "Or set SELENOID_URL to a working remote WebDriver (e.g. https://user:pass@selenoid.example/wd/hub)."
        )

    # Wrap driver in Selene browser
    # Create Selene Browser using explicit Config to avoid signature issues
    cfg = Config(driver=driver)
    browser = Browser(cfg)

    try:
        yield browser
    finally:
        # Try to attach artifacts, but never raise from teardown
        if browser is not None:
            try:
                attach.add_screenshot(browser)
            except Exception:
                warnings.warn('Failed to add screenshot')
            try:
                attach.add_logs(browser)
            except Exception:
                warnings.warn('Failed to add logs')
            try:
                attach.add_html(browser)
            except Exception:
                warnings.warn('Failed to add html')
            try:
                attach.add_video(browser)
            except Exception:
                warnings.warn('Failed to add video')

        # Quit driver/browser
        try:
            if browser is not None:
                browser.quit()
            elif driver is not None:
                driver.quit()
        except Exception:
            warnings.warn('Error quitting webdriver')

