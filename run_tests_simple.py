#!/usr/bin/env python
"""Simplified test runner to identify issues."""

import subprocess
import sys

def main():
    # Simple pytest command
    cmd = ["pytest", "tests/", "-v", "-m", "not integration and not slow", "--tb=short"]
    
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    
    return result.returncode

if __name__ == "__main__":
    sys.exit(main())