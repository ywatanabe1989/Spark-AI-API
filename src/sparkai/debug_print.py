#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-03-16 11:25:23 (ywatanabe)"
# File: /home/ywatanabe/proj/spark-ai-api/src/sparkai/debug_print.py
# ----------------------------------------
import os
__FILE__ = (
    "/home/ywatanabe/proj/spark-ai-api/src/sparkai/debug_print.py"
)
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------

def debug_print(message, is_debug_mode=False):
    is_debug_mode = is_debug_mode or os.environ.get("SPARKAI_DEBUG", "").lower() in ("true", "yes", "1")
    if is_debug_mode:
        print(f"[DEBUG]: {str(message)}")

# EOF