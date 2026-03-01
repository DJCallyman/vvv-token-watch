#!/usr/bin/env python
"""
Test runner script for VVV Token Watch.
Provides a convenient way to run the test suite with various options.
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path


def run_tests(args):
    """Run the test suite with specified options."""
    
    # Change to tests directory
    tests_dir = Path(__file__).parent / "tests"
    os.chdir(tests_dir)
    
    # Build pytest command
    cmd = ["python", "-m", "pytest"]
    
    # Add test directory
    cmd.append(".")
    
    # Add verbosity
    if args.verbose:
        cmd.append("-v")
    
    # Add coverage
    if args.coverage:
        cmd.extend(["--cov=../src", "--cov-report=html", "--cov-report=term"])
    
    # Add specific test file if specified
    if args.test_file:
        cmd.append(args.test_file)
    
    # Add markers if specified
    if args.markers:
        cmd.extend(["-m", args.markers])
    
    # Run tests
    print(f"Running: {' '.join(cmd)}")
    print("=" * 60)
    
    result = subprocess.run(cmd)
    
    return result.returncode


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run VVV Token Watch test suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    Run all tests
  %(prog)s -v                 Run with verbose output
  %(prog)s -c                 Run with coverage report
  %(prog)s test_config.py     Run specific test file
  %(prog)s -m "not slow"      Exclude slow tests
        """
    )
    
    parser.add_argument(
        "test_file",
        nargs="?",
        help="Specific test file to run (e.g., test_config.py)"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    parser.add_argument(
        "-c", "--coverage",
        action="store_true",
        help="Generate coverage report"
    )
    
    parser.add_argument(
        "-m", "--markers",
        help="Run tests matching given marker expression"
    )
    
    parser.add_argument(
        "--install-deps",
        action="store_true",
        help="Install test dependencies"
    )
    
    args = parser.parse_args()
    
    # Install dependencies if requested
    if args.install_deps:
        print("Installing test dependencies...")
        deps = ["pytest", "pytest-cov", "pytest-qt", "pytest-mock"]
        subprocess.run([sys.executable, "-m", "pip", "install"] + deps)
        print("Dependencies installed!")
        return 0
    
    # Check if pytest is available
    try:
        import pytest
    except ImportError:
        print("Error: pytest is not installed.")
        print("Run with --install-deps to install test dependencies.")
        return 1
    
    # Run tests
    return run_tests(args)


if __name__ == "__main__":
    sys.exit(main())
