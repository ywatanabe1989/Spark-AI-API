<!-- ---
!-- Timestamp: 2025-03-16 01:25:53
!-- Author: ywatanabe
!-- File: /home/ywatanabe/proj/spark-ai-api/README.md
!-- --- -->

# SparkAI API

This tool provides a command-line interface to interact with SparkAI using Selenium.

## Requirements

```
pip install -r requirements.txt
```

## Usage

Basic usage:
```
./main.py "Your message here"
```

Or using input/output files:
```
./main.py --input-file query.txt --output-file response.txt
```

## Web Service

Run as a service that accepts HTTP requests:
```
./service.py
```

This starts a server on port 5000 by default. Send queries using:
```
curl -X POST http://localhost:5000/api/query \
  -H "Content-Type: application/json" \
  -d '{"message":"Your question here", "thread_id":"None", "keep-open": true}'
```

Configure the service using environment variables:
- `SPARKAI_SERVICE_PORT`: Port to run the service (default: 5000)
- `SPARKAI_SERVICE_HOST`: Host interface to bind (default: 0.0.0.0)

## SSH Access

You can also access the service remotely via SSH:
```
ssh user@remote-server 'cd /path/to/spark-ai-api && ./main.py "Your question here"'
```

For file input/output over SSH:
```
cat query.txt | ssh user@remote-server 'cd /path/to/spark-ai-api && ./main.py' > response.txt
```

## Options

- `--thread-id`: Thread ID to resume a previous conversation
- `--chrome-profile`: Path to Chrome user data directory
- `--timeout`: Maximum wait time in seconds
- `--no-auto-login`: Not attempt automatic login with credentials
- `--username`: SSO username for auto-login
- `--password`: SSO password for auto-login
- `--cookie-file`: File to save/load session cookies
- `--parser-mode`: Use DOM parsing instead of clipboard for responses
- `--input-file`, `-i`: Read message from this file instead of command line
- `--output-file`, `-o`: Save response to this file
- `--no-headless`: Show Chrome browser window instead of running headless

## Environment Variables

All command-line options can be set using environment variables:
- `SPARKAI_THREAD_ID`
- `SPARKAI_CHROME_PROFILE`
- `SPARKAI_TIMEOUT` 
- `SPARKAI_NO_AUTO_LOGIN`
- `SPARKAI_USERNAME`
- `SPARKAI_PASSWORD`
- `SPARKAI_COOKIE_FILE`
- `SPARKAI_PARSER_MODE`
- `SPARKAI_INPUT_FILE`
- `SPARKAI_OUTPUT_FILE`
- `SPARKAI_NO_HEADLESS`

## Multi-line Input

Multi-line messages are supported, with newlines automatically handled as Shift+Enter in the SparkAI interface.

## Headless Mode

By default, the browser runs in headless mode. Use `--no-headless` to show the browser window.

## Contact

Yusuke Watanabe (Yusuke.Watanabe@unimelb.edu.au)

<!-- EOF -->