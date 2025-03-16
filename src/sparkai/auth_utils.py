#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-03-16 15:02:44 (ywatanabe)"
# File: /home/ywatanabe/proj/spark-ai-api/src/sparkai/auth_utils.py
# ----------------------------------------
import os
__FILE__ = (
    "/home/ywatanabe/proj/spark-ai-api/src/sparkai/auth_utils.py"
)
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------

import time
import sys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from .debug_print import debug_print

def login_to_spark(driver, username, password, max_wait_sec=30):
    """
    Perform login to Spark AI

    Parameters
    ----------
    driver : webdriver.Chrome
        Chrome WebDriver instance
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
    try:
        # Navigate to SparkAI
        driver.get("https://spark.unimelb.edu.au/securechat")

        # Check if we're already on the messaging page
        try:
            # Use a shorter timeout just for checking if already logged in
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.NAME, "prompt"))
            )
            return True
        except TimeoutException:
            pass

        # Wait for login form - username field
        try:
            # Look for user identifier field
            username_field = WebDriverWait(driver, max_wait_sec).until(
                EC.presence_of_element_located((By.NAME, "identifier"))
            )
            username_field.clear()
            username_field.send_keys(username)
            time.sleep(0.5)

            # Click the Next button - using JavaScript for more reliable click
            next_button = WebDriverWait(driver, max_wait_sec).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "input.button-primary[value='Next']")
                )
            )
            driver.execute_script("arguments[0].click();", next_button)
            debug_print("Next button clicked via JavaScript")
            time.sleep(1)  # Give time for the page to transition

            # Wait for password field to appear
            password_field = WebDriverWait(driver, max_wait_sec).until(
                EC.presence_of_element_located(
                    (By.NAME, "credentials.passcode")
                )
            )
            password_field.clear()
            password_field.send_keys(password)

            # Click verify button - using JavaScript for more reliable click
            verify_button = WebDriverWait(driver, max_wait_sec).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "input[type='submit'][value='Verify']")
                )
            )
            driver.execute_script("arguments[0].click();", verify_button)
            debug_print("Verify button clicked via JavaScript")

            # Handle authentication methods if they appear
            handle_duo_authentication(driver, max_wait_sec)
        except Exception as e:
            # Try generic login form detection as fallback
            debug_print(f"Standard login form not found: {e}. Trying generic login form detection...")
            try:
                # Find any username/email input field
                username_fields = driver.find_elements(By.XPATH,
                    "//input[@type='text' or @type='email' or contains(@name, 'user') or contains(@id, 'user')]")
                if username_fields and len(username_fields) > 0:
                    username_fields[0].clear()
                    username_fields[0].send_keys(username)

                # Find any password field
                password_fields = driver.find_elements(By.XPATH, "//input[@type='password']")
                if password_fields and len(password_fields) > 0:
                    password_fields[0].clear()
                    password_fields[0].send_keys(password)

                # Find submit/login button
                login_buttons = driver.find_elements(By.XPATH,
                    "//button[contains(., 'Log') or contains(., 'Sign') or contains(@type, 'submit')]")
                if not login_buttons:
                    # Try input submit buttons too
                    login_buttons = driver.find_elements(By.XPATH,
                        "//input[@type='submit' or contains(@value, 'Log') or contains(@value, 'Sign')]")

                if login_buttons and len(login_buttons) > 0:
                    # Use JavaScript for more reliable click
                    driver.execute_script("arguments[0].click();", login_buttons[0])
                    debug_print("Generic login button clicked via JavaScript")
            except Exception as inner_e:
                debug_print(f"Generic login attempt also failed: {inner_e}")
                pass

        # Wait for chat interface to load
        WebDriverWait(driver, max_wait_sec).until(
            EC.presence_of_element_located((By.NAME, "prompt"))
        )
        debug_print("Login successful - chat interface loaded")
        return True
    except Exception as e:
        sys.stderr.write(f"Login failed: {e}\n")

        # Check if we ended up on the chat interface despite errors
        try:
            if "spark.unimelb.edu.au/securechat" in driver.current_url:
                # # Take a screenshot for debugging
                # try:
                #     screenshot_path = f"/tmp/spark_login_result_{int(time.time())}.png"
                #     driver.save_screenshot(screenshot_path)
                #     debug_print(f"Debugging screenshot saved to {screenshot_path}")
                # except:
                #     pass

                # Check if prompt element exists despite error
                if driver.find_elements(By.NAME, "prompt"):
                    debug_print("Login appears successful despite errors")
                    return True
        except:
            pass

        return False

def handle_duo_authentication(driver, max_wait_sec=30):
    """
    Handle the Duo Security authentication page by selecting push notification if available.

    Parameters
    ----------
    driver : webdriver.Chrome
        Chrome WebDriver instance
    max_wait_sec : int
        Maximum wait time in seconds
    """
    try:
        # First check if we're already on an authentication page before waiting
        auth_elements = driver.find_elements(
            By.CLASS_NAME, "authenticator-verify-list"
        )

        # Only proceed with authentication if elements are already present
        if not auth_elements:
            # Quick check to see if authentication screen appears
            try:
                WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located(
                        (By.CLASS_NAME, "authenticator-verify-list")
                    )
                )
            except TimeoutException:
                # No authentication required, exit early
                return

        # At this point, we know authentication is needed
        debug_print("Duo authentication detected, attempting to handle...")

        # Try to find the "Get a push notification" button
        push_buttons = driver.find_elements(
            By.XPATH,
            "//h3[contains(text(), 'Get a push notification')]/../..//a[contains(@class, 'button')]",
        )

        if push_buttons:
            # Click the push notification button
            push_buttons[0].click()
            debug_print("Push notification requested, check your device")
        else:
            # If push notification not available, look for any authentication option
            auth_buttons = driver.find_elements(
                By.XPATH,
                "//div[contains(@class, 'authenticator-button')]//a[contains(@class, 'button')]",
            )

            if auth_buttons:
                auth_buttons[0].click()
                debug_print("Alternative authentication method selected")
            else:
                sys.stderr.write("No authentication methods found. Manual intervention may be required.\n")
                # Screenshot for debugging authentication issues
                try:
                    screenshot_path = f"/tmp/spark_duo_auth_{int(time.time())}.png"
                    driver.save_screenshot(screenshot_path)
                    debug_print(f"Authentication screenshot saved to {screenshot_path}")
                except:
                    pass
                return

        # Wait for authentication to complete by checking for prompt
        try:
            WebDriverWait(driver, max_wait_sec).until(
                EC.presence_of_element_located((By.NAME, "prompt"))
            )
            debug_print("Authentication completed successfully")
        except TimeoutException:
            sys.stderr.write("Authentication timed out waiting for completion.\n")

            # Check if we need to select a different auth method
            try:
                # Look for "Choose another way to verify" button
                other_method_buttons = driver.find_elements(
                    By.XPATH, "//a[contains(text(), 'Choose another') or contains(text(), 'different method')]"
                )
                if other_method_buttons:
                    other_method_buttons[0].click()
                    debug_print("Trying alternative authentication method")
                    time.sleep(2)

                    # Try to find other auth methods like "Text me new codes"
                    alt_auth_buttons = driver.find_elements(
                        By.XPATH, "//div[contains(@class, 'authenticator-button')]//a[contains(@class, 'button')]"
                    )
                    if alt_auth_buttons and len(alt_auth_buttons) > 1:
                        # Try second option
                        alt_auth_buttons[1].click()
                        debug_print("Selected secondary authentication method")

                        # Wait again for completion
                        WebDriverWait(driver, max_wait_sec).until(
                            EC.presence_of_element_located((By.NAME, "prompt"))
                        )
            except Exception as auth_e:
                debug_print(f"Error trying alternative authentication: {auth_e}")

    except Exception as e:
        sys.stderr.write(f"Error during authentication: {e}\n")

# def login_to_spark(driver, username, password, max_wait_sec=30):
#     """
#     Perform login to Spark AI

#     Parameters
#     ----------
#     driver : webdriver.Chrome
#         Chrome WebDriver instance
#     username : str
#         UoM SSO username
#     password : str
#         UoM SSO password
#     max_wait_sec : int
#         Maximum wait time in seconds

#     Returns
#     -------
#     bool
#         Whether login was successful
#     """
#     try:
#         # Navigate to SparkAI
#         driver.get("https://spark.unimelb.edu.au/securechat")

#         # Check if we're already on the messaging page
#         try:
#             # Use a shorter timeout just for checking if already logged in
#             WebDriverWait(driver, 5).until(
#                 EC.presence_of_element_located((By.NAME, "prompt"))
#             )
#             return True
#         except TimeoutException:
#             pass

#         # Wait for login form - username field
#         username_field = WebDriverWait(driver, max_wait_sec).until(
#             EC.presence_of_element_located((By.NAME, "identifier"))
#         )
#         username_field.clear()
#         username_field.send_keys(username)
#         time.sleep(0.5)

#         # Click the Next button
#         next_button = WebDriverWait(driver, max_wait_sec).until(
#             EC.element_to_be_clickable(
#                 (By.CSS_SELECTOR, "input.button-primary[value='Next']")
#             )
#         )
#         next_button.click()

#         # Wait for password field to appear
#         password_field = WebDriverWait(driver, max_wait_sec).until(
#             EC.presence_of_element_located(
#                 (By.NAME, "credentials.passcode")
#             )
#         )
#         password_field.clear()
#         password_field.send_keys(password)

#         # Click verify button
#         verify_button = WebDriverWait(driver, max_wait_sec).until(
#             EC.element_to_be_clickable(
#                 (By.CSS_SELECTOR, "input[type='submit'][value='Verify']")
#             )
#         )
#         verify_button.click()

#         # Handle authentication methods if they appear
#         handle_duo_authentication(driver, max_wait_sec)

#         # Wait for chat interface to load
#         WebDriverWait(driver, max_wait_sec).until(
#             EC.presence_of_element_located((By.NAME, "prompt"))
#         )

#         return True
#     except Exception as e:
#         sys.stderr.write(f"Login failed: {e}\n")
#         return False

# def handle_duo_authentication(driver, max_wait_sec=30):
#     """
#     Handle the Duo Security authentication page by selecting push notification if available.

#     Parameters
#     ----------
#     driver : webdriver.Chrome
#         Chrome WebDriver instance
#     max_wait_sec : int
#         Maximum wait time in seconds
#     """
#     try:
#         # First check if we're already on an authentication page before waiting
#         auth_elements = driver.find_elements(
#             By.CLASS_NAME, "authenticator-verify-list"
#         )

#         # Only proceed with authentication if elements are already present
#         if not auth_elements:
#             # Quick check to see if authentication screen appears
#             try:
#                 WebDriverWait(driver, 3).until(
#                     EC.presence_of_element_located(
#                         (By.CLASS_NAME, "authenticator-verify-list")
#                     )
#                 )
#             except TimeoutException:
#                 # No authentication required, exit early
#                 return

#         # At this point, we know authentication is needed
#         # Try to find the "Get a push notification" button
#         push_buttons = driver.find_elements(
#             By.XPATH,
#             "//h3[contains(text(), 'Get a push notification')]/../..//a[contains(@class, 'button')]",
#         )

#         if push_buttons:
#             # Click the push notification button
#             push_buttons[0].click()
#         else:
#             # If push notification not available, look for any authentication option
#             auth_buttons = driver.find_elements(
#                 By.XPATH,
#                 "//div[contains(@class, 'authenticator-button')]//a[contains(@class, 'button')]",
#             )
#             if auth_buttons:
#                 auth_buttons[0].click()
#             else:
#                 sys.stderr.write("No authentication methods found. Manual intervention may be required.\n")
#                 return

#         # Wait for authentication to complete by checking for prompt
#         try:
#             WebDriverWait(driver, max_wait_sec).until(
#                 EC.presence_of_element_located((By.NAME, "prompt"))
#             )
#         except TimeoutException:
#             sys.stderr.write("Authentication timed out waiting for completion.\n")
#     except Exception as e:
#         sys.stderr.write(f"Error during authentication: {e}\n")

# EOF