#!/usr/bin/env python3
"""
COCO - Conversation Coach Backend
Main entry point for the application
"""

import uvicorn
from app.main import app
from app.config import settings


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        log_level="info"
    )
