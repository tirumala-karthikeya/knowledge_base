#!/usr/bin/env python
"""
Simple test runner script.
Run with: python run_tests.py
Or use pytest directly: pytest
"""
import subprocess
import sys

if __name__ == "__main__":
    # Run pytest with coverage
    result = subprocess.run(
        ["pytest", "-v", "--cov=app", "--cov-report=term-missing"],
        cwd=".",
    )
    sys.exit(result.returncode)

