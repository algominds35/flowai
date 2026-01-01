#!/usr/bin/env python3
"""Startup script for Railway deployment"""
import os
import sys

# Get PORT from environment, default to 8000
port = int(os.getenv("PORT", "8000"))

print(f"Starting uvicorn on port {port}...")

# Start uvicorn programmatically
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
