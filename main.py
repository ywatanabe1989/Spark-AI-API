#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-03-15 15:56:28 (ywatanabe)"
# File: /home/ywatanabe/proj/SparkAI/main.py
# ----------------------------------------
import os
__FILE__ = (
    "/home/ywatanabe/proj/SparkAI/main.py"
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
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException


class SparkAI:
    """
    Class SparkAI provides an interface to interact with SparkAI using Selenium.

    Methods
    -------
    __init__(...)
        Initialize the SparkAI instance.
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
    run()
        Run the interactive messaging loop.
    close()
        Close the browser session.
    """

    def __init__(
        self,
        thread_id=None,
        path_chrome_config=None,
        max_wait_sec=30,
        prompt_template="",
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
        prompt_template : str
            Text template to prepend to messages.
        """

        self.driver = self._setup_chrome(path_chrome_config)
        url = self._determine_sparkai_url(thread_id)
        input(
            "Please login to SparkAI in the browser, then press Enter to continue..."
        )
        self.wait = WebDriverWait(self.driver, max_wait_sec)

        # Template to preceed given text
        self.prompt_template = prompt_template

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
        driver = webdriver.Chrome(options=chrome_options)
        return driver

    def _determine_sparkai_url(self, thread_id):
        """URL of web SparkAI chat interface"""
        url = (
            f"https://spark.unimelb.edu.au/securechat/threads/{thread_id}"
            if thread_id
            else "https://spark.unimelb.edu.au/securechat"
        )
        self.driver.get(url)

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
            The complete message sent (including the template).
        """

        actual_message = self.prompt_template + "\n\n" + message
        try:
            message_box = self.wait.until(
                EC.presence_of_element_located((By.NAME, "prompt"))
            )
            message_box.clear()
            message_box.send_keys(actual_message)
            send_button = self.wait.until(
                EC.element_to_be_clickable((By.ID, "send-button"))
            )
            send_button.click()
        except Exception as e:
            sys.stderr.write(f"Error sending message: {e}\n")
            # self.driver.save_screenshot("_send_message_error.png")

        return actual_message

    def _get_llm_response_from_copy_button(self):
        """
        Retrieve SparkAI's response via clipboard copy button.

        Returns
        -------
        str
            The text obtained from the system clipboard.
        """
        orig_count = self._count_n_copy_buttons()
        self._monitor_n_copy_buttons(orig_count)
        copy_button_xpath = "//button[.//div[contains(@class, 'sr-only') and normalize-space(text())='Copy message']]"
        new_buttons = self.driver.find_elements(By.XPATH, copy_button_xpath)
        new_button = new_buttons[-1]
        new_button.click()
        time.sleep(0.5)
        return self._get_clipboard_contents()

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

    def run(self):
        """
        Run an interactive loop to send messages and display responses.

        The loop continues until the user inputs 'quit' or 'exit'.
        """
        print("Enter your message (type 'quit' to exit):\n\n", flush=True)
        while True:
            user_input = input("========== YOU ==========\n\n")

            if not user_input:
                continue
            if user_input.lower() in ["quit", "exit"]:
                break

            # Printing
            _actual_message = self._send_message(user_input)
            print()
            llm_response = self._get_llm_response_from_copy_button()
            print(
                f"========== LLM RESPONSE ==========\n\n{llm_response}\n",
                flush=True,
            )

    def close(self):
        """Close the web driver and exit the browser."""
        self.driver.quit()


if __name__ == "__main__":
    sparkai = SparkAI()
    sparkai.run()
    # sparkai.close()

# EOF