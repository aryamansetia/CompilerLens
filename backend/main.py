"""
CompilerLens backend entry point.

Run it with:
    uvicorn main:app --reload

Then open:
    http://127.0.0.1:8000        the built-in interface (no Node.js needed)
    http://127.0.0.1:8000/docs   interactive API documentation
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from api.routes import VERSION, router

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title="CompilerLens API",
    version=VERSION,
    description=(
        "An educational compiler that exposes its internal phases. "
        "All six educational compiler phases are implemented for the "
        "supported declaration-and-expression grammar."
    ),
)

# The React dev server runs on a different port, so the browser needs explicit
# permission to call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://compiler-lens.vercel.app",
],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

# Serve the dependency-free fallback interface straight from the backend.
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False, response_model=None)
def serve_interface() -> FileResponse | JSONResponse:
    """The built-in UI, so the project is demonstrable with Python alone."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return JSONResponse({"service": "CompilerLens API", "docs": "/docs"})
