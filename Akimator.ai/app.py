"""FastAPI entry point for Akim AI."""

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path

from simulation import load_city_data, run_simulation

ROOT = Path(__file__).parent
STATIC = ROOT / "static"

app = FastAPI(title="Akim AI", version="0.1.0")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


class SimulateRequest(BaseModel):
    decisions: dict[str, str]


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/api/city")
def city_config() -> dict:
    data = load_city_data()
    return {
        "city": data["city"],
        "budget_total": data["budget_total"],
        "baseline": data["baseline"],
        "categories": data["categories"],
    }


@app.post("/api/simulate")
def simulate(payload: SimulateRequest) -> dict:
    try:
        return run_simulation(payload.decisions)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
