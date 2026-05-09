#!/usr/bin/env python3
"""Entry point for running WhoDis directly."""

import os
import sys

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn


def main() -> None:
    uvicorn.run(
        "whodis.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    main()
