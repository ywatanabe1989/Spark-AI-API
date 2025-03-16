#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-03-16 15:03:29 (ywatanabe)"
# File: /home/ywatanabe/proj/spark-ai-api/src/sparkai/SparkAI.py
# ----------------------------------------
import os
__FILE__ = (
    "/home/ywatanabe/proj/spark-ai-api/src/sparkai/SparkAI.py"
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
import uuid
import time
import sys
import argparse
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from .ChromeManager import ChromeManager
from .parse_args import parse_args
from .debug_print import debug_print

class SparkAI:
    def __init__(
        self,
        chat_id=None,
        path_chrome_config=None,
        max_wait_sec=30,
        auto_login=False,
        username=None,
        password=None,
        cookie_file=None,
        headless=False,
        persistent_profile=True,
        browser_id=None,
        debugger_address="localhost:9222",
        response_timeout=120,
        force_new_chat=False,
        kill_zombie=False,
        reuse_browser=True,  # Added parameter to control browser reuse
        force_new_window=False, # Force a new Chrome window even if one exists
    ):
        """
        Initialize SparkAI instance with Chrome browser.
        Parameters
        ----------
        browser_id : str, optional
            Identifier for browser instance. If provided, will try to reuse.
        chat_id : str, optional
            Identifier for chat conversation thread
        debugger_address : str, optional
            Address for remote debugging (e.g., "localhost:9222")
        force_new_chat : bool, optional
            Whether to force creation of a new chat thread even if reusing browser
        reuse_browser : bool, optional
            Whether to attempt to reuse an existing browser instead of creating a new one
        force_new_window : bool, optional
            Whether to force creation of a new Chrome window even if one exists
        """
        debug_print(f"SparkAI initialization started")
        self.path_chrome_config = path_chrome_config
        self.persistent_profile = persistent_profile
        self.max_wait_sec = max_wait_sec
        self.response_timeout = response_timeout
        self.force_new_chat = force_new_chat
        self.reuse_browser = reuse_browser
        self.force_new_window = force_new_window

        # Store credentials for possible reuse during session
        self.username = username
        self.password = password
        self.auto_login = auto_login

        # Use browser_id or default
        self.browser_id = browser_id or os.environ.get("SPARKAI_BROWSER_ID", "spark-ai-chat")
        self.chat_id = chat_id
        self.debugger_address = debugger_address
        self.kill_zombie = kill_zombie
        self.chrome_manager = ChromeManager.get_instance()
        self.chrome_manager.response_timeout = response_timeout

        # Tracking variable for browser state
        self._browser_initialized = False

        # Maximum retry attempts
        max_attempts = 3
        last_exception = None

        # First check if browser exists in active list
        active_browsers = self.chrome_manager.get_active_browsers()
        debug_print(f"Active browsers: {active_browsers}")

        # Get debugging port
        debugging_port = 9222
        if self.debugger_address and ":" in self.debugger_address:
            try:
                debugging_port = int(self.debugger_address.split(":")[-1])
            except ValueError:
                pass

        for attempt in range(max_attempts):
            try:
                debug_print(f"Browser initialization attempt {attempt+1}/{max_attempts}")

                # Get or create driver with proper options
                driver = self.chrome_manager.get_driver(
                    browser_id=self.browser_id,
                    headless=headless,
                    remote_debugging=True,
                    debugging_port=debugging_port,
                    force_new=self.force_new_window
                )

                if driver:
                    self._browser_initialized = True

                    # If force_new_chat is True, navigate to a new chat URL
                    if self.force_new_chat:
                        debug_print(f"Force new chat requested, navigating to new chat URL")
                        spark_url = self._determine_sparkai_url(None)  # New chat URL
                        self.chrome_manager.navigate_to(self.browser_id, spark_url)
                        self.chat_id = None  # Reset chat_id to ensure we get a new one

                    break  # Successful initialization

            except Exception as e:
                debug_print(f"Error on browser initialization attempt {attempt+1}: {e}")
                last_exception = e
                if attempt < max_attempts - 1:
                    debug_print(f"Waiting before retry...")
                    time.sleep(3)  # Longer wait between retries

        # If we got here without initialization, raise exception
        if not self._browser_initialized:
            error_msg = f"Failed to launch Chrome browser after {max_attempts} attempts"
            if last_exception:
                error_msg += f": {last_exception}"
            raise Exception(error_msg)

        # Continue with normal initialization if browser is ready
        try:
            # Navigate to SparkAI URL
            debug_print(f"Navigating to SparkAI URL")
            spark_url = self._determine_sparkai_url(chat_id)
            if not self.chrome_manager.navigate_to(self.browser_id, spark_url):
                debug_print(f"Initial navigation failed")

            # Handle login if needed
            if auto_login and username and password:
                debug_print(f"Starting auto-login process")
                self._auto_login(username, password)
        except Exception as e:
            debug_print(f"Error during post-initialization: {e}")
            # Not raising exception here to allow fallback behaviors

    def close(self):
        """
        Releases the browser instance without destroying it
        """
        # Instead of quitting the driver, just mark it as available for reuse
        if self.browser_id and hasattr(self, 'chrome_manager'):
            debug_print(f"Marking browser {self.browser_id} as available without closing")
            self.chrome_manager.close(self.browser_id)

    def destroy(self):
        """Force close the browser completely"""
        debug_print(f"destroy() called - closing browser with browser_id {self.browser_id}")
        # Set a flag to indicate whether to close the browser
        # Use environment variable to control browser persistence
        if os.environ.get("SPARKAI_KEEP_BROWSER", "").lower() in ("true", "yes", "1"):
            debug_print(f"SPARKAI_KEEP_BROWSER is set to true - keeping browser open")
            self.chrome_manager.close(self.browser_id)  # Just mark as available, don't close
        else:
            self.chrome_manager.close_driver(self.browser_id)

    def _auto_login(self, username=None, password=None, max_retry=3):
        """
        Attempt auto-login to SparkAI

        Parameters
        ----------
        username : str, optional
            Username for auto-login
        password : str, optional
            Password for auto-login
        max_retry : int, optional
            Maximum number of login attempts

        Returns
        -------
        bool
            Whether login was successful
        """
        debug_print("_auto_login() started")

        # Use provided credentials or try to get them from environment
        username = username or os.environ.get('SPARKAI_USERNAME') or os.environ.get('SPARK_USERNAME')
        password = password or os.environ.get('SPARKAI_PASSWORD') or os.environ.get('SPARK_PASSWORD')

        if not username or not password:
            debug_print("Auto-login credentials not available")
            return False

        # Check if already logged in
        debug_print("Checking if already on message page")
        try:
            driver = self.chrome_manager.get_driver(self.browser_id)
            if not driver:
                return False

            message_box = driver.find_elements(By.NAME, "prompt")
            if message_box and message_box[0].is_displayed():
                debug_print("Already logged in, no action needed")
                return True
            else:
                debug_print("Not logged in yet, proceeding with login")
        except Exception as e:
            debug_print(f"Error checking login state: {e}")

        # Import login utility here to avoid circular imports
        try:
            from .auth_utils import login_to_spark
            debug_print("Calling login_to_spark from auth_utils")
            result = login_to_spark(
                self.chrome_manager.get_driver(self.browser_id),
                username,
                password
            )
            debug_print(f"login_to_spark result: {result}")
            return result
        except Exception as e:
            debug_print(f"Error during auto-login: {e}")
            return False

    def _load_cookies(self, cookie_file):
        """Load cookies from file to restore session."""
        debug_print(f"Loading cookies via ChromeManager for browser_id {self.browser_id}")
        self.chrome_manager.load_cookies(self.browser_id, cookie_file)

    def _save_cookies(self, cookie_file):
        """Save browser cookies to file for future sessions."""
        debug_print(f"Saving cookies via ChromeManager for browser_id {self.browser_id}")
        self.chrome_manager.save_cookies(self.browser_id, cookie_file)

    @staticmethod
    def _determine_sparkai_url(chat_id):
        """URL of web SparkAI chat interface"""
        url = (
            f"https://spark.unimelb.edu.au/securechat/threads/{chat_id}"
            if chat_id
            else "https://spark.unimelb.edu.au/securechat"
        )
        debug_print(f"Determined SparkAI URL: {url}")
        return url

    def get_current_chat_id(self):
        """Get the current thread ID from the browser URL"""
        try:
            current_url = self.driver.current_url
            if "/threads/" in current_url:
                chat_id = current_url.split("/threads/")[1].split("?")[0]
                self.chat_id = chat_id
                return chat_id
            return None
        except:
            return None

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
        debug_print(f"send_message() called with message length: {len(message)}")

        # Check if we need to login when reusing a browser session
        try:
            driver = self.chrome_manager.get_driver(self.browser_id)
            current_url = driver.current_url

            # If current URL contains login or SSO pages, we need to login again
            if ("login" in current_url.lower() or
                "authorize" in current_url.lower() or
                "sso" in current_url.lower() or
                "authenticate" in current_url.lower() or
                not current_url.startswith("https://spark.unimelb.edu.au")):

                debug_print(f"Browser needs authentication at {current_url}")

                # Navigate to main URL first
                spark_url = self._determine_sparkai_url(self.chat_id)
                self.chrome_manager.navigate_to(self.browser_id, spark_url)

                # Try auto-login if credentials are available
                if hasattr(self, 'username') and hasattr(self, 'password') and self.username and self.password:
                    debug_print(f"Attempting automatic re-login")
                    self._auto_login(self.username, self.password)
                else:
                    debug_print(f"Manual login required")
                    input("Please log in manually in the browser window, then press Enter to continue...")

        except Exception as e:
            debug_print(f"Error checking login status: {e}")

        # Now try to send the message
        try:
            debug_print(f"Attempting to send message via ChromeManager for browser_id {self.browser_id}")
            result = self.chrome_manager.send_message_to_spark(self.browser_id, message)
            debug_print(f"ChromeManager send_message_to_spark result: {result}")

            if not result:
                raise Exception("Failed to send message through ChromeManager")

            debug_print(f"Getting response from Spark")
            response = self.chrome_manager.get_response_from_spark(self.browser_id)
            debug_print(f"Got response of length: {len(response) if response else 0}")

            # Update chat_id after sending message
            chat_id = self.get_current_chat_id()
            if chat_id:
                debug_print(f"Updated chat_id to {chat_id}")

            return response
        except Exception as e:
            sys.stderr.write(f"Error sending/receiving message: {e}\n")
            debug_print(f"Error using ChromeManager methods: {e}")
            debug_print(f"Falling back to original implementation")

            # Fall back to original implementation
            self._send_message(message)
            return self._get_llm_response_from_copy_button()


    def _get_llm_response_from_copy_button(self):
        """
        Retrieve SparkAI's response via clipboard copy button.
        Returns
        -------
        str
            The text obtained from the system clipboard.
        """
        import pyperclip
        debug_print(f"_get_llm_response_from_copy_button() fallback method called")
        try:
            # Get original number of copy buttons
            copy_button_xpath = "//button[.//div[contains(@class, 'sr-only') and normalize-space(text())='Copy message']]"
            orig_count = len(self.driver.find_elements(By.XPATH, copy_button_xpath))
            debug_print(f"Found {orig_count} initial copy buttons")

            # Check for message processing indicators
            message_processing = False

            # First check for loading animation (may not be present in reused sessions)
            try:
                loading_elements = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'animate-pulse')]")
                if loading_elements and len(loading_elements) > 0:
                    debug_print(f"Loading animation detected, will wait for it to disappear")
                    message_processing = True

                    # Wait for loading animations to disappear
                    WebDriverWait(self.driver, 64).until_not(
                        EC.presence_of_element_located(
                            (By.XPATH, "//div[contains(@class, 'animate-pulse')]")
                        )
                    )
                    debug_print(f"Loading animation gone")
            except Exception as e:
                debug_print(f"Error checking loading animation: {e}")

            # If we didn't see loading animations, check for other processing indicators
            if not message_processing:
                debug_print(f"No loading animation detected, checking other indicators")

                # Check for text indicating AI is thinking/generating
                try:
                    thinking_elements = self.driver.find_elements(
                        By.XPATH, "//div[contains(text(), 'thinking') or contains(text(), 'generating') or contains(text(), 'processing')]"
                    )
                    if thinking_elements and len(thinking_elements) > 0:
                        debug_print(f"AI thinking indicator found, response is being generated")
                        message_processing = True
                except:
                    pass

                # In reused sessions, we might not see any indicators, so wait for new copy buttons
                max_wait_time = 60  # seconds
                start_time = time.time()

                debug_print(f"Monitoring for new copy buttons to appear (max wait: {max_wait_time}s)")
                while time.time() - start_time < max_wait_time:
                    current_buttons = self.driver.find_elements(By.XPATH, copy_button_xpath)
                    current_count = len(current_buttons)

                    if current_count > orig_count:
                        debug_print(f"New copy button appeared ({current_count} > {orig_count})")
                        break

                    # Also check for content changes in the most recent AI message
                    try:
                        last_message = self.driver.find_elements(
                            By.XPATH, "//div[contains(@class, 'chat-message') and not(contains(@class, 'user'))]//div[contains(@class, 'content')]"
                        )
                        if last_message and len(last_message) > 0:
                            # If there's content, response might be generating
                            content_text = last_message[-1].text.strip()
                            if content_text:
                                message_processing = True
                    except:
                        pass

                    # If we found a processing indicator or have waited at least 5 seconds, check less frequently
                    if message_processing or (time.time() - start_time > 5):
                        time.sleep(1)
                    else:
                        time.sleep(0.3)  # Check more frequently at first

            # Wait for a bit after processing to ensure everything is settled
            debug_print(f"Adding delay to ensure response is fully loaded")
            time.sleep(3)

            # Get final copy buttons
            new_buttons = self.driver.find_elements(By.XPATH, copy_button_xpath)
            new_count = len(new_buttons)
            debug_print(f"Found {new_count} copy buttons for final check")

            while not_copied:
                if new_count > 0:
                    new_button = new_buttons[-1]

                    # For other platforms, try pyperclip first
                    try:
                        # Clear clipboard before clicking the copy button
                        pyperclip.copy("")
                        debug_print(f"Clipboard cleared")

                        # Click the copy button
                        new_button.click()
                        debug_print(f"Copy button clicked")

                        # Give time for the clipboard operation to complete
                        time.sleep(0.5)

                        # Use pyperclip to get clipboard contents
                        clipboard_text = pyperclip.paste()
                        debug_print(f"Clipboard text retrieved, length: {len(clipboard_text) if clipboard_text else 0}")

                        if not clipboard_text:
                            debug_print(f"Empty clipboard, falling back to JavaScript method")
                            clipboard_text = self.chrome_manager.get_clipboard_contents(self.browser_id)
                    except Exception as e:
                        debug_print(f"Error with pyperclip: {e}")
                        # Fallback to JavaScript method
                        new_button.click()
                        time.sleep(0.5)
                        clipboard_text = self.chrome_manager.get_clipboard_contents(self.browser_id)

                    debug_print(f"Final response length: {len(clipboard_text) if clipboard_text else 0}")

                    # Clear clipboard after retrieving content to avoid leaving sensitive data
                    try:
                        debug_print(f"Clearing clipboard after retrieving content")
                        pyperclip.copy("")
                    except Exception as clear_e:
                        debug_print(f"Error clearing clipboard: {clear_e}")

                    return clipboard_text

        except Exception as e:
            sys.stderr.write(f"Error getting response: {e}\n")
            debug_print(f"Error in _get_llm_response_from_copy_button: {e}")
            try:
                debug_print(f"Attempting to save error screenshot")
                self.driver.save_screenshot("clipboard_error.png")
                debug_print(f"Screenshot saved as clipboard_error.png")
            except Exception as screenshot_error:
                debug_print(f"Failed to save screenshot: {screenshot_error}")
                pass
            return f"Error retrieving response: {str(e)}"

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
        from selenium.webdriver.common.action_chains import ActionChains
        from selenium.webdriver.common.keys import Keys
        debug_print(f"_send_message() fallback method called")
        try:
            debug_print(f"Waiting for message input box")
            message_box = WebDriverWait(self.driver, 8).until(
                EC.presence_of_element_located((By.NAME, "prompt"))
            )
            message_box.clear()
            # Split message into lines
            lines = message.split("\n")
            debug_print(f"Message has {len(lines)} lines")
            # Type first line normally
            message_box.send_keys(lines[0])
            debug_print(f"First line entered")
            # For subsequent lines, use Shift+Enter and then the line content
            for i, line in enumerate(lines[1:], 1):
                debug_print(f"Processing line {i+1}")
                # Create action chain for Shift+Enter
                actions = ActionChains(self.driver)
                actions.key_down(Keys.SHIFT)
                actions.send_keys(Keys.ENTER)
                actions.key_up(Keys.SHIFT)
                actions.send_keys(line)
                actions.perform()
                # Small delay to ensure proper input
                time.sleep(0.1)

            debug_print(f"Looking for send button")
            # Click the send button
            send_button = WebDriverWait(self.driver, 2).until(
                EC.element_to_be_clickable((By.ID, "send-button"))
            )
            send_button.click()
            debug_print(f"Send button clicked")
            # Wait for message to be sent (loading indicator to disappear)
            try:
                debug_print(f"Waiting for loading indicator to disappear")
                WebDriverWait(self.driver, 2).until_not(
                    EC.presence_of_element_located(
                        (By.XPATH, "//div[contains(@class, 'animate-pulse')]")
                    )
                )
                debug_print(f"Loading indicator gone")
            except:
                debug_print(f"No loading indicator found or timeout")
                pass

            return message
        except Exception as e:
            sys.stderr.write(f"Error sending message: {e}\n")
            debug_print(f"Error in _send_message: {e}")
            return message

    @property
    def driver(self):
        """Get the WebDriver instance for this browser"""
        return self.chrome_manager.get_driver(self.browser_id)


def main():
    """
    Main command-line interface function.
    """
    # Setup argument parser
    parser = argparse.ArgumentParser(description="Interact with SparkAI")
    parser.add_argument(
        "message", nargs="*", help="Message to send to SparkAI"
    )
    parser.add_argument(
        "--chat-id",
        dest="chat_id",
        help="Specified chat ID to continue conversation"
    )
    parser.add_argument(
        "--no-auto-login",
        action="store_true",
        help="Don't attempt auto-login if not logged in"
    )
    parser.add_argument(
        "--username",
        help="Username for auto-login"
    )
    parser.add_argument(
        "--password",
        help="Password for auto-login"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Response timeout in seconds"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run Chrome in headless mode"
    )
    parser.add_argument(
        "--kill-zombie",
        action="store_true",
        help="Kill existing chrome processes"
    )
    parser.add_argument(
        "--force-new-browser",
        action="store_true",
        help="Force creation of a new browser window"
    )
    parser.add_argument(
        "--force-new-window",
        action="store_true",
        help="Force creation of a new Chrome window even if one exists"
    )

    # Parse arguments
    args = parser.parse_args()
    args.force_new_chat = (not args.chat_id)
    args.auto_login = (not args.no_auto_login)

    # Make message into a single string
    message = " ".join(args.message) if args.message else ""

    # Check for special debug commands
    if message == "__debug":
        handle_debug_command()
        return

    # Initialize SparkAI
    browser_id = os.environ.get("SPARKAI_BROWSER_ID", "spark-ai-chat")

    # Get username and password from environment if not provided
    username = args.username or os.environ.get("SPARKAI_USERNAME")
    password = args.password or os.environ.get("SPARKAI_PASSWORD")

    try:
        sparkai = SparkAI(
            chat_id=args.chat_id,
            browser_id=browser_id,
            auto_login=args.auto_login,
            username=username,
            password=password,
            response_timeout=args.timeout,
            headless=args.headless,
            force_new_chat=args.force_new_chat,
            kill_zombie=args.kill_zombie,
            reuse_browser=not args.force_new_browser,
            force_new_window=args.force_new_window,
        )

        # If we have a message, send it
        if message:
            response = sparkai.send_message(message)
            print(response)  # Print to stdout for user

        # Keep browser session alive for reuse
        debug_print(f"Browser is being kept open with ID: {browser_id}")
        debug_print(f"Use SPARKAI_BROWSER_ID={browser_id} to reuse this browser")
        sparkai.chrome_manager.release_driver(browser_id)

        # Output the browser ID for possible reuse
        debug_print(browser_id)
        return 0
    except Exception as e:
        debug_print(f"Error: {e}")
        return 1

# if __name__ == "__main__":
#     main()

# EOF