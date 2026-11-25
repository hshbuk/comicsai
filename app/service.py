import json
import asyncio
import re
import uuid
from datetime import datetime
from pathlib import Path

from .comfyui_client import generate_image, release_comfy_memory
from .config import GLOBAL_ASSETS_DIR, OUTPUT_DIR, WORKFLOW_DIR
from .llm_client import create_plan
from .models import GenerateRequest, GenerateResponse, ImportAssetRequest, RegeneratePanelRequest
from .text_overlay import compose_panel

JOBS: dict[str, dict] = {}

STYLE_PRESETS = {
    "japanese_manga": "Japanese manga sequential art, crisp black ink contours, clear panel-readable silhouettes, controlled screentone shading, expressive faces only when the story requires it, purposeful speed lines only during motion, grounded anatomy and readable staging",
    "american_comics": "American comic-book sequential art, confident ink contours, bold readable silhouettes, cinematic but controlled lighting, selective halftone texture, grounded anatomy, clear action choreography and professional comic storytelling",
    "realistic_comic": "realistic graphic-comic sequential art, natural human anatomy, believable materials and environments, crisp focused edges, cinematic lighting with clear value separation, restrained ink and paint texture, readable comic storytelling",
}


def _color_direction(color_mode: str) -> str:
    return (
        "full color comic palette, intentional color scripting, clean color separation, no muddy blur"
        if color_mode == "color"
        else "strict black and white comic art, pure black ink with white areas and controlled gray screentones, no color"
    )


def list_workflows() -> list[str]:
    return sorted(p.name for p in WORKFLOW_DIR.glob("*.json"))


def load_workflow(name: str) -> dict:
    candidate = (WORKFLOW_DIR / Path(name).name).resolve()
    if candidate.parent != WORKFLOW_DIR.resolve() or candidate.suffix.lower() != ".json":
        raise ValueError("Invalid workflow name")
    if not candidate.exists():
        raise FileNotFoundError(name)
    return json.loads(candidate.read_text(encoding="utf-8"))


def ensure_panel_workflow(workflow: dict) -> None:
    if any(isinstance(node, dict) and node.get("class_type") == "Generate Comic" for node in workflow.values()):
        raise ValueError("This workflow creates a complete comic page. Choose single_panel_sdxl_api.json for panel generation.")


async def generate_comic(request: GenerateRequest) -> GenerateResponse:
    plan = request.plan if request.plan is not None else await create_plan(request)
    workflow = load_workflow(request.workflow)
    ensure_panel_workflow(workflow)
    project_id = uuid.uuid4().hex
    project_dir = OUTPUT_DIR / project_id
    project_dir.mkdir(parents=True)
    (project_dir / "plan.json").write_text(plan.model_dump_json(indent=2), encoding="utf-8")
    images: list[str] = []
    index = 0
    for page in plan.pages:
        for panel in page.panels:
            for view_index, view in enumerate(panel.scene_views or [panel.prompt], start=1):
                index += 1
                seed = request.seed if request.seed is not None else (panel.seed + view_index - 1 if panel.seed is not None else 1000 + index)
                content = await generate_image(workflow, f"{_color_direction(request.color_mode)}; {view}", panel.negative_prompt, seed)
                content = compose_panel(content, panel.dialogue if view_index == 1 else [], panel.narration if view_index == 1 else "")
                filename = f"page-{page.number:03d}-panel-{panel.number:02d}-view-{view_index:02d}.png"
                (project_dir / filename).write_bytes(content)
                images.append(f"/outputs/{project_id}/{filename}")
    (project_dir / "project.json").write_text(json.dumps({"request": request.model_dump(), "plan": plan.model_dump(), "images": images}, ensure_ascii=False, indent=2), encoding="utf-8")
    return GenerateResponse(project_id=project_id, plan=plan, images=images)


def _project_slug(text: str) -> str:
    value = re.sub(r"[^\w\-]+", "-", text.strip(), flags=re.UNICODE).strip("-")[:70]
    return value or "comic-project"


def _persist_project(project_id: str, request: GenerateRequest, plan, images: list[str], status: str, error: str | None = None) -> None:
    project_dir = OUTPUT_DIR / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    data = {"project_id": project_id, "saved_at": datetime.now().isoformat(timespec="seconds"), "status": status, "request": request.model_dump(exclude={"plan"}), "plan": plan.model_dump(), "images": images}
    if error:
        data["error"] = error
    (project_dir / "project.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _reference_bytes(plan, panel=None) -> bytes | None:
    """Select the most relevant generated asset (matching English prompt terms or primary character)."""
    text = " ".join([getattr(panel, "description", ""), getattr(panel, "prompt", "")]).lower() if panel else ""
    mentioned = [
        asset for asset in plan.assets
        if asset.image and (
            asset.name.lower() in text
            or any(word in text for word in re.findall(r"[a-z]{4,}", asset.prompt.lower())[:4])
        )
    ]
    candidates = (
        mentioned
        or [asset for asset in plan.assets if asset.image and asset.kind == "character"]
        or [asset for asset in plan.assets if asset.image]
    )
    if not candidates:
        return None
    relative = candidates[0].image.removeprefix("/outputs/")
    path = OUTPUT_DIR / relative
    return path.read_bytes() if path.exists() else None


def _safe_visual_style(style: str) -> str:
    """Keep the requested look while removing layout words that trigger page synthesis."""
    style_key = style.strip()
    if style_key in STYLE_PRESETS:
        return f"{STYLE_PRESETS[style_key]}, detailed sequential-art finish"
    style = style_key
    cleaned = re.sub(r"\bgraphic\s+novel\b", "illustrated", style, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(comic|comics|comic-book|page|pages|panel|panels|webtoon|manga|storyboard|layout|sequential)\b", "illustrated", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.strip() or "graphic illustration"
    return f"{cleaned}, detailed cinematic comic illustration, realistic anatomy, natural proportions, textured environment, professional sequential-art finish"


def _compact_workflow(workflow: dict) -> dict:
    """Reduce the IPAdapter graph footprint for 6GB GPUs."""
    compact = json.loads(json.dumps(workflow))
    for node in compact.values():
        if not isinstance(node, dict):
            continue
        inputs = node.get("inputs", {})
        if node.get("class_type") == "EmptyLatentImage":
            inputs["width"] = min(int(inputs.get("width", 768)), 512)
            inputs["height"] = min(int(inputs.get("height", 768)), 512)
        if node.get("class_type") == "KSampler":
            inputs["steps"] = min(int(inputs.get("steps", 28)), 20)
            inputs["cfg"] = min(float(inputs.get("cfg", 6.5)), 6.0)
    return compact


async def _run_job(job_id: str, request: GenerateRequest, plan, project_id: str) -> None:
    job = JOBS[job_id]
    try:
        workflow = load_workflow(request.workflow)
        ensure_panel_workflow(workflow)
        uses_reference = "__REFERENCE_IMAGE__" in json.dumps(workflow)
        asset_workflow = _compact_workflow(load_workflow("single_panel_sdxl_api.json")) if uses_reference else workflow
        if uses_reference:
            await release_comfy_memory()
        index = 0
        assets_dir = OUTPUT_DIR / project_id / "assets"
        (assets_dir / "characters").mkdir(parents=True, exist_ok=True)
        (assets_dir / "locations").mkdir(parents=True, exist_ok=True)
        for asset_index, asset in enumerate(plan.assets, start=1):
            asset_prompt = f"{_color_direction(request.color_mode)}; {_safe_visual_style(request.style)}, {asset.prompt}; this is a reusable continuity asset for the following story: {request.brief}; preserve identity and recurring visual facts, but do not invent unrelated characters or scenery; no speech bubbles, no text, no borders, no page layout, no collage"
            asset_image = await generate_image(asset_workflow, asset_prompt, "text, letters, glyphs, fake writing, words, speech bubble, comic page, border, watermark, logo, blurry, gibberish", 900000 + asset_index)
            asset_filename = f"{_project_slug(asset.name)}.png"
            asset_path = assets_dir / ("characters" if asset.kind == "character" else "locations") / asset_filename
            asset_path.write_bytes(asset_image)
            asset.image = f"/outputs/{project_id}/assets/{'characters' if asset.kind == 'character' else 'locations'}/{asset_filename}"
            
            # Save to global assets library for cross-comic reuse
            global_cat_dir = GLOBAL_ASSETS_DIR / ("characters" if asset.kind == "character" else "locations")
            global_cat_dir.mkdir(parents=True, exist_ok=True)
            (global_cat_dir / asset_filename).write_bytes(asset_image)
            _save_asset_metadata(asset, project_id)

            job["assets"].append(asset.model_dump())
            job["plan"] = plan.model_dump()
            job["completed"] += 1
            job["current"] = {"phase": "asset", "asset": asset.name, "image": asset.image}
            _persist_project(project_id, request, plan, job["images"], "running")
        if uses_reference:
            await release_comfy_memory()
        for page in plan.pages:
            for panel in page.panels:
                views = panel.scene_views or [panel.prompt]
                for view_index, view in enumerate(views, start=1):
                    index += 1
                    seed = request.seed if request.seed is not None else (panel.seed + view_index - 1 if panel.seed is not None else 1000 + index)
                    clean_action = re.sub(r"[\u0590-\u05ff]+", "", view).strip(" ,;")
                    char_visuals = ", ".join(
                        re.sub(r"[\u0590-\u05ff]+", "", a.prompt).split(",")[0].strip()
                        for a in plan.assets if a.kind == "character"
                    )
                    prompt = (
                        f"{clean_action}, {char_visuals}, "
                        f"{_safe_visual_style(request.style)}, {_color_direction(request.color_mode)}, "
                        "single comic panel, dynamic sequential storytelling, no text, no speech bubbles"
                    )
                    portrait_negative = "" if panel.critical else ", portrait, headshot, bust shot, passport photo, centered face"
                    negative = f"{panel.negative_prompt}, text, letters, glyphs, fake writing, words, captions, labels, logos, watermark, gibberish, speech bubbles, dialogue balloons, comic page, multi-panel, collage, grid, panel borders, white margins, layout, split face, duplicated face, double face, side-by-side face, triptych, multiple views, composite image, chibi, toy-like, plastic, 3d render, flat vector, childish cartoon, painterly blur, out of focus, abstract art, unrelated portrait{portrait_negative}"
                    try:
                        content = await generate_image(workflow, prompt, negative, seed, reference_bytes=_reference_bytes(plan, panel))
                    except RuntimeError as exc:
                        if not uses_reference or "GPU memory" not in str(exc):
                            raise
                        await release_comfy_memory()
                        content = await generate_image(_compact_workflow(load_workflow("single_panel_sdxl_api.json")), prompt, negative, seed)
                    # Put the scene's text on the first view only; never duplicate it on every shot.
                    content = compose_panel(content, panel.dialogue if view_index == 1 else [], panel.narration if view_index == 1 else "")
                    filename = f"page-{page.number:03d}-panel-{panel.number:02d}-view-{view_index:02d}.png"
                    (OUTPUT_DIR / project_id / filename).write_bytes(content)
                    image_url = f"/outputs/{project_id}/{filename}"
                    job["images"].append(image_url)
                    job["completed"] += 1
                    job["current"] = {"phase": "panel", "page": page.number, "panel": panel.number, "view": view_index, "image": image_url}
                    _persist_project(project_id, request, plan, job["images"], "running")
        job["status"] = "completed"
        _persist_project(project_id, request, plan, job["images"], "completed")
    except Exception as exc:
        job["status"] = "failed"
        detail = f"{type(exc).__name__}: {exc!r}"
        job["error"] = detail
        _persist_project(project_id, request, plan, job["images"], "failed", detail)


async def start_generation(request: GenerateRequest) -> dict:
    plan = request.plan if request.plan is not None else await create_plan(request)
    first_prompt = request.brief or plan.pages[0].panels[0].prompt
    project_id = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{_project_slug(first_prompt)}-{uuid.uuid4().hex[:6]}"
    (OUTPUT_DIR / project_id).mkdir(parents=True, exist_ok=True)
    job_id = uuid.uuid4().hex
    total = len(plan.assets) + sum(len(panel.scene_views or [panel.prompt]) for page in plan.pages for panel in page.panels)
    JOBS[job_id] = {"job_id": job_id, "project_id": project_id, "status": "running", "total": total, "completed": 0, "images": [], "assets": [], "current": None, "plan": plan.model_dump(), "error": None}
    _persist_project(project_id, request, plan, [], "running")
    asyncio.create_task(_run_job(job_id, request, plan, project_id))
    return JOBS[job_id]


def get_job(job_id: str) -> dict:
    if job_id not in JOBS:
        raise FileNotFoundError(job_id)
    return JOBS[job_id]


def list_projects() -> list[dict]:
    projects = []
    for path in sorted(OUTPUT_DIR.iterdir(), reverse=True):
        project_file = path / "project.json"
        if path.is_dir() and project_file.exists():
            try:
                data = json.loads(project_file.read_text(encoding="utf-8"))
                projects.append({"project_id": data.get("project_id", path.name), "title": data.get("plan", {}).get("title", path.name), "status": data.get("status"), "images": len(data.get("images", [])), "saved_at": data.get("saved_at")})
            except (OSError, json.JSONDecodeError):
                continue
    return projects


def load_project(project_id: str) -> dict:
    project_dir = (OUTPUT_DIR / Path(project_id).name).resolve()
    project_file = project_dir / "project.json"
    if project_dir.parent != OUTPUT_DIR.resolve() or not project_file.exists():
        raise FileNotFoundError(project_id)
    return json.loads(project_file.read_text(encoding="utf-8"))


def save_project_plan(project_id: str, plan) -> dict:
    data = load_project(project_id)
    data["plan"] = plan.model_dump()
    data["saved_at"] = datetime.now().isoformat(timespec="seconds")
    path = OUTPUT_DIR / Path(project_id).name / "project.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data


def export_project(project_id: str, kind: str) -> tuple[Path, str]:
    project_dir = (OUTPUT_DIR / Path(project_id).name).resolve()
    if project_dir.parent != OUTPUT_DIR.resolve() or not project_dir.exists():
        raise FileNotFoundError(project_id)
    if kind == "json":
        return project_dir / "project.json", "application/json"
    data = json.loads((project_dir / "project.json").read_text(encoding="utf-8"))
    image_paths = [project_dir / Path(url).name for url in data.get("images", [])]
    image_paths = [path for path in image_paths if path.exists() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}]
    if kind == "cbz":
        if not image_paths:
            raise ValueError("Project has no generated pages to export")
        import zipfile
        import xml.etree.ElementTree as ET
        target = project_dir / f"{_project_slug(data.get('plan', {}).get('title', project_dir.name))}.cbz"
        root = ET.Element("ComicInfo")
        ET.SubElement(root, "Title").text = str(data.get("plan", {}).get("title", project_dir.name))
        ET.SubElement(root, "Summary").text = str(data.get("request", {}).get("brief", ""))
        ET.SubElement(root, "Year").text = datetime.now().strftime("%Y")
        ET.SubElement(root, "PageCount").text = str(len(image_paths))
        metadata = ET.tostring(root, encoding="utf-8", xml_declaration=True)
        with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for index, image_path in enumerate(image_paths, start=1):
                suffix = image_path.suffix.lower()
                archive.write(image_path, f"{index:04d}{suffix}")
            archive.writestr("ComicInfo.xml", metadata)
        return target, "application/vnd.comicbook+zip"
    if kind == "markdown":
        lines = [f"# {data['plan']['title']}", "", f"Style: {data['plan']['style']}", ""]
        for page in data["plan"]["pages"]:
            lines += [f"## Page {page['number']}: {page['title']}", page["summary"], ""]
            for panel in page["panels"]:
                lines += [f"### Panel {panel['number']}", panel["description"], f"Prompt: {panel['prompt']}", ""]
        target = project_dir / "script.md"
        target.write_text("\n".join(lines), encoding="utf-8")
        return target, "text/markdown"
    if kind == "zip":
        import shutil
        archive = shutil.make_archive(str(project_dir), "zip", project_dir)
        return Path(archive), "application/zip"
    raise ValueError("Unsupported export format")


def _save_asset_metadata(asset, project_id: str) -> None:
    registry_file = GLOBAL_ASSETS_DIR / "registry.json"
    registry = []
    if registry_file.exists():
        try:
            registry = json.loads(registry_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            registry = []
    
    # Check if asset already exists in registry
    existing = next((item for item in registry if item.get("id") == asset.id or (item.get("name") == asset.name and item.get("kind") == asset.kind)), None)
    entry = {
        "id": asset.id or uuid.uuid4().hex[:8],
        "kind": asset.kind,
        "name": asset.name,
        "description": asset.description,
        "prompt": asset.prompt,
        "image": f"/outputs/global_assets/{'characters' if asset.kind == 'character' else 'locations'}/{_project_slug(asset.name)}.png",
        "project_id": project_id,
        "created_at": datetime.now().isoformat(timespec="seconds")
    }
    if existing:
        registry.remove(existing)
    registry.append(entry)
    registry_file.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")


def list_global_assets() -> list[dict]:
    registry_file = GLOBAL_ASSETS_DIR / "registry.json"
    if not registry_file.exists():
        return []
    try:
        data = json.loads(registry_file.read_text(encoding="utf-8"))
        # Verify image file exists
        valid_assets = []
        for item in data:
            rel = item.get("image", "").removeprefix("/outputs/")
            if (OUTPUT_DIR / rel).exists():
                valid_assets.append(item)
        return valid_assets
    except (json.JSONDecodeError, OSError):
        return []


def import_asset_to_project(project_id: str, asset_id: str) -> dict:
    project = load_project(project_id)
    assets = list_global_assets()
    asset = next((a for a in assets if a.get("id") == asset_id), None)
    if not asset:
        raise FileNotFoundError(f"Asset with ID '{asset_id}' not found in global library")
    
    # Add to plan assets if not present
    plan_assets = project.get("plan", {}).get("assets", [])
    if not any(a.get("name") == asset["name"] for a in plan_assets):
        plan_assets.append(asset)
        project["plan"]["assets"] = plan_assets
        project_dir = OUTPUT_DIR / Path(project_id).name
        (project_dir / "project.json").write_text(json.dumps(project, ensure_ascii=False, indent=2), encoding="utf-8")
    return project


async def regenerate_single_panel(req: RegeneratePanelRequest) -> dict:
    project = load_project(req.project_id)
    plan = project.get("plan", {})
    workflow = load_workflow(req.workflow)
    ensure_panel_workflow(workflow)
    uses_reference = "__REFERENCE_IMAGE__" in json.dumps(workflow)

    # Find the target panel
    target_page = next((p for p in plan.get("pages", []) if p.get("number") == req.page_number), None)
    if not target_page:
        raise ValueError(f"Page {req.page_number} not found in project")
    target_panel = next((p for p in target_page.get("panels", []) if p.get("number") == req.panel_number), None)
    if not target_panel:
        raise ValueError(f"Panel {req.panel_number} not found on page {req.page_number}")

    views = target_panel.get("scene_views") or [target_panel.get("prompt")]
    view_idx = min(req.view_index, len(views))
    view = req.prompt or views[view_idx - 1]

    clean_action = re.sub(r"[\u0590-\u05ff]+", "", view).strip(" ,;")
    char_visuals = ", ".join(
        re.sub(r"[\u0590-\u05ff]+", "", a.get("prompt", "")).split(",")[0].strip()
        for a in plan.get("assets", []) if a.get("kind") == "character"
    )
    
    req_data = project.get("request", {})
    color_mode = req_data.get("color_mode", "color")
    style = req_data.get("style", "comic book illustration")
    
    prompt = (
        f"{clean_action}, {char_visuals}, "
        f"{_safe_visual_style(style)}, {_color_direction(color_mode)}, "
        "single comic panel, dynamic sequential storytelling, no text, no speech bubbles"
    )
    portrait_negative = "" if target_panel.get("critical") else ", portrait, headshot, bust shot, passport photo, centered face"
    neg = f"{target_panel.get('negative_prompt', '')}, text, letters, glyphs, fake writing, words, captions, labels, logos, watermark, gibberish, speech bubbles, dialogue balloons, comic page, multi-panel, collage, grid, panel borders, white margins, layout, split face, duplicated face, double face, side-by-side face, triptych, multiple views, composite image, chibi, toy-like, plastic, 3d render, flat vector, childish cartoon, painterly blur, out of focus, abstract art, unrelated portrait{portrait_negative}"

    seed = req.seed if req.seed is not None else (int(datetime.now().timestamp() * 1000) % 10000000)
    
    # Mock panel object for _reference_bytes
    class DummyPanel:
        description = target_panel.get("description", "")
        prompt = target_panel.get("prompt", "")
    
    class DummyPlan:
        assets = []
    
    from .models import ReferenceAsset
    dummy_plan = DummyPlan()
    dummy_plan.assets = [ReferenceAsset(**a) for a in plan.get("assets", [])]
    
    ref_bytes = _reference_bytes(dummy_plan, DummyPanel())

    if uses_reference:
        await release_comfy_memory()

    try:
        content = await generate_image(workflow, prompt, neg, seed, reference_bytes=ref_bytes)
    except RuntimeError as exc:
        if not uses_reference or "GPU memory" not in str(exc):
            raise
        await release_comfy_memory()
        content = await generate_image(_compact_workflow(load_workflow("single_panel_sdxl_api.json")), prompt, neg, seed)

    content = compose_panel(content, target_panel.get("dialogue") if view_idx == 1 else [], target_panel.get("narration") if view_idx == 1 else "")
    filename = f"page-{req.page_number:03d}-panel-{req.panel_number:02d}-view-{view_idx:02d}.png"
    out_path = OUTPUT_DIR / Path(req.project_id).name / filename
    out_path.write_bytes(content)

    img_url = f"/outputs/{Path(req.project_id).name}/{filename}"
    images = project.get("images", [])
    if img_url not in images:
        images.append(img_url)
        project["images"] = images
    
    project_dir = OUTPUT_DIR / Path(req.project_id).name
    (project_dir / "project.json").write_text(json.dumps(project, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "status": "success",
        "image": f"{img_url}?v={datetime.now().timestamp()}",
        "seed": seed,
        "page": req.page_number,
        "panel": req.panel_number,
        "view": view_idx
    }
