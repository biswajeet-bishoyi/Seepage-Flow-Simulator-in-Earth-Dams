"""
FastAPI backend for the Seepage Flow Simulator.

Provides a REST API wrapping the engine for remote/frontend consumption.

Run: uvicorn ui.api.main:app --host 0.0.0.0 --port 8000 --reload
"""

import os
import sys
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ui.api.routes.solve import router as solve_router

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Seepage Flow Simulator API",
    description=(
        "REST API for 2D steady-state seepage analysis in earth dams. "
        "Solves the Laplace equation using FDM and computes safety metrics."
    ),
    version="1.0.0",
)

# CORS middleware for frontend access
cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(solve_router, prefix="/api")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "seepage-simulator"}
