from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse, JSONResponse

app = FastAPI()

HERE = Path(__file__).resolve().parent
INPUT_DIR = HERE / "incoming"
OUTPUT_DIR = HERE / "output"


@app.get("/")
def root():
    return {"status": "ok", "service": "vattenrapport"}


@app.post("/generate-report")
async def generate_report(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Filen måste vara en PDF.")

    INPUT_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)

    job_id = uuid4().hex
    input_pdf = INPUT_DIR / f"{job_id}_{file.filename}"

    with input_pdf.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    result = subprocess.run(
        [sys.executable, str(HERE / "run_water_report_pipeline.py"), str(input_pdf)],
        cwd=HERE,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": "Rapportgenerering misslyckades.",
                "stdout": result.stdout,
                "stderr": result.stderr,
            },
        )

    run_dirs = sorted(
        OUTPUT_DIR.iterdir(),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    if not run_dirs:
        raise HTTPException(status_code=500, detail="Ingen output-mapp skapades.")

    latest_run = run_dirs[0]
    report_pdf = latest_run / "report_v3.pdf"
    report_model = latest_run / "report_model_v3.json"

    if not report_pdf.exists():
        raise HTTPException(status_code=500, detail="Rapport-PDF skapades inte.")

    headers = {}

    if report_model.exists():
        try:
            data = json.loads(report_model.read_text(encoding="utf-8"))
            headers["X-Quality-Status"] = str(data.get("quality_status", "unknown"))
            headers["X-Quality-Issues"] = json.dumps(
                data.get("quality_issues", []),
                ensure_ascii=False,
            )
        except Exception:
            headers["X-Quality-Status"] = "unknown"
            headers["X-Quality-Issues"] = "[]"

    return FileResponse(
        path=report_pdf,
        media_type="application/pdf",
        filename="personlig_vattenrapport.pdf",
        headers=headers,
    )
