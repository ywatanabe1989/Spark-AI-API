<!-- ---
!-- Timestamp: 2025-03-28 09:36:30
!-- Author: ywatanabe
!-- File: /home/ywatanabe/proj/spark-ai-api/README.md
!-- --- -->

# /home/ywatanabe/proj/spark-ai-api/README.md
# Spark AI API

A Python client for the University of Melbourne's Spark AI chat system.

## Installation

```bash
pip install sparkai
```

## Usage

### Command Line

```bash
# Basic usage
sparkai "Hi" --force-new-browser --force-new-window
sparkai "Your question here"
sparkai -i /path/to/input/text/file.txt
```

### As a Library

```python
from sparkai import SparkAI

# Create a client
client = SparkAI(
    username="your_username",
    password="your_password",
    auto_login=True,
    headless=False
)

# Send a message and get the response
response = client.send_message("What is the meaning of life?")
print(response)

# Close the browser when done
client.close()
```
## Environment Variables

- `SPARKAI_USERNAME`: Your UoM SSO username
- `SPARKAI_PASSWORD`: Your UoM SSO password
- `SPARKAI_THREAD_ID`: Thread ID to resume a conversation
- `SPARKAI_COOKIE_FILE`: Path to save/load session cookies
- `SPARKAI_SESSION_ID`: Session ID for browser reuse

## Contact
Yusuke Watanabe (Yusuke.Watanabe@unimelb.edu.au)

<!-- EOF -->