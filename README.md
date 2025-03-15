<!-- ---
!-- Timestamp: 2025-03-15 16:00:27
!-- Author: ywatanabe
!-- File: /home/ywatanabe/proj/SparkAI/README.md
!-- --- -->

# SparkAI API

Provides a Python interface for [SparkAI](https://spark.unimelb.edu.au/).

## Prerequisites

- Python 3.x
- Google Chrome browser installed
- Selenium Python package
- Valid UoM SSO credentials (with one-time security code) for SparkAI login

## Installation

``` shell
pip install -r requirements.txt
```

## Usage
1. Start the application:
```bash
./main.py 2>&1 | tee ./main.py.log
```
2. When the browser launches, log in to SparkAI using your UoM SSO credentials.
3. After logging in, return to the terminal and press Enter to continue.
4. Authorize any clipboard copy requests in Chrome as needed.
5. Enter your messages at the prompt. To exit, type "C-c", "quit" or "exit".

## Disclaimer
Confirm that this script complies with the Terms of Use and ethical guidelines.

## Contact
ywatanabe@unimelb.edu.au

<!-- EOF -->