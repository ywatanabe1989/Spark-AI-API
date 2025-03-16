#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-03-16 14:51:55 (ywatanabe)"
# File: /home/ywatanabe/proj/spark-ai-api/src/sparkai/ChromeManager.py
# ----------------------------------------
import os
__FILE__ = (
    "/home/ywatanabe/proj/spark-ai-api/src/sparkai/ChromeManager.py"
)
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------

import argparse
import json
import subprocess
import sys
import time
import uuid

import pyperclip
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

try:
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.service import Service

    WEBDRIVER_MANAGER_AVAILABLE = True
except ImportError:
    WEBDRIVER_MANAGER_AVAILABLE = False

from .debug_print import debug_print


class ChromeManager:
    """
    Manages Chrome browser instances for incognito mode sessions.
    Allows for reusing the browser window across multiple operations.
    """

    _instance = None

    @classmethod
    def get_instance(cls):
        """Singleton pattern to get Chrome manager instance"""
        if cls._instance is None:
            cls._instance = ChromeManager()
        return cls._instance

    def __init__(self):
        """Initialize with no active drivers"""
        self.drivers = {}

    def setup_chrome(
        self,
        browser_id=None,
        headless=False,
        remote_debugging=True,
        debugging_port=9222,
        kill_zombie=False,
        force_new=False
    ):
        """
        Set up a Chrome browser instance.
        Parameters
        ----------
        browser_id : str
            Unique identifier for this browser
        headless : bool
            Whether to run Chrome in headless mode
        remote_debugging : bool
            Whether to enable remote debugging
        debugging_port : int
            Port to use for remote debugging
        kill_zombie : bool
            Whether to kill zombie Chrome processes
        force_new : bool
            Whether to force creation of a new window even if one exists
        Returns
        -------
        webdriver.Chrome
            Configured Chrome WebDriver instance
        """
        # Check if we already have a driver for this session
        if browser_id in self.drivers and self.is_driver_alive(
            self.drivers[browser_id]
        ) and not force_new:
            debug_print(f"Reusing existing driver for browser {browser_id}")
            return self.drivers[browser_id]

        # Check if a Chrome browser with remote debugging is already running
        if not force_new and remote_debugging:
            try:
                # Try to attach to existing Chrome with remote debugging
                debug_print(f"Attempting to attach to existing Chrome on port {debugging_port}")
                chrome_options = Options()
                chrome_options.add_experimental_option(
                    "debuggerAddress", f"localhost:{debugging_port}"
                )

                # Create a new driver connected to the existing browser
                try:
                    if WEBDRIVER_MANAGER_AVAILABLE:
                        service = Service(ChromeDriverManager().install())
                        driver = webdriver.Chrome(service=service, options=chrome_options)
                    else:
                        driver = webdriver.Chrome(options=chrome_options)

                    # Test if connection was successful
                    current_url = driver.current_url
                    debug_print(f"Successfully attached to existing Chrome browser at {current_url}")
                    self.drivers[browser_id] = driver
                    return driver
                except Exception as e:
                    debug_print(f"Failed to attach to existing Chrome: {e}")
                    # Continue with creating a new browser
            except Exception as e:
                debug_print(f"Error checking for existing Chrome: {e}")

        debug_print(f"Creating new Chrome driver for browser {browser_id}")

        # Create unique profile directory to avoid conflicts
        path_chrome_config = os.path.join(
            os.path.expanduser("~/.config/google-chrome"),
            f"SparkAI_Test_{uuid.uuid4().hex}"  # Create unique profile for each session
        )
        # Ensure the directory exists
        os.makedirs(path_chrome_config, exist_ok=True)

        chrome_options = Options()

        # Create a fresh Chrome profile without shared user data
        if os.path.exists(path_chrome_config):
            # Use the actual profile directory, not Default subdirectory
            parent_dir = os.path.dirname(path_chrome_config)
            chrome_options.add_argument(f"user-data-dir={parent_dir}")
            # Add profile directory name
            profile_name = os.path.basename(path_chrome_config)
            chrome_options.add_argument(f"--profile-directory={profile_name}")
        else:
            # Create empty directory for Chrome profile
            os.makedirs(path_chrome_config, exist_ok=True)
            chrome_options.add_argument(f"user-data-dir={path_chrome_config}")

        # Basic Chrome options
        # chrome_options.add_argument("--incognito")
        chrome_options.add_experimental_option("detach", True)

        # Essential stability options for Linux/WSL
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")

        # Auto-grant clipboard permissions
        chrome_options.add_experimental_option("prefs", {
            "profile.content_settings.exceptions.clipboard": {
                "[*.],*": {"setting": 1}
            },
            "profile.default_content_setting_values.clipboard": 1,
            "profile.default_content_setting_values.notifications": 1,
            # Disable password saving prompts
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
            # Disable cookie prompts
            "profile.default_content_setting_values.cookies": 1,
            # Keep cookies between sessions
            "profile.exit_type": "Normal",
        })

        # Add remote debugging if requested
        if remote_debugging:
            chrome_options.add_argument(f"--remote-debugging-port={debugging_port}")

        # Add headless mode options if requested
        if headless:
            debug_print(f"Using headless mode")
            # Use the newer headless mode
            chrome_options.add_argument("--headless=new")
            # Set a standard window size
            chrome_options.add_argument("--window-size=1920,1080")
        else:
            # If not headless, still set a reasonable window size
            chrome_options.add_argument("--window-size=1200,800")

        # Remove detection flags
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)

        # Check if we should try using webdriver-manager
        try_webdriver_manager = WEBDRIVER_MANAGER_AVAILABLE

        if kill_zombie:
            # Pre-cleanup: Kill any zombie Chrome processes before starting a new one
            try:
                debug_print("Attempting to kill any zombie Chrome processes...")
                os.system("pkill -f chrome")
                time.sleep(1)  # Give processes time to terminate
            except:
                pass

        # Try to create driver with multiple attempts
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                debug_print(f"Initializing Chrome driver (attempt {attempt+1}/{max_attempts})")
                # Create ChromeDriver, trying different methods
                if try_webdriver_manager and attempt > 0:
                    debug_print("Trying with webdriver_manager...")
                    service = Service(ChromeDriverManager().install())
                    driver = webdriver.Chrome(service=service, options=chrome_options)
                else:
                    driver = webdriver.Chrome(options=chrome_options)

                debug_print(f"Chrome driver initialized successfully")
                # Store the driver
                self.drivers[browser_id] = driver
                return driver
            except Exception as e:
                debug_print(f"Error initializing Chrome driver (attempt {attempt+1}/{max_attempts}): {e}")
                # If we've detected a renderer connection problem, force headless mode
                if "unable to connect to renderer" in str(e) and not headless:
                    debug_print("Renderer connection issue detected, forcing headless mode for next attempt")
                    headless = True
                    chrome_options.add_argument("--headless=new")

                if attempt < max_attempts - 1:
                    debug_print(f"Waiting before retry...")
                    time.sleep(2)  # Wait before retry

                # Clear any zombie Chrome processes that might be causing issues
                try:
                    debug_print("Attempting to kill any zombie Chrome processes...")
                    os.system("pkill -f chrome")
                    time.sleep(1)  # Give processes time to terminate
                except:
                    pass

        # If we reach here, all attempts failed
        raise Exception(f"Failed to initialize Chrome driver after {max_attempts} attempts")

    def is_driver_alive(self, driver):
        """Check if driver is still active"""
        try:
            # Try to get a simple property to check if driver is responsive
            driver.current_url
            return True
        except:
            return False


    def get_driver(
        self,
        browser_id=None,
        headless=False,
        remote_debugging=True,
        debugging_port=9222,
        force_new=False,
    ):
        """
        Get an existing driver or create a new one
        Parameters
        ----------
        browser_id : str
            Unique identifier for browser session
        headless : bool
            Whether to run in headless mode
        remote_debugging : bool
            Whether to enable remote debugging
        debugging_port : int
            Port to use for remote debugging
        force_new : bool
            Whether to force creation of a new window even if one exists
        Returns
        -------
        webdriver.Chrome
            WebDriver instance for the requested browser
        """
        # If browser_id is provided and exists, check if it's still valid
        if browser_id in self.drivers:
            try:
                # Test if driver is still alive
                self.drivers[browser_id].current_url
                debug_print(
                    f"Reusing existing driver for browser {browser_id}"
                )
                return self.drivers[browser_id]
            except Exception as e:
                debug_print(
                    f"Existing driver is invalid, creating new one: {e}"
                )
                # Remove invalid driver
                try:
                    self.drivers[browser_id].quit()
                except:
                    pass
                del self.drivers[browser_id]

        # Create a new driver
        return self.setup_chrome(
            browser_id, headless, remote_debugging, debugging_port, force_new=force_new
        )

    def close_driver(self, browser_id):
        """Close a specific driver"""
        if browser_id in self.drivers:
            try:
                self.drivers[browser_id].quit()
            except:
                pass
            del self.drivers[browser_id]

    def close_all(self):
        """Close all active drivers"""
        for browser_id in list(self.drivers.keys()):
            self.close_driver(browser_id)

    def get_active_browsers(self):
        """
        Returns a list of active browser IDs
        Returns
        -------
        list
            List of browser IDs for active browsers
        """
        return [
            bid
            for bid in self.drivers.keys()
            if self.is_driver_alive(self.drivers[bid])
        ]

    def load_cookies(self, browser_id, cookie_file):
        """
        Load cookies from file to restore session
        Parameters
        ----------
        browser_id : str
            Browser ID for the browser instance
        cookie_file : str
            Path to the cookie file
        Returns
        -------
        bool
            Whether cookies were successfully loaded
        """
        driver = self.get_driver(browser_id)
        if not driver:
            return False
        # First navigate to the domain to set cookies properly
        driver.get("https://spark.unimelb.edu.au")
        time.sleep(1)  # Give the page time to load
        try:
            with open(cookie_file, "r") as f:
                cookies = json.load(f)
            # Add cookies one by one with domain checks
            for cookie in cookies:
                # Ensure cookie has all required fields
                if "domain" in cookie:
                    # Remove problematic attributes that might cause issues
                    if "expiry" in cookie:
                        cookie["expiry"] = int(cookie["expiry"])
                    # Skip sameSite=None cookies in non-secure contexts
                    if (
                        "sameSite" in cookie
                        and cookie["sameSite"] == "None"
                        and not cookie.get("secure", False)
                    ):
                        continue
                    try:
                        # Make sure we're on a page with the right domain before adding cookie
                        domain = cookie["domain"].lstrip(".")
                        if domain in driver.current_url:
                            driver.add_cookie(cookie)
                    except Exception as e:
                       debug_print(f"Couldn't add cookie {cookie.get('name')}: {e}")
            # Refresh page to apply cookies
            driver.refresh()
            return True
        except Exception as e:
            debug_print(f"Error loading cookies: {e}")
            return False

    def save_cookies(self, browser_id, cookie_file):
        """
        Save browser cookies to file for future sessions
        Parameters
        ----------
        browser_id : str
            Browser ID for the browser instance
        cookie_file : str
            Path to save the cookie file
        Returns
        -------
        bool
            Whether cookies were successfully saved
        """
        driver = self.get_driver(browser_id)
        if not driver:
            return False
        # Wait a bit for any authentication to complete
        time.sleep(2)
        try:
            # Get all cookies and save them
            cookies = driver.get_cookies()
            with open(cookie_file, "w") as f:
                json.dump(cookies, f)
            debug_print(f"Saved {len(cookies)} cookies to {cookie_file}")
            return True
        except Exception as e:
            debug_print(f"Error saving cookies: {e}")
            return False

    def navigate_to(self, browser_id, url):
        """
        Navigate the browser to a specified URL
        Parameters
        ----------
        browser_id : str
            Browser ID for the browser instance
        url : str
            URL to navigate to
        Returns
        -------
        bool
            Whether navigation was successful
        """
        driver = self.get_driver(browser_id)
        if not driver:
            return False
        try:
            driver.get(url)
            return True
        except Exception as e:
            debug_print(f"Error navigating to {url}: {e}")
            return False
        # Error navigating to https://spark.unimelb.edu.au/securechat: Message: invalid session id

    def login_to_spark(self, browser_id, username, password, max_wait_sec=30):
        """
        Login to Spark AI using the specified browser
        Parameters
        ----------
        browser_id : str
            Browser identifier for the browser to use
        username : str
            UoM SSO username
        password : str
            UoM SSO password
        max_wait_sec : int
            Maximum wait time in seconds
        Returns
        -------
        bool
            Whether login was successful
        """
        from .auth_utils import login_to_spark as perform_login

        # Get or create a driver for this browser - always use non-headless for login
        debug_print(f"Getting driver for login with headless=False")
        driver = self.get_driver(browser_id)

        # Perform the login
        debug_print(f"Performing login with username={username}")
        success = perform_login(driver, username, password, max_wait_sec)
        debug_print(f"Login result: {success}")
        return success

    def open(
        self,
        browser_id=None,
        headless=False,
        remote_debugging=True,
        debugging_port=9222,
    ):
        """
        Opens a new Chrome browser instance or returns an existing one
        Parameters
        ----------
        browser_id : str, optional
            Identifier for the browser
        headless : bool
            Whether to run in headless mode
        remote_debugging : bool
            Whether to enable remote debugging
        debugging_port : int
            Port to use for remote debugging
        Returns
        -------
        tuple
            (driver, browser_id) - The WebDriver instance and its browser ID
        """
        if browser_id is None:
            browser_id = str(uuid.uuid4())
        driver = self.get_driver(
            browser_id, headless, remote_debugging, debugging_port
        )
        return driver, browser_id

    def close(self, browser_id):
        """
        Releases a Chrome browser instance without destroying it
        Parameters
        ----------
        browser_id : str
            Identifier for the browser to release
        """
        # This method doesn't actually close the browser,
        # just marks it as available for reuse
        pass

    def attach(
        self,
        browser_id=None,
        debugger_address=None,
        max_retries=1,
        retry_delay=1,
    ):
        """
        Attaches to an existing Chrome browser instance using remote debugging
        Parameters
        ----------
        browser_id : str, optional
            Identifier for the browser (if using an internal session)
        debugger_address : str, optional
            Address for remote debugging (e.g., "localhost:9222")
        max_retries : int
            Maximum number of connection attempts
        retry_delay : int
            Delay in seconds between retry attempts
        Returns
        -------
        tuple
            (driver, browser_id) - The WebDriver instance and its browser ID
        """
        # First try to attach to an internal session if browser_id is provided
        if (
            browser_id
            and browser_id in self.drivers
            and self.is_driver_alive(self.drivers[browser_id])
        ):
            return self.drivers[browser_id], browser_id

        # If no valid internal session, try to connect to remote debugging session
        if debugger_address:
            for attempt in range(max_retries):
                try:
                    # Create options for connecting to existing browser
                    chrome_options = Options()
                    chrome_options.add_experimental_option(
                        "debuggerAddress", debugger_address
                    )
                    # Set page load timeout to prevent hanging
                    chrome_options.page_load_strategy = "eager"

                    # Create a new driver connected to the existing browser
                    driver = webdriver.Chrome(options=chrome_options)

                    # Test connection quickly
                    driver.current_url

                    # Generate a new browser ID if not provided
                    if not browser_id:
                        browser_id = str(uuid.uuid4())

                    # Register this driver in our manager
                    self.drivers[browser_id] = driver
                    return driver, browser_id
                except Exception as e:
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)

            # If all retries failed, return error state
            return None, None

        # No debugger address provided
        return None, None

    def launch_chrome_for_debugging(self, port=9222):
        """
        Launch a Chrome browser with remote debugging enabled
        Parameters
        ----------
        port : int
            Port to use for remote debugging
        Returns
        -------
        subprocess.Popen
            Process object for the launched Chrome instance
        """
        chrome_cmd = "google-chrome"
        if sys.platform == "darwin":  # macOS
            chrome_cmd = "/Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome"
        elif sys.platform == "win32":  # Windows
            chrome_cmd = "chrome.exe"
        try:
            process = subprocess.Popen(
                [
                    chrome_cmd,
                    f"--remote-debugging-port={port}",
                    "--no-first-run",
                    "--no-default-browser-check",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            debug_print(f"Chrome launched with remote debugging on port {port}")
            return process
        except Exception as e:
            debug_print(f"Failed to launch Chrome: {e}")
            return None

    def is_logged_in_to_spark(self, browser_id, max_wait_sec=30, auto_login=True):
        """
        Check if the current browser is logged in to SparkAI and wait until login is complete

        Parameters
        ----------
        browser_id : str
            Browser ID for the browser instance
        max_wait_sec : int
            Maximum time to wait for login to complete
        auto_login : bool
            Whether to attempt automatic login if credentials are available

        Returns
        -------
        bool
            Whether user is logged in
        """
        driver = self.get_driver(browser_id)
        if not driver:
            return False

        debug_print(f"Checking if logged in to SparkAI (will wait up to {max_wait_sec} seconds)")
        start_time = time.time()

        try:
            # Try to detect login state immediately - check for prompt box
            try:
                message_box = driver.find_element(By.NAME, "prompt")
                if message_box and message_box.is_displayed():
                    debug_print("Login already complete - message input box found immediately")
                    return True
            except:
                debug_print("Message input box not found immediately, will wait")
                pass

            # Check if we're on a login page
            login_detected = False
            login_form_filled = False

            # Get credentials from environment (support both SPARK_* and SPARKAI_* prefixes)
            username = os.environ.get("SPARKAI_USERNAME") or os.environ.get("SPARK_USERNAME")
            password = os.environ.get("SPARKAI_PASSWORD") or os.environ.get("SPARK_PASSWORD")

            debug_print(f"Auto-login credentials available: {bool(username and password)}")

            # Wait for either the message input box (if logged in) or the login button (if not logged in)
            while time.time() - start_time < max_wait_sec:
                try:
                    # Check for the message input box with a short timeout
                    message_box = WebDriverWait(driver, 1).until(
                        EC.presence_of_element_located((By.NAME, "prompt"))
                    )
                    if message_box and message_box.is_displayed():
                        debug_print("Login successful - message input box found")
                        return True
                except TimeoutException:
                    # Check if we're on a login page
                    current_url = driver.current_url

                    # First check login elements
                    try:
                        # Common login form fields
                        username_fields = driver.find_elements(By.XPATH, "//input[@type='text' or @type='email' or contains(@name, 'user') or contains(@id, 'user')]")
                        password_fields = driver.find_elements(By.XPATH, "//input[@type='password']")
                        login_buttons = driver.find_elements(By.XPATH, "//button[contains(., 'Log') or contains(., 'Sign')]")

                        # If we have login form elements visible, we need to handle login
                        if (username_fields or password_fields) and not login_form_filled:
                            login_detected = True

                            if auto_login and username and password:
                                debug_print("Attempting auto-login with environment credentials")

                                # Find username field and enter credentials
                                if username_fields and username_fields[0].is_displayed():
                                    username_fields[0].clear()
                                    username_fields[0].send_keys(username)
                                    debug_print("Username entered")

                                # Find password field and enter credentials
                                if password_fields and password_fields[0].is_displayed():
                                    password_fields[0].clear()
                                    password_fields[0].send_keys(password)
                                    debug_print("Password entered")

                                # Click login button
                                if login_buttons and login_buttons[0].is_displayed():
                                    login_buttons[0].click()
                                    debug_print("Login button clicked")
                                    login_form_filled = True
                                    time.sleep(2)  # Wait for form submission
                            else:
                                # Manual login needed - print message only once
                                if not login_form_filled:
                                    debug_print("\n" + "="*60)
                                    debug_print("LOGIN REQUIRED: Please log in through the browser window")
                                    debug_print("The script will continue once login is complete")
                                    if not username or not password:
                                        debug_print("\nTIP: Set SPARKAI_USERNAME and SPARKAI_PASSWORD environment variables")
                                        debug_print("for automatic login in future sessions")
                                    debug_print("="*60 + "\n")
                                    login_form_filled = True  # Mark as notified
                    except Exception as e:
                        debug_print(f"Login element check error: {e}")

                    # Log current page info
                    if "login" in current_url.lower() or "auth" in current_url.lower() or "sso" in current_url.lower():
                        debug_print(f"On authentication page: {current_url}")
                        debug_print(f"Current page title: {driver.title}")

                    # Wait a bit before checking again
                    time.sleep(0.5)

            # If we get here, we've timed out waiting for login
            debug_print(f"Timed out after {max_wait_sec} seconds waiting for login status")
            current_url = driver.current_url
            debug_print(f"Final URL: {current_url}")

            # Take a screenshot to diagnose the issue
            try:
                screenshot_path = f"/tmp/spark_login_timeout_{int(time.time())}.png"
                driver.save_screenshot(screenshot_path)
                debug_print(f"Saved screenshot to {screenshot_path}")
            except:
                debug_print("Failed to save debug screenshot")

            # Last chance check - maybe we're on the chat page but the element detection failed
            if "chat" in current_url and "securechat" in current_url:
                debug_print("URL suggests we might be on the chat page - trying HTML check")
                # Check page source for signs of being on chat interface
                page_source = driver.page_source.lower()
                if "textarea" in page_source and ("message" in page_source or "prompt" in page_source):
                    debug_print("Page source suggests we're on the chat interface")
                    return True

            # If login was detected but we're still not logged in, it probably means
            # the user needs to complete the login manually
            if login_detected:
                debug_print("\nLogin incomplete. Please complete the login process in the browser window.")
                debug_print("Or set correct SPARKAI_USERNAME and SPARKAI_PASSWORD environment variables.")
                return False

            return False
        except Exception as e:
            debug_print(f"Error checking login status: {e}")
            return False

    def send_message_to_spark(self, browser_id, message):
        """
        Send a message to SparkAI chat interface

        Parameters
        ----------
        browser_id : str
            Browser ID for the browser instance
        message : str
            Message content to send

        Returns
        -------
        bool
            Whether message was sent successfully
        """
        driver = self.get_driver(browser_id)
        if not driver:
            return False

        # First, ensure we're logged in - use a longer timeout for initial login
        login_timeout = 120  # 2 minutes should be enough for manual login

        # Try auto-login if environment variables are set
        username = os.environ.get("SPARKAI_USERNAME") or os.environ.get("SPARK_USERNAME")
        password = os.environ.get("SPARKAI_PASSWORD") or os.environ.get("SPARK_PASSWORD")

        if username and password:
            from .auth_utils import login_to_spark
            debug_print(f"Attempting auto-login with username={username}")
            login_to_spark(driver, username, password, max_wait_sec=login_timeout)

        if not self.is_logged_in_to_spark(browser_id, max_wait_sec=login_timeout):
            sys.stderr.write("Error: Not logged in to SparkAI. Please authenticate and try again.\n")
            # Display browser ID for easier reuse
            sys.stderr.write(f"Browser ID: {browser_id} - Set SPARKAI_BROWSER_ID={browser_id} to reuse this browser\n")
            return False

        try:
            debug_print("Looking for message input box")
            message_box = WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((By.NAME, "prompt"))
            )
            message_box.clear()

            # Split message into lines
            lines = message.split("\n")

            # Type first line normally
            debug_print(f"Entering message with {len(lines)} lines")
            message_box.send_keys(lines[0])

            # For subsequent lines, use Shift+Enter and then the line content
            for line in lines[1:]:
                # Create action chain for Shift+Enter
                actions = ActionChains(driver)
                actions.key_down(Keys.SHIFT)
                actions.send_keys(Keys.ENTER)
                actions.key_up(Keys.SHIFT)
                actions.send_keys(line)
                actions.perform()

                # Small delay to ensure proper input
                time.sleep(0.1)

            # Click the send button
            debug_print("Clicking send button")
            send_button = WebDriverWait(driver, 2).until(
                EC.element_to_be_clickable((By.ID, "send-button"))
            )
            send_button.click()

            # Wait for message to be sent (loading indicator to disappear)
            try:
                debug_print("Waiting for loading indicator to disappear")
                WebDriverWait(driver, 2).until_not(
                    EC.presence_of_element_located(
                        (By.XPATH, "//div[contains(@class, 'animate-pulse')]")
                    )
                )
            except:
                debug_print("No loading indicator found or timeout")
                pass

            debug_print("Message sent successfully")
            return True
        except Exception as e:
            sys.stderr.write(f"Error sending message: {e}\n")
            return False

    def get_response_from_spark(self, browser_id, timeout_sec=30):
        """
        Get response from SparkAI after sending a message
        Parameters
        ----------
        browser_id : str
            Browser ID for the browser instance
        timeout_sec : int, optional
            Maximum time to wait for response
        Returns
        -------
        str
            Response text
        """
        debug_print("Getting response from Spark")
        driver = self.get_driver(browser_id)
        if not driver:
            return None

        # Check if we're logged in and on the chat page
        if not self.is_logged_in_to_spark(browser_id):
            debug_print("Not logged in when trying to get response")
            return None

        start_time = time.time()

        # Try direct DOM extraction first (most reliable method)
        try:
            # First wait for response to start
            try:
                # Wait for loading animation to appear first
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'animate-pulse')]"))
                )
                debug_print("Loading animation detected")
            except:
                debug_print("No loading animation detected, checking for response directly")

            # Wait for loading animation to disappear
            debug_print("Waiting for loading animations to disappear")
            try:
                WebDriverWait(driver, timeout_sec).until_not(
                    EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'animate-pulse')]"))
                )
                debug_print("Loading animation gone")
            except:
                debug_print("No loading animation found to disappear")

            # Wait a bit for the response to render fully
            time.sleep(2)

            # Try direct extraction of content from response elements first
            try:
                response_elements = driver.find_elements(
                    By.XPATH, "//div[contains(@class, 'chat-message') and not(contains(@class, 'user'))]//div[contains(@class, 'content')]"
                )
                if response_elements and len(response_elements) > 0:
                    response_text = response_elements[-1].text.strip()
                    if response_text:
                        debug_print(f"Got response directly from DOM, length: {len(response_text)}")
                        return response_text
            except Exception as e:
                debug_print(f"Direct DOM extraction failed: {e}")

            # Count existing copy buttons to identify new ones
            try:
                copy_button_xpath = "//button[contains(@class, 'copy-button') or contains(@aria-label, 'Copy') or .//div[contains(@class, 'sr-only') and normalize-space(text())='Copy message']]"
                initial_copy_buttons = driver.find_elements(
                    By.XPATH, copy_button_xpath
                )
                debug_print(f"Found {len(initial_copy_buttons)} initial copy buttons")

                # Look for new copy buttons
                try:
                    copy_buttons = driver.find_elements(
                        By.XPATH, copy_button_xpath
                    )
                    debug_print(f"Found {len(copy_buttons)} copy buttons after response")

                    # Check if we have new copy buttons or if we should use the last one
                    use_button = None
                    if len(copy_buttons) > len(initial_copy_buttons):
                        use_button = copy_buttons[-1]
                    elif len(copy_buttons) > 0:
                        use_button = copy_buttons[-1]  # Use last button even if count didn't change

                    if use_button:
                        debug_print("Clicking copy button to extract response")
                        use_button.click()
                        time.sleep(0.5)  # Give time for clipboard operation

                        # Try to get clipboard content
                        try:
                            clipboard_text = pyperclip.paste()
                            if clipboard_text:
                                debug_print(f"Got clipboard text via pyperclip, length: {len(clipboard_text)}")
                                return clipboard_text
                        except Exception as e:
                            debug_print(f"Pyperclip failed: {e}")

                        # If that failed, try JavaScript method
                        clipboard_text = self.get_clipboard_contents(driver)
                        if clipboard_text:
                            debug_print(f"Got clipboard text via JavaScript, length: {len(clipboard_text)}")
                            return clipboard_text
                except Exception as e:
                    debug_print(f"Error with copy buttons: {e}")

                # If we failed with copy buttons, try direct extraction one more time
                try:
                    # Extract directly from DOM using JavaScript
                    response_text = driver.execute_script("""
                        const messages = document.querySelectorAll('div.chat-message:not(.user) div.content');
                        if (messages && messages.length > 0) {
                            return messages[messages.length - 1].innerText;
                        }
                        return '';
                    """)

                    if response_text:
                        debug_print(f"Got response via JavaScript extraction, length: {len(response_text)}")
                        return response_text
                except Exception as e:
                    debug_print(f"JavaScript extraction failed: {e}")
            except Exception as e:
                debug_print(f"Copy button method failed: {e}")

            # Last resort - try to get any text from non-user messages
            try:
                all_messages = driver.find_elements(
                    By.XPATH, "//div[contains(@class, 'chat-message') and not(contains(@class, 'user'))]"
                )
                if all_messages and len(all_messages) > 0:
                    last_message = all_messages[-1].text.strip()
                    if last_message:
                        debug_print(f"Got text from general message element, length: {len(last_message)}")
                        return last_message
            except Exception as e:
                debug_print(f"Last resort extraction failed: {e}")
        except Exception as e:
            debug_print(f"Error in get_response_from_spark: {e}")

        # If we reach here, we couldn't get a response
        debug_print("Failed to get response through any method")
        return "Could not retrieve response from Spark. Please check the browser window directly."

    # def get_response_from_spark(self, browser_id, timeout_sec=30):
    #     """
    #     Get response from SparkAI after sending a message

    #     Parameters
    #     ----------
    #     browser_id : str
    #         Browser ID for the browser instance
    #     timeout_sec : int, optional
    #         Maximum time to wait for response

    #     Returns
    #     -------
    #     str
    #         Response text
    #     """
    #     debug_print("Getting response from Spark")
    #     driver = self.get_driver(browser_id)
    #     if not driver:
    #         return None

    #     # Check if we're logged in and on the chat page
    #     if not self.is_logged_in_to_spark(browser_id):
    #         return None

    #     start_time = time.time()

    #     # Count existing copy buttons to identify new ones
    #     try:
    #         copy_button_xpath = "//button[contains(@class, 'copy-button') or contains(@aria-label, 'Copy') or .//div[contains(@class, 'sr-only') and normalize-space(text())='Copy message']]"
    #         initial_copy_buttons = driver.find_elements(
    #             By.XPATH, copy_button_xpath
    #         )
    #         debug_print(f"Found {len(initial_copy_buttons)} initial copy buttons")
    #     except:
    #         initial_copy_buttons = []
    #         debug_print("Failed to find initial copy buttons")

    #     # Wait for new copy button to appear (indicates response is complete)
    #     debug_print("Waiting for new copy button to appear")

    #     # First wait for response to start
    #     try:
    #         # Wait for loading animation to appear first
    #         WebDriverWait(driver, 5).until(
    #             EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'animate-pulse')]"))
    #         )
    #         debug_print("Loading animation detected")
    #     except:
    #         debug_print("No loading animation detected, checking for response directly")

    #     # Wait for loading animation to disappear
    #     debug_print("Waiting for loading animations to disappear")
    #     try:
    #         WebDriverWait(driver, timeout_sec).until_not(
    #             EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'animate-pulse')]"))
    #         )
    #         debug_print("Loading animation gone")
    #     except:
    #         debug_print("No loading animation found to disappear")

    #     # Wait a bit for the response to render fully
    #     time.sleep(2)

    #     # Try to find new copy buttons compared to initial state
    #     try:
    #         copy_buttons = driver.find_elements(
    #             By.XPATH, copy_button_xpath
    #         )
    #         debug_print(f"Found {len(copy_buttons)} copy buttons after response")

    #         # Check if we have new copy buttons
    #         if len(copy_buttons) > len(initial_copy_buttons):
    #             # Click the last (newest) copy button
    #             new_button = copy_buttons[-1]
    #             debug_print("Clicking copy button to extract response")
    #             new_button.click()
    #             time.sleep(0.5)  # Give time for clipboard operation

    #             # Try to get clipboard content
    #             clipboard_text = self.get_clipboard_contents(driver)
    #             if clipboard_text:
    #                 debug_print(f"Got clipboard text via JavaScript, length: {len(clipboard_text)}")
    #                 return clipboard_text

    #             # If JavaScript method failed, try system clipboard
    #             try:
    #                 clipboard_text = pyperclip.paste()
    #                 if clipboard_text:
    #                     debug_print(f"Got clipboard text via pyperclip, length: {len(clipboard_text)}")
    #                     return clipboard_text
    #             except Exception as e:
    #                 debug_print(f"Pyperclip failed: {e}")
    #     except Exception as e:
    #         debug_print(f"Error with copy button method: {e}")

    # def get_clipboard_contents(self, driver):
    #     """
    #     Retrieve SparkAI's response via clipboard copy button.

    #     Parameters
    #     ----------
    #     driver : webdriver.Chrome
    #         Chrome WebDriver instance

    #     Returns
    #     -------
    #     str
    #         The text obtained from the system clipboard.
    #     """
    #     try:
    #         # Support both driver as parameter and self.driver
    #         self.driver = driver  # Set instance driver for internal methods
    #         self.browser_id = None  # Initialize browser_id for compatibility

    #         # For browsers we're tracking, identify the browser_id
    #         for bid, drv in self.drivers.items():
    #             if drv == driver:
    #                 self.browser_id = bid
    #                 break

    #         # Get original number of copy buttons
    #         orig_count = self._count_n_copy_buttons()

    #         # Wait for response to complete and new copy button to appear
    #         self._monitor_n_copy_buttons(orig_count)

    #         # Wait for any loading animations to disappear
    #         try:
    #             WebDriverWait(driver, 64).until_not(
    #                 EC.presence_of_element_located(
    #                     (By.XPATH, "//div[contains(@class, 'animate-pulse')]")
    #                 )
    #             )
    #         except:
    #             # No loading animation found, continue
    #             pass

    #         # Small delay to ensure response is fully loaded
    #         time.sleep(0.5)

    #         # Find all copy buttons and click the last one (most recent response)
    #         copy_button_xpath = "//button[.//div[contains(@class, 'sr-only') and normalize-space(text())='Copy message']]"
    #         new_buttons = driver.find_elements(
    #             By.XPATH, copy_button_xpath
    #         )
    #         new_button = new_buttons[-1]

    #         # For other platforms, try pyperclip first
    #         try:
    #             # Clear clipboard before clicking the copy button
    #             pyperclip.copy("")
    #             # Click the copy button
    #             new_button.click()
    #             # Give time for the clipboard operation to complete
    #             time.sleep(0.5)
    #             # Use pyperclip to get clipboard contents
    #             clipboard_text = pyperclip.paste()
    #             if not clipboard_text:
    #                 clipboard_text = self._get_clipboard_contents()
    #         except Exception:
    #             # Fallback to JavaScript method
    #             new_button.click()
    #             time.sleep(0.5)
    #             clipboard_text = self._get_clipboard_contents()

    #         return clipboard_text
    #     except Exception as e:
    #         sys.stderr.write(f"Error getting response: {e}\n")
    #         driver.save_screenshot("clipboard_error.png")
    #         return f"Error retrieving response: {str(e)}"

    # def _count_n_copy_buttons(self):
    #     """
    #     Count the number of copy buttons present on the page.

    #     Returns
    #     -------
    #     int
    #         The count of copy buttons.
    #     """
    #     copy_button_xpath = "//button[.//div[contains(@class, 'sr-only') and normalize-space(text())='Copy message']]"
    #     # Support both self.driver and driver as parameter from get_clipboard_contents
    #     driver = getattr(self, 'driver', None)
    #     if not driver:
    #         # Try to find the driver from browser_id
    #         if hasattr(self, 'browser_id') and self.browser_id in self.drivers:
    #             driver = self.drivers[self.browser_id]

    #     if not driver:
    #         return 0

    #     return len(driver.find_elements(By.XPATH, copy_button_xpath))

    # def _monitor_n_copy_buttons(self, orig_count):
    #     """
    #     Wait until the number of copy buttons increases from the original count.

    #     Parameters
    #     ----------
    #     orig_count : int
    #         The initial number of copy buttons.

    #     Returns
    #     -------
    #     int
    #         The new count of copy buttons.
    #     """
    #     copy_button_xpath = "//button[.//div[contains(@class, 'sr-only') and normalize-space(text())='Copy message']]"
    #     # Support both self.driver and driver as parameter from get_clipboard_contents
    #     driver = getattr(self, 'driver', None)
    #     if not driver:
    #         # Try to find the driver from browser_id
    #         if hasattr(self, 'browser_id') and self.browser_id in self.drivers:
    #             driver = self.drivers[self.browser_id]

    #     if not driver:
    #         return orig_count

    #     WebDriverWait(driver, 32).until(
    #         lambda d: len(d.find_elements(By.XPATH, copy_button_xpath))
    #         > orig_count
    #     )
    #     return len(driver.find_elements(By.XPATH, copy_button_xpath))

    # def _get_clipboard_contents(self):
    #     """
    #     Retrieve text from the clipboard using the browser's asynchronous script.

    #     Returns
    #     -------
    #     str
    #         The text content from the clipboard.
    #     """
    #     try:
    #         # Support both self.driver and driver as parameter from get_clipboard_contents
    #         driver = getattr(self, 'driver', None)
    #         if not driver:
    #             # Try to find the driver from browser_id
    #             if hasattr(self, 'browser_id') and self.browser_id in self.drivers:
    #                 driver = self.drivers[self.browser_id]

    #         if not driver:
    #             return ""

    #         return driver.execute_async_script(
    #             """
    #             var callback = arguments[arguments.length - 1];
    #             navigator.clipboard.readText().then(text => callback(text)).catch(err => callback(''));
    #             """
    #         )
    #     except Exception as e:
    #         sys.stderr.write(f"Error reading clipboard: {e}\n")
    #         return ""

    def release_driver(self, browser_id):
        """
        Mark the driver as available without closing it.

        Parameters
        ----------
        browser_id : str
            Identifier for the browser instance
        """
        if browser_id in self.drivers:
            debug_print(
                f"Marking browser {browser_id} as available without closing"
            )
            # We don't need to do anything else as the driver will remain in the dict
            # and be reused on the next request
            return True

        return False


def main():
    """Main function to execute when run as a script"""
    parser = argparse.ArgumentParser(description="Chrome Manager Tool")
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open a new Chrome browser window",
    )
    parser.add_argument(
        "--attach",
        action="store_true",
        help="Attach to an existing Chrome browser window",
    )
    parser.add_argument(
        "--launch",
        action="store_true",
        help="Launch Chrome browser with remote debugging enabled",
    )
    parser.add_argument(
        "--browser-id",
        type=str,
        default=None,
        help="Browser ID for browser reuse",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run Chrome in headless mode",
    )
    parser.add_argument(
        "--url",
        type=str,
        default="https://spark.unimelb.edu.au/securechat",
        help="URL to open in the browser",
    )
    parser.add_argument(
        "--debugger-address",
        type=str,
        default="localhost:9222",
        help="Address for remote debugging (e.g., 'localhost:9222')",
    )
    parser.add_argument(
        "--debugging-port",
        type=int,
        default=9222,
        help="Port to use for remote debugging",
    )
    parser.add_argument(
        "--send-message",
        type=str,
        help="Send a message to SparkAI if already on the chat page",
    )
    parser.add_argument(
        "--get-response",
        action="store_true",
        help="Get the response after sending a message",
    )
    parser.add_argument(
        "--list-browsers",
        action="store_true",
        help="List all active browsers",
    )

    args = parser.parse_args()
    manager = ChromeManager.get_instance()

    if args.list_browsers:
        active_browsers = manager.get_active_browsers()
        if active_browsers:
            debug_print("Active browsers:")
            for bid in active_browsers:
                debug_print(f"  {bid}")
        else:
            debug_print("No active browsers found")
        return None

    if args.launch:
        chrome_process = manager.launch_chrome_for_debugging(
            args.debugging_port
        )
        if chrome_process:
            debug_print(
                f"Chrome launched for debugging. Use --attach --debugger-address={args.debugger_address} to connect."
            )
            debug_print("Press Ctrl+C to terminate Chrome...")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                chrome_process.terminate()
                debug_print("\nChrome browser terminated.")
            return None
    if args.attach:
        driver, browser_id = manager.attach(
            args.browser_id, args.debugger_address
        )
        if driver:
            debug_print(
                f"Successfully attached to browser with browser ID: {browser_id}"
            )
            if args.url:
                manager.navigate_to(browser_id, args.url)
                debug_print(f"Browser navigated to: {args.url}")
            if args.send_message:
                debug_print("Sending message to SparkAI...")
                if manager.send_message_to_spark(
                    browser_id, args.send_message
                ):
                    debug_print("Message sent successfully")
                    if args.get_response:
                        debug_print("Waiting for response...")
                        response = manager.get_response_from_spark(browser_id)
                        debug_print("\nResponse from SparkAI:")
                        debug_print("------------------------")
                        debug_print(response)
                        debug_print("------------------------")
                else:
                    debug_print("Failed to send message")
            debug_print("Press Ctrl+C to exit but keep the browser window open...")
            try:
                # Keep the script running until keyboard interrupt
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                debug_print("\nExiting without closing browser window.")
                manager.close(browser_id)
            return browser_id
        else:
            debug_print(f"Failed to attach to Chrome browser.")
            debug_print(
                "Hint: To attach to an existing Chrome browser, launch Chrome with:"
            )
            debug_print(f"  python {os.path.basename(__file__)} --launch")
            debug_print(
                f"  or run: google-chrome --remote-debugging-port={args.debugging_port}"
            )
            debug_print(
                f"Then use: python {os.path.basename(__file__)} --attach --debugger-address={args.debugger_address}"
            )
            return None
    elif args.open:
        driver, browser_id = manager.open(
            args.browser_id,
            args.headless,
            remote_debugging=True,
            debugging_port=args.debugging_port,
        )
        manager.navigate_to(browser_id, args.url)
        debug_print(f"Chrome browser opened with browser ID: {browser_id}")
        debug_print(f"Browser navigated to: {args.url}")
        debug_print(f"Remote debugging enabled on port: {args.debugging_port}")
        if args.send_message:
            debug_print("Sending message to SparkAI...")
            if manager.send_message_to_spark(browser_id, args.send_message):
                debug_print("Message sent successfully")
                if args.get_response:
                    debug_print("Waiting for response...")
                    response = manager.get_response_from_spark(browser_id)
                    debug_print("\nResponse from SparkAI:")
                    debug_print("------------------------")
                    debug_print(response)
                    debug_print("------------------------")
            else:
                debug_print("Failed to send message")
        debug_print("Press Ctrl+C to exit but keep the browser window open...")
        try:
            # Keep the script running until keyboard interrupt
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            debug_print("\nExiting without closing browser window.")
            manager.close(browser_id)
        return browser_id
    else:
        debug_print("No action specified. Available actions:")
        debug_print("  --list-browsers: List all active browsers")
        debug_print("  --launch: Launch Chrome with remote debugging enabled")
        debug_print("  --open: Open a new Chrome browser window with automation")
        debug_print("  --attach: Attach to an existing Chrome browser window")
        debug_print(f"Example: python {os.path.basename(__file__)} --open")
        return None


if __name__ == "__main__":
    main()

# EOF