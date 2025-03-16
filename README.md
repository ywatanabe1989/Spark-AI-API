<!-- ---
!-- Timestamp: 2025-03-16 07:52:43
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
sparkai "Your question here"

# With a specific thread ID
sparkai --thread-id=123456 "Your question here"

# Read from a file and write to a file
sparkai --input-file=input.txt --output-file=output.txt

# Keep the browser window open
sparkai --no-headless --keep-open "Your question here"
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

### API Service

```bash
# Start the API service
sparkai-service --port=5000

# Then make requests:
curl -X POST http://localhost:5000/api/query \
     -H "Content-Type: application/json" \
     -d '{"message":"Your question here"}'
```

## Environment Variables

- `SPARKAI_USERNAME`: Your UoM SSO username
- `SPARKAI_PASSWORD`: Your UoM SSO password
- `SPARKAI_THREAD_ID`: Thread ID to resume a conversation
- `SPARKAI_COOKIE_FILE`: Path to save/load session cookies
- `SPARKAI_SESSION_ID`: Session ID for browser reuse

<!-- EOF -->