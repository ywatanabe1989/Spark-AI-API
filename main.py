#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-03-16 01:53:52 (ywatanabe)"
# File: /home/ywatanabe/proj/spark-ai-api/main.py
# ----------------------------------------
import os
__FILE__ = (
    "/home/ywatanabe/proj/spark-ai-api/main.py"
)
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------

"""
Functionality:
    Provides an interface to interact with SparkAI via a Selenium-driven web browser.
Input:
    None directly; configuration is provided as parameters.
Output:
    Web-based interactions with SparkAI.
Prerequisites:
    Selenium, a valid Chrome installation, and proper Chrome user data configuration.
"""
import sys
import time
import json
import argparse
import pyperclip
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    StaleElementReferenceException,
    TimeoutException,
)
import tempfile
import subprocess
import platform
import subprocess
import platform
import socket
import tempfile


class SparkAI:
    """
    Class SparkAI provides an interface to interact with SparkAI using Selenium.
    Methods
    -------
    __init__(...)
        Initialize the SparkAI instance.
    send_message(message)
        Send a message and return the AI response.
    _send_message(message)
        Send a message using the web interface.
    _get_llm_response_from_copy_button()
        Retrieve the SparkAI response via clipboard.
    _count_n_copy_buttons()
        Count the current copy buttons on the page.
    _monitor_n_copy_buttons(orig_count)
        Wait for new copy button appearance.
    _get_clipboard_contents()
        Get the clipboard text content.
    close()
        Close the browser session.
    """

    def __init__(
        self,
        thread_id=None,
        path_chrome_config=None,
        max_wait_sec=30,
        auto_login=False,
        username=None,
        password=None,
        cookie_file=None,
        headless=True,
        persistent_profile=True,
    ):
        """
        Initialize SparkAI instance and launch the Chrome browser.
        Parameters
        ----------
        thread_id : optional
            The thread identifier for the SparkAI session.
        path_chrome_config : str
            The path to Chrome's user data directory.
        max_wait_sec : int
            Maximum seconds to wait for page elements.
        auto_login : bool
            Whether to attempt automatic login.
        username : str
            UoM SSO username for auto-login.
        password : str
            UoM SSO password for auto-login.
        cookie_file : str
            Path to save/load session cookies.
        headless : bool
            Run Chrome in headless mode without visible window.
        persistent_profile : bool
            Whether to keep the Chrome profile between sessions.
        """
        self.path_chrome_config = (
            path_chrome_config  # Store as instance variable first
        )
        self.persistent_profile = persistent_profile

        # Create directory for Chrome profile if it doesn't exist and we want persistence
        if (
            persistent_profile
            and path_chrome_config
            and not os.path.exists(path_chrome_config)
        ):
            os.makedirs(path_chrome_config, exist_ok=True)

        self.driver = self._setup_chrome(
            self.path_chrome_config, headless
        )  # Pass headless parameter too
        self.max_wait_sec = max_wait_sec

        # Load cookies if available
        if cookie_file and os.path.exists(cookie_file):
            self._load_cookies(cookie_file)

        # Navigate to SparkAI
        url = self._determine_sparkai_url(thread_id)

        # Check if already logged in before attempting login
        try:
            # Use a short timeout to check if already logged in
            WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.NAME, "prompt"))
            )
            # print("[DEBUG] Already logged in, skipping authentication.")
        except TimeoutException:
            # Not logged in, handle login
            if auto_login and username and password:
                self._auto_login(username, password)
            else:
                input(
                    "Please login to SparkAI in the browser, then press Enter to continue..."
                )

        # Save cookies after successful login
        if cookie_file:
            self._save_cookies(cookie_file)

    @staticmethod
    def _setup_chrome(path_chrome_config, headless=True):
        """Chrome settings"""
        if not path_chrome_config:
            if os.name == "nt":
                path_chrome_config = rf"C:\Users\{os.getlogin()}\AppData\Local\Google\Chrome\User Data\Default"
            else:
                path_chrome_config = os.path.expanduser(
                    "~/.config/google-chrome/Default"
                )

        chrome_options = Options()

        # Create a fresh Chrome profile without shared user data
        if os.path.exists(path_chrome_config):
            # Use the actual profile directory, not Default subdirectory
            parent_dir = os.path.dirname(path_chrome_config)
            chrome_options.add_argument(
                f"user-data-dir={parent_dir}"
            )
            # Add profile directory name
            profile_name = os.path.basename(path_chrome_config)
            chrome_options.add_argument(f"--profile-directory={profile_name}")

        else:
            # Create empty directory for Chrome profile
            os.makedirs(path_chrome_config, exist_ok=True)
            chrome_options.add_argument(f"user-data-dir={path_chrome_config}")

        # Other Chrome options
        chrome_options.add_argument(
            "--enable-features=ClipboardContentSetting"
        )
        chrome_options.add_argument("--window-size=1920,1080")

        # Add headless mode options
        if headless:
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")

        # Allow clipboard access
        chrome_options.add_experimental_option(
            "prefs",
            {
                "profile.content_settings.exceptions.clipboard": {
                    "[*.]*": {"setting": 1}  # 1 = Allow
                },
                # Disable password saving prompts
                "credentials_enable_service": False,
                "profile.password_manager_enabled": False,
                # Disable cookie prompts
                "profile.default_content_setting_values.cookies": 1,
                # Keep cookies between sessions
                "profile.exit_type": "Normal"
            },
        )

        driver = webdriver.Chrome(options=chrome_options)
        return driver

    def _auto_login(self, username, password):
        """
        Attempt automatic login to SparkAI using provided credentials.
        Parameters
        ----------
        username : str
            UoM SSO username.
        password : str
            UoM SSO password.
        Returns
        -------
        bool
            Whether login was successful.
        """
        try:
            # Check if we're already on the messaging page
            try:
                # Use a shorter timeout just for checking if already logged in
                WebDriverWait(self.driver, 2).until(
                    EC.presence_of_element_located((By.NAME, "prompt"))
                )
                # print("[DEBUG] Already logged in.")
                return True
            except TimeoutException:
                pass

            # Wait for login form - username field
            username_field = WebDriverWait(self.driver, 2).until(
                EC.presence_of_element_located((By.NAME, "identifier"))
            )
            username_field.clear()
            username_field.send_keys(username)
            time.sleep(0.5)

            # Click the Next button
            next_button = WebDriverWait(self.driver, 2).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "input.button-primary[value='Next']")
                )
            )
            next_button.click()

            # Wait for password field to appear
            password_field = WebDriverWait(self.driver, 4).until(
                EC.presence_of_element_located(
                    (By.NAME, "credentials.passcode")
                )
            )
            password_field.clear()
            password_field.send_keys(password)

            # Click verify button
            verify_button = WebDriverWait(self.driver, 2).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "input[type='submit'][value='Verify']")
                )
            )
            verify_button.click()

            # Handle authentication methods if they appear
            self._handle_duo_authentication()

            # Wait for chat interface to load
            WebDriverWait(self.driver, 32).until(
                EC.presence_of_element_located((By.NAME, "prompt"))
            )
            # print("[DEBUG] Login successful.")
            return True
        except Exception as e:
            print(f"Login failed: {e}")
            input("Please login manually, then press Enter to continue...")
            return False

    def _handle_duo_authentication(self):
        """
        Handle the Duo Security authentication page by selecting push notification if available.
        """
        try:
            # First check if we're already on an authentication page before waiting
            auth_elements = self.driver.find_elements(
                By.CLASS_NAME, "authenticator-verify-list"
            )

            # Only proceed with authentication if elements are already present
            if not auth_elements:
                # Quick check to see if authentication screen appears
                try:
                    WebDriverWait(self.driver, 3).until(
                        EC.presence_of_element_located(
                            (By.CLASS_NAME, "authenticator-verify-list")
                        )
                    )
                except TimeoutException:
                    # No authentication required, exit early
                    return

            # At this point, we know authentication is needed

            # Try to find the "Get a push notification" button
            push_buttons = self.driver.find_elements(
                By.XPATH,
                "//h3[contains(text(), 'Get a push notification')]/../..//a[contains(@class, 'button')]",
            )

            if push_buttons:
                # Click the push notification button
                push_buttons[0].click()
                # print("[DEBUG] Selected push notification for authentication")
            else:
                # If push notification not available, look for any authentication option
                auth_buttons = self.driver.find_elements(
                    By.XPATH,
                    "//div[contains(@class, 'authenticator-button')]//a[contains(@class, 'button')]",
                )
                if auth_buttons:
                    auth_buttons[0].click()
                    # print("[DEBUG] Selected available authentication method")
                else:
                    print(
                        "No authentication methods found. Manual intervention may be required."
                    )
                    input("Press Enter after completing authentication...")
        except Exception as e:
            print(f"Error during authentication: {e}")
            # Don't prompt for manual intervention unless we're sure authentication is needed
            if "authenticator-verify-list" in self.driver.page_source:
                input(
                    "Please complete authentication manually, then press Enter to continue..."
                )

    def _load_cookies(self, cookie_file):
        """Load cookies from file to restore session."""
        # First navigate to the domain to set cookies properly
        self.driver.get("https://spark.unimelb.edu.au")
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
                        if domain in self.driver.current_url:
                            self.driver.add_cookie(cookie)
                    except Exception as e:
                        print(f"Couldn't add cookie {cookie.get('name')}: {e}")

            # Refresh page to apply cookies
            self.driver.refresh()
        except Exception as e:
            print(f"Error loading cookies: {e}")

    def _save_cookies(self, cookie_file):
        """Save browser cookies to file for future sessions."""
        # Wait a bit for any authentication to complete
        time.sleep(2)

        try:
            # Get all cookies and save them
            cookies = self.driver.get_cookies()
            with open(cookie_file, "w") as f:
                json.dump(cookies, f)
            print(f"Saved {len(cookies)} cookies to {cookie_file}")
        except Exception as e:
            print(f"Error saving cookies: {e}")

    def _determine_sparkai_url(self, thread_id):
        """URL of web SparkAI chat interface"""
        url = (
            f"https://spark.unimelb.edu.au/securechat/threads/{thread_id}"
            if thread_id
            else "https://spark.unimelb.edu.au/securechat"
        )
        self.driver.get(url)

    def send_message(self, message):
        """
        Send a message to SparkAI and get the response.
        Parameters
        ----------
        message : str
            The message to send to SparkAI.

        Returns
        -------
        str
            The AI's response.
        """
        self._send_message(message)
        return self._get_llm_response_from_copy_button()

    def _send_message(self, message):
        """
        Send a message to SparkAI.
        Parameters
        ----------
        message : str
            The message content to send.
        Returns
        -------
        str
            The complete message sent.
        """
        try:
            # Import ActionChains and Keys for keyboard interactions
            from selenium.webdriver.common.action_chains import ActionChains
            from selenium.webdriver.common.keys import Keys

            message_box = WebDriverWait(self.driver, 8).until(
                EC.presence_of_element_located((By.NAME, "prompt"))
            )
            message_box.clear()

            # Split message into lines
            lines = message.split("\n")

            # Type first line normally
            message_box.send_keys(lines[0])

            # For subsequent lines, use Shift+Enter and then the line content
            for line in lines[1:]:
                # Create action chain for Shift+Enter
                actions = ActionChains(self.driver)
                actions.key_down(Keys.SHIFT)
                actions.send_keys(Keys.ENTER)
                actions.key_up(Keys.SHIFT)
                actions.send_keys(line)
                actions.perform()

                # Small delay to ensure proper input
                time.sleep(0.1)

            # Click the send button
            send_button = WebDriverWait(self.driver, 2).until(
                EC.element_to_be_clickable((By.ID, "send-button"))
            )
            send_button.click()

            # Wait for message to be sent (loading indicator to disappear)
            try:
                WebDriverWait(self.driver, 2).until_not(
                    EC.presence_of_element_located(
                        (By.XPATH, "//div[contains(@class, 'animate-pulse')]")
                    )
                )
            except:
                pass

            return message
        except Exception as e:
            sys.stderr.write(f"Error sending message: {e}\n")
            return message

    def _get_llm_response_from_copy_button(self):
        """
        Retrieve SparkAI's response via clipboard copy button.
        Returns
        -------
        str
            The text obtained from the system clipboard.
        """
        try:
            # Get original number of copy buttons
            orig_count = self._count_n_copy_buttons()
            # Wait for response to complete and new copy button to appear
            self._monitor_n_copy_buttons(orig_count)
            # Wait for any loading animations to disappear
            try:
                WebDriverWait(self.driver, 64).until_not(
                    EC.presence_of_element_located(
                        (By.XPATH, "//div[contains(@class, 'animate-pulse')]")
                    )
                )
            except:
                # No loading animation found, continue
                pass
            # Small delay to ensure response is fully loaded
            time.sleep(0.5)
            # Find all copy buttons and click the last one (most recent response)
            copy_button_xpath = "//button[.//div[contains(@class, 'sr-only') and normalize-space(text())='Copy message']]"
            new_buttons = self.driver.find_elements(
                By.XPATH, copy_button_xpath
            )
            new_button = new_buttons[-1]

            # Detect if we're in WSL
            in_wsl = (
                "microsoft-standard" in os.uname().release.lower()
                if hasattr(os, "uname")
                else False
            )

            if in_wsl:
                # In WSL, use JavaScript method directly
                new_button.click()
                time.sleep(0.5)
                clipboard_text = self._get_clipboard_contents()
            else:
                # For other platforms, try pyperclip first
                try:
                    # Clear clipboard before clicking the copy button
                    pyperclip.copy("")
                    # Click the copy button
                    new_button.click()
                    # Give time for the clipboard operation to complete
                    time.sleep(0.5)
                    # Use pyperclip to get clipboard contents
                    clipboard_text = pyperclip.paste()
                    if not clipboard_text:
                        clipboard_text = self._get_clipboard_contents()
                except Exception:
                    # Fallback to JavaScript method
                    new_button.click()
                    time.sleep(0.5)
                    clipboard_text = self._get_clipboard_contents()

            return clipboard_text
        except Exception as e:
            sys.stderr.write(f"Error getting response: {e}\n")
            self.driver.save_screenshot("clipboard_error.png")
            return f"Error retrieving response: {str(e)}"

    def _count_n_copy_buttons(self):
        """
        Count the number of copy buttons present on the page.
        Returns
        -------
        int
            The count of copy buttons.
        """
        copy_button_xpath = "//button[.//div[contains(@class, 'sr-only') and normalize-space(text())='Copy message']]"
        return len(self.driver.find_elements(By.XPATH, copy_button_xpath))

    def _monitor_n_copy_buttons(self, orig_count):
        """
        Wait until the number of copy buttons increases from the original count.
        Parameters
        ----------
        orig_count : int
            The initial number of copy buttons.
        Returns
        -------
        int
            The new count of copy buttons.
        """
        copy_button_xpath = "//button[.//div[contains(@class, 'sr-only') and normalize-space(text())='Copy message']]"
        WebDriverWait(self.driver, 32).until(
            lambda d: len(d.find_elements(By.XPATH, copy_button_xpath))
            > orig_count
        )
        return len(self.driver.find_elements(By.XPATH, copy_button_xpath))

    def _get_clipboard_contents(self):
        """
        Retrieve text from the clipboard using the browser's asynchronous script.
        Returns
        -------
        str
            The text content from the clipboard.
        """
        try:
            return self.driver.execute_async_script(
                """
                var callback = arguments[arguments.length - 1];
                navigator.clipboard.readText().then(text => callback(text)).catch(err => callback(''));
                """
            )
        except Exception as e:
            sys.stderr.write(f"Error reading clipboard: {e}\n")
            return ""

    def close(self):
        """Close the web driver and exit the browser."""
        self.driver.quit()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SparkAI CLI Interface")
    # Environment variables with fallbacks
    default_thread_id = os.environ.get("SPARKAI_THREAD_ID")
    # Convert "None" string to actual None
    if default_thread_id in ["None", "none", "null", ""]:
        default_thread_id = None
    default_chrome_profile = os.environ.get("SPARKAI_CHROME_PROFILE")
    default_timeout = int(os.environ.get("SPARKAI_TIMEOUT", "30"))
    default_username = os.environ.get("SPARKAI_USERNAME")
    default_password = os.environ.get("SPARKAI_PASSWORD")
    default_cookie_file = os.environ.get("SPARKAI_COOKIE_FILE")

    parser.add_argument(
        "--thread-id",
        type=str,
        default=default_thread_id,
        help="Thread ID to resume a previous conversation",
    )
    parser.add_argument(
        "--chrome-profile",
        type=str,
        default=default_chrome_profile,
        help="Path to Chrome user data directory",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=default_timeout,
        help="Maximum wait time in seconds (default: %(default)s)",
    )
    parser.add_argument(
        "--no-auto-login",
        action="store_true",
        default=os.environ.get("SPARKAI_NO_AUTO_LOGIN", "").lower()
        in ("true", "yes", "1"),
        help="Not attempt automatic login with credentials",
    )
    parser.add_argument(
        "--username",
        type=str,
        default=default_username,
        help="SSO username for auto-login",
    )
    parser.add_argument(
        "--password",
        type=str,
        default=default_password,
        help="SSO password for auto-login",
    )
    parser.add_argument(
        "--cookie-file",
        type=str,
        default=default_cookie_file,
        help="File to save/load session cookies",
    )
    parser.add_argument(
        "message",
        type=str,
        nargs="?",
        help="Message to send to SparkAI",
    )
    parser.add_argument(
        "--input-file",
        "-i",
        type=str,
        default=os.environ.get("SPARKAI_INPUT_FILE"),
        help="Read message from this file instead of command line",
    )
    parser.add_argument(
        "--output-file",
        "-o",
        type=str,
        default=os.environ.get("SPARKAI_OUTPUT_FILE"),
        help="Save response to this file",
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        default=os.environ.get("SPARKAI_NO_HEADLESS", "").lower()
        in ("true", "yes", "1"),
        help="Show Chrome browser window instead of running headless",
    )
    parser.add_argument(
        "--keep-open",
        action="store_true",
        default=os.environ.get("SPARKAI_KEEP_OPEN", "").lower()
        in ("true", "yes", "1"),
        help="Keep the browser open after running",
    )
    parser.add_argument(
        "--no-persistent-profile",
        action="store_true",
        default=os.environ.get("SPARKAI_NO_PERSISTENT_PROFILE", "").lower()
        in ("true", "yes", "1"),
        help="Don't maintain persistent browser profile",
    )

    args = parser.parse_args()
    # Check if message is from stdin when not provided as argument
    if not args.message and not sys.stdin.isatty():
        args.message = sys.stdin.read().strip()
    return args


def main():
    # Parse command line arguments
    args = parse_args()

    # Fix the SparkAI class by creating a simple version that runs directly
    sparkai = SparkAI(
        thread_id=args.thread_id,
        path_chrome_config=args.chrome_profile,
        max_wait_sec=args.timeout,
        auto_login=not args.no_auto_login,
        username=args.username,
        password=args.password,
        cookie_file=args.cookie_file,
        headless=not args.no_headless,
        persistent_profile=not args.no_persistent_profile,
    )

    try:
        # If we have an input file, read from it
        if args.input_file:
            with open(args.input_file, "r", encoding="utf-8") as f:
                message = f.read()
        # If we have a direct message, use it
        elif args.message:
            message = args.message
        else:
            print("No message provided. Exiting.")
            if not args.keep_open:
                sparkai.close()
            return
        # Send the message and get the response
        response = sparkai.send_message(message)
        # If we have an output file, write to it
        if args.output_file:
            with open(args.output_file, "w", encoding="utf-8") as f:
                f.write(response)
        else:
            # Otherwise print to stdout
            print(response)

    except Exception as e:
        print(f"Error: {e}")
        sys.stderr.write(f"Error: {str(e)}\n")

    # Keep browser open if requested
    if args.keep_open:
        try:
            print("Browser is being kept open. Press Ctrl+C to exit...")
            # Keep the script running until user interrupts with Ctrl+C
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nExiting...")
        finally:
            # Only close when the user explicitly exits
            sparkai.close()
    else:
        # Close the browser by default
        sparkai.close()


if __name__ == "__main__":
    main()

# EOF