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

    # Fallback to local Chrome using webdriver-manager
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

            service = ChromeService(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
        except WebDriverException as e:
            warnings.warn(f"Cannot start local Chrome webdriver: {e}")
            driver = None

    if driver is None:
        pytest.skip(
            "No webdriver available (tried remote Selenoid and local Chrome)."
            " Set SELENOID_URL or ensure chromedriver is installed to run browser tests."
        )

    # Wrap driver in Selene browser
    try:
        browser = Browser(Config(driver=driver))
    except Exception:
        # If that fails, try older signature
        browser = Browser(Config(driver))

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

