#!/bin/bash
# -*- coding: utf-8 -*-
# Timestamp: "2025-03-15 23:54:05 (ywatanabe)"
# File: /home/ywatanabe/proj/spark-ai-api/main.sh

THIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_PATH="$0.log"
touch "$LOG_PATH"


INPUT_FILE=~/spark-ai-input.txt
echo "HELLO THIS IS MY MESSAGE

This is after empty line" > $INPUT_FILE

python ./main.py -i $INPUT_FILE 2>&1 | tee $LOG_PATH

# EOF