#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-03-16 13:46:22 (ywatanabe)"
# File: /home/ywatanabe/proj/spark-ai-api/src/sparkai/client.py
# ----------------------------------------
import os
__FILE__ = (
    "/home/ywatanabe/proj/spark-ai-api/src/sparkai/client.py"
)
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------

import argparse
import sys
import time
import uuid
from .SparkAI import SparkAI
from .parse_args import parse_args
from .debug_print import debug_print



def main():
    """
    Main entry point for the SparkAI CLI
    """
    parser = argparse.ArgumentParser(description='Interact with SparkAI')
    parser.add_argument('message', nargs='*', help='Message to send to SparkAI')
    parser.add_argument('--chat-id', help='Specified chat ID to continue conversation')
    parser.add_argument('--no-auto-login', action='store_true', help='Disable auto-login attempt')
    parser.add_argument('--username', help='Username for auto-login')
    parser.add_argument('--password', help='Password for auto-login')
    parser.add_argument('--timeout', help='Response timeout in seconds')
    parser.add_argument('--headless', action='store_true', help='Run Chrome in headless mode')
    parser.add_argument('--visible', action='store_true', help='Run Chrome in visible mode (non-headless)')

    args = parser.parse_args()

    # If message was provided as multiple arguments, join them
    message = ' '.join(args.message) if args.message else None

    # Set environment variables from args if provided
    if args.chat_id:
        os.environ['SPARKAI_CHAT_ID'] = args.chat_id
    if args.username:
        os.environ['SPARKAI_USERNAME'] = args.username
    if args.password:
        os.environ['SPARKAI_PASSWORD'] = args.password
    if args.timeout:
        os.environ['SPARKAI_TIMEOUT'] = args.timeout

    # Determine headless mode - visible flag overrides headless flag
    headless = True  # Default to headless
    if args.visible:
        headless = False
    elif args.headless:
        headless = True

    # Check if we're in WSL and warn about potential display issues

    # Initialize the SparkAI client
    sparkai = SparkAI(headless=headless)

    # Only attempt auto-login when sending a message and not explicitly disabled
    username = os.environ.get('SPARKAI_USERNAME') or os.environ.get('SPARK_USERNAME')
    password = os.environ.get('SPARKAI_PASSWORD') or os.environ.get('SPARK_PASSWORD')

    if username and password and not args.no_auto_login:
        # Auto-login will happen automatically in send_message, no need for explicit call here
        debug_print(f"Auto-login credentials found for {username}")
    elif not args.no_auto_login:
        debug_print("No auto-login credentials found, manual login may be required")

    # Interactive mode if no message provided
    if not message:
        debug_print("SparkAI Interactive Mode (Ctrl+D or type 'exit' to quit)")
        try:
            while True:
                message = input("\n> ")
                if message.lower() in ['exit', 'quit']:
                    break
                response = sparkai.send_message(message)
                if response:
                    debug_print(f"\n{response}")
                else:
                    debug_print("\nNo response received")
        except (KeyboardInterrupt, EOFError):
            debug_print("\nExiting...")
        return

    # Send a single message and get response
    response = sparkai.send_message(message)
    if response:
        debug_print(response)
    else:
        sys.stderr.write("No response received\n")

if __name__ == "__main__":
    main()

# EOF