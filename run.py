#!/usr/bin/env python3
"""
VVV Token Watch - Main entry point.

This is the main entry point for the VVV Token Watch application.
It launches the GUI application from the src module.
"""

import sys
import os

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import and run the main application
from src.main import main

if __name__ == '__main__':
    main()
