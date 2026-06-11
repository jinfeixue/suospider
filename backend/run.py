#!/usr/bin/env python
"""Application entry point."""
import uvicorn
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    # Disable reload to prevent issues with script file changes
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Disable reload to prevent script file changes from restarting server
        log_level="info",
    )
