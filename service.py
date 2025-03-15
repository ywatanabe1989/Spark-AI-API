#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-03-16 01:50:51 (ywatanabe)"
# File: /home/ywatanabe/proj/spark-ai-api/service.py
# ----------------------------------------
import os
__FILE__ = (
    "/home/ywatanabe/proj/spark-ai-api/service.py"
)
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------

# Web service wrapper for SparkAI API

import argparse
import sys
import json
import uuid
import tempfile
import subprocess
import shutil
from flask import Flask, request, jsonify
import socket
import psutil

app = Flask(__name__)


@app.route("/api/query", methods=["POST"])
def handle_query():
    # Create unique temp directory for this request
    temp_dir = tempfile.mkdtemp(prefix="sparkai_")
    chrome_profile_dir = os.path.join(temp_dir, "chrome_profile")
    os.makedirs(chrome_profile_dir, exist_ok=True)
    temp_in_path = os.path.join(temp_dir, "input.txt")
    temp_out_path = os.path.join(temp_dir, "output.txt")
    try:
        # Get request data
        data = request.get_json()
        if not data or "message" not in data:
            return jsonify({"error": "No message provided"}), 400
        message = data.get("message", "")
        thread_id = data.get("thread_id", None)
        keep_open = data.get("keep_open", False)
        no_headless = data.get("no-headless", False)
        # Write message to input file
        with open(temp_in_path, "w", encoding="utf-8") as f:
            f.write(message)
        # Build command with explicit arguments to avoid confusion
        cmd = [
            sys.executable,
            os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "main.py"
            ),
            "--input-file",
            temp_in_path,
            "--output-file",
            temp_out_path,
            "--chrome-profile",
            chrome_profile_dir,
        ]
        # Add thread_id if provided and not "None"
        if thread_id and thread_id.lower() != "none":
            cmd.extend(["--thread-id", thread_id])
        # Add keep-open flag if requested
        if no_headless:
            cmd.append("--no-headless")
        # Add keep-open flag if requested
        if keep_open:
            cmd.append("--keep-open")
        # Execute command
        result = subprocess.run(cmd, capture_output=True, text=True)
        # Read response from output file
        response = "Error reading response file"
        if os.path.exists(temp_out_path):
            try:
                with open(temp_out_path, "r", encoding="utf-8") as f:
                    response = f.read()
            except Exception as e:
                response = f"Error reading response file: {str(e)}"
        # Return response
        return jsonify(
            {
                "response": response,
                "status": "success" if result.returncode == 0 else "error",
                "error": result.stderr if result.stderr else None,
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        # Clean up temp directory
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except:
            pass


def is_port_in_use(port, host="localhost"):
    """Check if a port is in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return False
        except socket.error:
            return True


def find_process_by_port(port):
    """Find process using the specified port."""
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            for conn in proc.connections(kind="inet"):
                if conn.laddr.port == port:
                    return proc
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            pass
    return None


def kill_process_on_port(port, force=False):
    """Kill the process using the specified port."""
    process = find_process_by_port(port)
    if not process:
        print(f"No process found using port {port}")
        return False

    print(f"Found process {process.pid} ({process.name()}) using port {port}")

    try:
        if force:
            process.kill()
            print(f"Process {process.pid} forcefully terminated")
        else:
            process.terminate()
            print(f"Process {process.pid} gracefully terminated")

        # Wait for process to terminate
        gone, alive = psutil.wait_procs([process], timeout=3)
        if alive:
            print(f"Process {process.pid} is still alive, using SIGKILL")
            for p in alive:
                p.kill()

        return True
    except Exception as e:
        print(f"Error killing process: {e}")
        return False


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="SparkAI API Service")
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("SPARKAI_SERVICE_PORT", 5000)),
        help="Port to run the service on",
    )
    parser.add_argument(
        "--host",
        type=str,
        default=os.environ.get("SPARKAI_SERVICE_HOST", "0.0.0.0"),
        help="Host to bind the service to",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force kill any process using the specified port",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    port = args.port
    host = args.host

    # Check if port is in use and handle with --force if needed
    if is_port_in_use(port, host if host != "0.0.0.0" else "localhost"):
        print(f"Port {port} is already in use")
        if args.force:
            print(f"Attempting to kill process using port {port}")
            if kill_process_on_port(port, force=True):
                print(f"Successfully killed process using port {port}")
            else:
                print(f"Failed to kill process. Exiting.")
                sys.exit(1)
        else:
            print("Use --force to kill the process using this port")
            sys.exit(1)

    print(
        r"""Usage:
curl -X POST http://localhost:5000/api/query \
-H "Content-Type: application/json" \
-d '{"message":"Your question here",
"thread_id":"None",
"no_headless": true,
"keep_open": true
}'
"""
    )
    print(f"Starting SparkAI API service on {host}:{port}")
    app.run(host=host, port=port)

# EOF