"""Bias Detection Dashboard — FastAPI server."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from core.analyzer import analyze_paper_streaming
from core.llm_client import MODEL_PRESETS, set_api_key

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="Financial LLM Bias Detection", version="0.1.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/models")
async def get_models():
    return MODEL_PRESETS


@app.post("/api/analyze")
async def analyze(
    file: UploadFile = File(...),
    model: str = Form(default="anthropic/claude-sonnet-4-6"),
    provider: str = Form(default="Anthropic"),
    api_key: str = Form(default=""),
    repo_url: str = Form(default=""),
):
    """Upload PDF, evaluate 12 checklist items, return report JSON."""
    if api_key:
        set_api_key(provider, api_key)
    pdf_bytes = await file.read()
    try:
        report_dict = None
        async for progress in analyze_paper_streaming(pdf_bytes, model, repo_url=repo_url or None):
            if "data" in progress and progress.get("event") == "report":
                report_dict = progress["data"]
        if not report_dict:
            raise Exception("Analysis completed without producing a report")
        return report_dict
    except Exception as e:
        err = str(e)
        if "429" in err or "rate_limit" in err.lower() or "quota" in err.lower():
            if "gemini" in model.lower():
                msg = (
                    "Gemini free tier quota exceeded (20 requests/day per model). "
                    "Each analysis uses 2 API calls. Options: "
                    "(1) Try a different Gemini model (e.g. gemini-2.5-pro has separate quota), "
                    "(2) Wait until tomorrow for quota reset, "
                    "(3) Enable billing at ai.google.dev for higher limits."
                )
            else:
                msg = f"Rate limit exceeded. Please wait a minute and try again. Details: {err[:200]}"
        elif "api_key" in err.lower() or "auth" in err.lower():
            msg = "Invalid or missing API key. Please check your key and try again."
        else:
            msg = err[:500]
        return JSONResponse(status_code=500, content={"error": msg, "type": type(e).__name__})


@app.post("/api/analyze/stream")
async def analyze_stream(
    file: UploadFile = File(...),
    model: str = Form(default="anthropic/claude-sonnet-4-6"),
    provider: str = Form(default="Anthropic"),
    api_key: str = Form(default=""),
    repo_url: str = Form(default=""),
):
    """Streaming analysis — sends SSE events for 3 steps."""
    if api_key:
        set_api_key(provider, api_key)
    pdf_bytes = await file.read()

    async def event_stream():
        try:
            async for progress in analyze_paper_streaming(pdf_bytes, model, repo_url=repo_url or None):
                yield f"data: {json.dumps(progress)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'event': 'error', 'error': str(e)[:500]})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
