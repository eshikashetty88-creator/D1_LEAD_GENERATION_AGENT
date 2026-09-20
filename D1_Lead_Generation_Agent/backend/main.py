from fastapi import FastAPI
from agents.models import ICP
from agents.graph import run_pipeline

app = FastAPI(title="D1 Lead Generation Agent API", version="1.0")


@app.get("/")
def root():
    return {
        "message": "D1 Autonomous Lead Generation & Qualification Agent API",
        "docs": "/docs",
    }


@app.post("/generate")
def generate(icp: ICP):
    result = run_pipeline(icp)
    return result.model_dump()
