#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-03-16 13:42:57 (ywatanabe)"
# File: /home/ywatanabe/proj/spark-ai-api/src/sparkai/parse_args.py
# ----------------------------------------
import os
__FILE__ = (
    "/home/ywatanabe/proj/spark-ai-api/src/sparkai/parse_args.py"
)
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------

import sys
import argparse


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SparkAI CLI Interface")
    # Environment variables with fallbacks
    default_chat_id = os.environ.get("SPARKAI_CHAT_ID")
    # Convert "None" string to actual None
    if default_chat_id in ["None", "none", "null", ""]:
        default_chat_id = None
    default_chrome_profile = os.environ.get("SPARKAI_CHROME_PROFILE")
    default_timeout = int(os.environ.get("SPARKAI_TIMEOUT", "5"))
    default_response_timeout = int(os.environ.get("SPARKAI_RESPONSE_TIMEOUT", "120"))
    default_username = os.environ.get("SPARKAI_USERNAME")
    default_password = os.environ.get("SPARKAI_PASSWORD")
    default_cookie_file = os.environ.get("SPARKAI_COOKIE_FILE")
    default_browser_id = os.environ.get("SPARKAI_BROWSER_ID")

    parser.add_argument(
        "--chat-id",
        type=str,
        default=default_chat_id,
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
        help="Maximum wait time in seconds for general operations (default: %(default)s)",
    )
    parser.add_argument(
        "--response-timeout",
        type=int,
        default=default_response_timeout,
        help="Maximum wait time in seconds for LLM response (default: %(default)s)",
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
        "--headless",
        action="store_true",
        default=os.environ.get("SPARKAI_HEADLESS", "").lower()
        in ("true", "yes", "1"),
        help="Hide Chrome browser window",
    )
    parser.add_argument(
        "--no-persistent-profile",
        action="store_true",
        default=os.environ.get("SPARKAI_NO_PERSISTENT_PROFILE", "").lower()
        in ("true", "yes", "1"),
        help="Don't maintain persistent browser profile",
    )
    parser.add_argument(
        "--browser-id",
        type=str,
        default=default_browser_id,
        help="Browser ID for browser reuse (can also use SPARKAI_BROWSER_ID env var)",
    )
    parser.add_argument(
        "--attach-only",
        action="store_true",
        default=os.environ.get("SPARKAI_ATTACH_ONLY", "").lower()
        in ("true", "yes", "1"),
        help="Only attach to an existing session without sending messages",
    )
    args = parser.parse_args()
    # Check if message is from stdin when not provided as argument
    if not args.message and not sys.stdin.isatty():
        args.message = sys.stdin.read().strip()
    return args

# EOF