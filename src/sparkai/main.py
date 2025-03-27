#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-03-28 09:32:57 (ywatanabe)"
# File: /home/ywatanabe/proj/spark-ai-api/src/sparkai/main.py
# ----------------------------------------
import os
__FILE__ = (
    "/home/ywatanabe/proj/spark-ai-api/src/sparkai/main.py"
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
    args = parse_args()

    # If message was provided as multiple arguments, join them
    message = ' '.join(args.message) if args.message else None

    # If an input file was specified, read the message from it
    if args.input_file:
        try:
            with open(args.input_file, 'r') as f:
                file_content = f.read()
                if message:
                    message = message + ' ' + file_content
                else:
                    message = file_content
        except IOError as e:
            sys.stderr.write(f"Error reading input file: {e}\n")
            sys.exit(1)

    # Set environment variables from args if provided
    if args.chat_id:
        os.environ['SPARKAI_CHAT_ID'] = args.chat_id
    if args.username:
        os.environ['SPARKAI_USERNAME'] = args.username
    if args.password:
        os.environ['SPARKAI_PASSWORD'] = args.password
    if args.timeout:
        os.environ['SPARKAI_TIMEOUT'] = str(args.timeout)

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

    print(response)

if __name__ == "__main__":
    main()

# EOF