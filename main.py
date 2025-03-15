#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-03-15 23:53:11 (ywatanabe)"
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
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException

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
        parser_mode=False,
        headless=True
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
        parser_mode : bool
            Use response parsing instead of clipboard.
        headless : bool
            Run Chrome in headless mode without visible window.
        """
        self.parser_mode = parser_mode
        self.driver = self._setup_chrome(path_chrome_config)

        # Initialize the wait object before using it in auto_login
        self.wait = WebDriverWait(self.driver, max_wait_sec)

        # Load cookies if available
        if cookie_file and os.path.exists(cookie_file):
            self._load_cookies(cookie_file)

        # Navigate to SparkAI
        url = self._determine_sparkai_url(thread_id)

        # Handle login
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
    def _setup_chrome(path_chrome_config):
        """Chrome settings"""
        if not path_chrome_config:
            if os.name == "nt":
                path_chrome_config = rf"C:\Users\{os.getlogin()}\AppData\Local\Google\Chrome\User Data\Default"
            else:
                path_chrome_config = os.path.expanduser(
                    "~/.config/google-chrome/Default"
                )
        chrome_options = Options()
        chrome_options.add_argument(f"user-data-dir={path_chrome_config}")
        # Enable clipboard permissions
        chrome_options.add_argument("--enable-features=ClipboardContentSetting")
        # Set window size to ensure elements are visible
        chrome_options.add_argument("--window-size=1920,1080")
        # Allow clipboard access
        chrome_options.add_experimental_option("prefs", {
            "profile.content_settings.exceptions.clipboard": {
                "[*.]*": {"setting": 1}  # 1 = Allow
            }
        })
        driver = webdriver.Chrome(options=chrome_options)
        return driver

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
        chrome_options.add_argument(f"user-data-dir={path_chrome_config}")
        # Enable clipboard permissions
        chrome_options.add_argument("--enable-features=ClipboardContentSetting")
        # Set window size to ensure elements are visible
        chrome_options.add_argument("--window-size=1920,1080")

        # Add headless mode options
        if headless:
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")

        # Allow clipboard access
        chrome_options.add_experimental_option("prefs", {
            "profile.content_settings.exceptions.clipboard": {
                "[*.]*": {"setting": 1}  # 1 = Allow
            }
        })
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
                self.wait.until(EC.presence_of_element_located((By.NAME, "prompt")))
                # print("Already logged in.")
                return True
            except TimeoutException:
                pass

            # Wait for login form - username field
            username_field = self.wait.until(
                EC.presence_of_element_located((By.NAME, "identifier"))
            )
            username_field.clear()
            username_field.send_keys(username)
            time.sleep(0.5)

            # Click the Next button
            next_button = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "input.button-primary[value='Next']"))
            )
            next_button.click()

            # Wait for password field to appear
            password_field = self.wait.until(
                EC.presence_of_element_located((By.NAME, "credentials.passcode"))
            )
            password_field.clear()
            password_field.send_keys(password)

            # Click verify button
            verify_button = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='submit'][value='Verify']"))
            )
            verify_button.click()

            # Wait for successful login or MFA challenge
            try:
                # Check if we need to handle MFA
                self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".mfa-verify-form")))
                print("MFA required. Please enter the code in the browser.")
                input("Press Enter after completing MFA...")
            except TimeoutException:
                # No MFA needed
                pass

            # Wait for chat interface to load
            self.wait.until(EC.presence_of_element_located((By.NAME, "prompt")))
            print("Login successful.")
            return True

        except Exception as e:
            print(f"Login failed: {e}")
            input("Please login manually, then press Enter to continue...")
            return False

    def _save_cookies(self, cookie_file):
        """Save browser cookies to file for future sessions."""
        with open(cookie_file, 'w') as f:
            json.dump(self.driver.get_cookies(), f)

    def _load_cookies(self, cookie_file):
        """Load cookies from file to restore session."""
        self.driver.get("https://spark.unimelb.edu.au")
        try:
            with open(cookie_file, 'r') as f:
                cookies = json.load(f)
                for cookie in cookies:
                    self.driver.add_cookie(cookie)
        except Exception as e:
            print(f"Error loading cookies: {e}")

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

            message_box = self.wait.until(
                EC.presence_of_element_located((By.NAME, "prompt"))
            )
            message_box.clear()

            # Split message into lines
            lines = message.split('\n')

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
            send_button = self.wait.until(
                EC.element_to_be_clickable((By.ID, "send-button"))
            )
            send_button.click()

            # Wait for message to be sent (loading indicator to disappear)
            try:
                self.wait.until_not(
                    EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'animate-pulse')]"))
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
        if self.parser_mode:
            return self._get_llm_response_by_parsing()
        try:
            # Get original number of copy buttons
            orig_count = self._count_n_copy_buttons()
            # Wait for response to complete and new copy button to appear
            self._monitor_n_copy_buttons(orig_count)
            # Wait for any loading animations to disappear
            try:
                self.wait.until_not(
                    EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'animate-pulse')]"))
                )
            except:
                # No loading animation found, continue
                pass
            # Small delay to ensure response is fully loaded
            time.sleep(0.5)
            # Find all copy buttons and click the last one (most recent response)
            copy_button_xpath = "//button[.//div[contains(@class, 'sr-only') and normalize-space(text())='Copy message']]"
            new_buttons = self.driver.find_elements(By.XPATH, copy_button_xpath)
            new_button = new_buttons[-1]

            # Detect if we're in WSL
            in_wsl = "microsoft-standard" in os.uname().release.lower() if hasattr(os, 'uname') else False

            if in_wsl:
                # In WSL, use JavaScript method directly
                new_button.click()
                time.sleep(0.5)
                clipboard_text = self._get_clipboard_contents()
            else:
                # For other platforms, try pyperclip first
                try:
                    # Clear clipboard before clicking the copy button
                    pyperclip.copy('')
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

    def _get_llm_response_by_parsing(self):
        """
        Parse LLM response directly from the DOM without using clipboard.
        Returns
        -------
        str
            The extracted text response.
        """
        try:
            # Get original count of messages
            orig_count = self._count_n_copy_buttons()

            # Wait for new message
            self._monitor_n_copy_buttons(orig_count)

            # Wait a moment for any animations to complete
            time.sleep(0.5)

            # Find the message container for the latest message
            message_containers = self.driver.find_elements(
                By.XPATH,
                "//div[contains(@class, 'prose') and contains(@class, 'w-full')]"
            )

            # Get the last container (most recent message)
            if not message_containers:
                return "Could not find message container"

            latest_container = message_containers[-1]

            # Extract text content
            response_text = self.driver.execute_script("""
                function extractTextWithCodeBlocks(element) {
                    let result = '';

                    // Handle all child nodes
                    for (const node of element.childNodes) {
                        // If text node, just add the text
                        if (node.nodeType === Node.TEXT_NODE) {
                            result += node.textContent;
                        }
                        // If element node
                        else if (node.nodeType === Node.ELEMENT_NODE) {
                            // For code blocks
                            if (node.tagName === 'PRE') {
                                const codeElement = node.querySelector('code');
                                if (codeElement) {
                                    result += '```\\n' + codeElement.textContent + '\\n```\\n';
                                } else {
                                    result += '```\\n' + node.textContent + '\\n```\\n';
                                }
                            }
                            // For other block elements, ensure there are line breaks
                            else if (getComputedStyle(node).display === 'block') {
                                const innerText = extractTextWithCodeBlocks(node);
                                if (innerText.trim()) {
                                    result += innerText + '\\n';
                                }
                            }
                            // For inline elements, just get their text
                            else {
                                result += extractTextWithCodeBlocks(node);
                            }
                        }
                    }
                    return result;
                }

                return extractTextWithCodeBlocks(arguments[0]);
            """, latest_container)

            return response_text.strip()

        except Exception as e:
            sys.stderr.write(f"Error parsing response: {e}\n")
            self.driver.save_screenshot("parser_error.png")
            return f"Error parsing response: {str(e)}"

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
        self.wait.until(
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
    parser = argparse.ArgumentParser(description='SparkAI CLI Interface')

    # Environment variables with fallbacks
    default_thread_id = os.environ.get('SPARKAI_THREAD_ID')
    # Convert "None" string to actual None
    if default_thread_id in ["None", "none", "null", ""]:
        default_thread_id = None

    default_chrome_profile = os.environ.get('SPARKAI_CHROME_PROFILE')
    default_timeout = int(os.environ.get('SPARKAI_TIMEOUT', '30'))
    default_username = os.environ.get('SPARKAI_USERNAME')
    default_password = os.environ.get('SPARKAI_PASSWORD')
    default_cookie_file = os.environ.get('SPARKAI_COOKIE_FILE')
    default_parser_mode = os.environ.get('SPARKAI_PARSER_MODE', '').lower() in ('true', 'yes', '1')

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
        default=os.environ.get('SPARKAI_NO_AUTO_LOGIN', '').lower() in ('true', 'yes', '1'),
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
        "--parser-mode",
        action="store_true",
        default=default_parser_mode,
        help="Use DOM parsing instead of clipboard for responses",
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
        default=os.environ.get('SPARKAI_INPUT_FILE'),
        help="Read message from this file instead of command line",
    )
    parser.add_argument(
        "--output-file",
        "-o",
        type=str,
        default=os.environ.get('SPARKAI_OUTPUT_FILE'),
        help="Save response to this file",
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        default=os.environ.get('SPARKAI_NO_HEADLESS', '').lower() in ('true', 'yes', '1'),
        help="Show Chrome browser window instead of running headless",
    )
    args = parser.parse_args()

    # Check if message is from stdin when not provided as argument
    if not args.message and not sys.stdin.isatty():
        args.message = sys.stdin.read().strip()

    return args

def main():
    args = parse_args()

    # Get message from input file if specified
    if args.input_file:
        try:
            with open(args.input_file, 'r', encoding='utf-8') as f:
                args.message = f.read().strip()
        except Exception as e:
            print(f"Error reading input file: {e}")
            sys.exit(1)

    # Check if message is from stdin when not provided as argument or file
    if not args.message and not sys.stdin.isatty():
        args.message = sys.stdin.read().strip()

    if not args.message:
        print("Error: No message provided. Please provide a message as an argument, via stdin, or with --input-file.")
        sys.exit(1)

    # Initialize SparkAI with command-line arguments
    sparkai = SparkAI(
        thread_id=args.thread_id,
        path_chrome_config=args.chrome_profile,
        max_wait_sec=args.timeout,
        auto_login=(not args.no_auto_login),
        username=args.username,
        password=args.password,
        cookie_file=args.cookie_file,
        parser_mode=args.parser_mode,
        headless=(not args.no_headless),
    )

    try:
        # Send the message and get response
        llm_response = sparkai.send_message(args.message)

        # Output response
        if args.output_file:
            with open(args.output_file, 'w', encoding='utf-8') as f:
                f.write(llm_response)
            print(f"Response saved to {args.output_file}")
        else:
            print(llm_response)
    finally:
        sparkai.close()

if __name__ == "__main__":
    main()

# EOF