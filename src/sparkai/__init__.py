#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Timestamp: "2025-03-16 09:37:21 (ywatanabe)"
# File: /home/ywatanabe/proj/spark-ai-api/src/sparkai/__init__.py
# ----------------------------------------
import os
__FILE__ = (
    "/home/ywatanabe/proj/spark-ai-api/src/sparkai/__init__.py"
)
__DIR__ = os.path.dirname(__FILE__)
# ----------------------------------------

"""
SparkAI API Client

This package provides tools to interact with the Spark AI system.
"""

from . import SparkAI
from . import ChromeManager
from . import client
from . import auth_utils


__version__ = "0.1.0"

__copyright__ = "Copyright (C) 2025 Yusuke Watanabe"
__version__ = "0.1.0"
__license__ = "MIT"
__author__ = "Yusuke Watanabe"
__author_email__ = "ywatanabe@alumni.u-tokyo.ac.jp"
__url__ = "https://github.com/ywatanabe1989/spark"

# EOF