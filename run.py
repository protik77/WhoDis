#!/usr/bin/env python3
"""Entry point for running WhoDis directly."""

import sys
import os

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from whodis.main import app
import uvicorn

def main():
    uvicorn.run(
        "whodis.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )

if __name__ == "__main__":
    main()
