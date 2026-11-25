from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import OUTPUT_DIR, WORKFLOW_DIR
from .models import BookPlan, GenerateRequest, ImportAssetRequest, PlanRequest, RegeneratePanelRequest
from .llm_client import create_plan
from .service import (
    export_project,
    generate_comic,
    get_job,
    import_asset_to_project,
    list_global_assets,
    list_projects,
    list_workflows,
    load_project,
    load_workflow,
    regenerate_single_panel,
    save_project_plan,
    start_generation,
)
from .comfyui_client import diagnose_workflow, validate_workflow
from .reader_api import router as reader_router

app = FastAPI(title="Comics AI", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://127.0.0.1:8000", "http://localhost:8000"], allow_methods=["*"], allow_headers=["*"])
app.mount("/outputs", StaticFiles(directory=OUTPUT_DIR), name="outputs")
app.include_router(reader_router)


@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(Path(__file__).parent.parent / "static" / "index.html")


@app.get("/api/health")
async def health():
    return {"ok": True, "workflows": list_workflows()}


@app.get("/api/workflows")
async def workflows():
    return {"workflows": list_workflows()}


@app.get("/api/workflows/{name}/validate")
async def validate(name: str):
    try:
        workflow = load_workflow(name)
        result = await diagnose_workflow(workflow)
        result["nodes"] = len(workflow)
        return result
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(404, str(exc)) from exc


@app.post("/api/workflows/upload")
async def upload_workflow(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".json"):
        raise HTTPException(400, "Workflow must be a .json file")
    safe_name = Path(file.filename).name
    try:
        import json
        data = json.loads(await file.read())
        if not isinstance(data, dict):
            raise ValueError("JSON root must be an object")
        (WORKFLOW_DIR / safe_name).write_text(json.dumps(data, indent=2), encoding="utf-8")
    except (ValueError, UnicodeDecodeError) as exc:
        raise HTTPException(400, f"Invalid workflow JSON: {exc}") from exc
    return {"name": safe_name}


@app.post("/api/plan")
async def plan(request: PlanRequest):
    return await create_plan(request)


@app.post("/api/generate")
async def generate(request: GenerateRequest):
    try:
        return await generate_comic(request)
    except FileNotFoundError:
        raise HTTPException(404, f"Workflow not found: {request.workflow}")
    except Exception as exc:
        raise HTTPException(502, f"Generation failed: {exc}") from exc


@app.post("/api/generate/start")
async def generate_start(request: GenerateRequest):
    try:
        return await start_generation(request)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(404, str(exc)) from exc


@app.get("/api/jobs/{job_id}")
async def job_status(job_id: str):
    try:
        return get_job(job_id)
    except FileNotFoundError:
        raise HTTPException(404, "Job not found")


@app.get("/api/projects")
async def projects():
    return {"projects": list_projects()}


@app.get("/api/projects/{project_id}")
async def project(project_id: str):
    try:
        return load_project(project_id)
    except FileNotFoundError:
        raise HTTPException(404, "Project not found")


@app.post("/api/projects/{project_id}/save")
async def save_project(project_id: str, plan: BookPlan):
    try:
        return save_project_plan(project_id, plan)
    except FileNotFoundError:
        raise HTTPException(404, "Project not found")


@app.get("/api/projects/{project_id}/export")
async def export(project_id: str, format: str = "zip"):
    try:
        path, media_type = export_project(project_id, format)
        return FileResponse(path, media_type=media_type, filename=path.name)
    except FileNotFoundError:
        raise HTTPException(404, "Project not found")
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/assets")
async def global_assets():
    return {"assets": list_global_assets()}


@app.post("/api/assets/import")
async def import_asset(request: ImportAssetRequest):
    try:
        return import_asset_to_project(request.project_id, request.asset_id)
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/generate/panel")
async def generate_panel(request: RegeneratePanelRequest):
    try:
        return await regenerate_single_panel(request)
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(502, f"Panel generation failed: {exc}") from exc
