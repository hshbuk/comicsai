import json
from pathlib import Path
from urllib.parse import quote
import xml.etree.ElementTree as ET

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, Response

from .config import OUTPUT_DIR
from .service import export_project, load_project

router = APIRouter(tags=["reader"])


def _project_image_paths(project_id: str) -> tuple[dict, list[Path]]:
    data = load_project(project_id)
    project_dir = (OUTPUT_DIR / Path(project_id).name).resolve()
    paths: list[Path] = []
    for url in data.get("images", []):
        candidate = project_dir / Path(url).name
        if candidate.exists() and candidate.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
            paths.append(candidate)
    return data, paths


def _archive_entry(project_id: str) -> dict | None:
    try:
        data, paths = _project_image_paths(project_id)
    except FileNotFoundError:
        return None
    if not paths:
        return None
    plan = data.get("plan", {})
    req = data.get("request", {})
    title = str(plan.get("title") or project_id)
    style = str(plan.get("style") or req.get("style") or "").strip()
    lang = str(plan.get("language") or req.get("language") or "").strip()
    tags = []
    if style:
        tags.append(f"style:{style}")
    if lang:
        tags.append(f"language:{lang}")
    tags.append("source:comics-ai")
    return {
        "arcid": project_id,
        "title": title,
        "tags": ", ".join(tags),
        "summary": str(req.get("brief") or ""),
        "isnew": "false",
        "extension": "cbz",
        "pagecount": len(paths),
        "progress": 0,
        "lastreadtime": 0,
    }


def _all_archive_entries() -> list[dict]:
    entries: list[dict] = []
    if not OUTPUT_DIR.exists():
        return entries
    for path in sorted(OUTPUT_DIR.iterdir(), reverse=True):
        if path.is_dir() and (path / "project.json").exists():
            entry = _archive_entry(path.name)
            if entry is not None:
                entries.append(entry)
    return entries


@router.get("/api/info")
async def lanraragi_info():
    """LANraragi-compatible server info endpoint for Tachiyomi/Mihon/Aniyomi."""
    return {
        "name": "Comics AI Studio",
        "motd": "Comics AI Local Library",
        "version": "0.9.4",
        "version_name": "Comics AI",
        "has_password": "0",
        "nofun_mode": "0",
        "archives_per_page": 100,
    }


@router.get("/api/categories")
async def lanraragi_categories():
    return []


@router.get("/api/archives")
async def lanraragi_archives():
    return _all_archive_entries()


@router.get("/api/search")
async def lanraragi_search(
    filter: str = Query(default=""),
    start: int = Query(default=0, ge=0),
    sortby: str = Query(default="title"),
    order: str = Query(default="asc"),
):
    entries = _all_archive_entries()
    total = len(entries)
    if filter.strip():
        needle = filter.strip().lower()
        entries = [
            e for e in entries
            if needle in e["title"].lower() or needle in e["tags"].lower() or needle in e["summary"].lower()
        ]
    reverse = order.lower() == "desc"
    if sortby == "title":
        entries.sort(key=lambda e: e["title"].lower(), reverse=reverse)
    filtered = len(entries)
    page_items = entries[start:start + 100]
    return {
        "data": page_items,
        "draw": 0,
        "recordsFiltered": filtered,
        "recordsTotal": total,
    }


@router.get("/api/search/random")
async def lanraragi_search_random(count: int = Query(default=5, ge=1, le=50)):
    entries = _all_archive_entries()[:count]
    return {"data": entries}


@router.get("/api/archives/{arcid}/metadata")
async def lanraragi_metadata(arcid: str):
    entry = _archive_entry(arcid)
    if entry is None:
        raise HTTPException(404, "Archive not found")
    return entry


@router.get("/api/archives/{arcid}/thumbnail")
async def lanraragi_thumbnail(arcid: str):
    try:
        _, paths = _project_image_paths(arcid)
    except FileNotFoundError:
        raise HTTPException(404, "Archive not found")
    if not paths:
        raise HTTPException(404, "No pages in archive")
    return FileResponse(paths[0])


@router.get("/api/archives/{arcid}/files")
async def lanraragi_files(arcid: str):
    try:
        _, paths = _project_image_paths(arcid)
    except FileNotFoundError:
        raise HTTPException(404, "Archive not found")
    pages = [f"/api/archives/{quote(arcid, safe='')}/page?path={quote(p.name, safe='')}" for p in paths]
    return {"pages": pages, "job": 0}


@router.get("/api/archives/{arcid}/page")
async def lanraragi_page(arcid: str, path: str = Query(...)):
    try:
        _, paths = _project_image_paths(arcid)
    except FileNotFoundError:
        raise HTTPException(404, "Archive not found")
    target_name = Path(path).name
    match = next((p for p in paths if p.name == target_name), None)
    if match is None:
        raise HTTPException(404, "Page not found")
    return FileResponse(match)


@router.get("/api/archives/{arcid}/download")
async def lanraragi_download(arcid: str):
    try:
        cbz_path, media_type = export_project(arcid, "cbz")
        return FileResponse(cbz_path, media_type=media_type, filename=cbz_path.name)
    except FileNotFoundError:
        raise HTTPException(404, "Archive not found")
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/opds")
async def opds_catalog():
    """OPDS 1.2 acquisition feed for comic readers supporting OPDS."""
    entries = _all_archive_entries()
    feed = ET.Element("feed", {
        "xmlns": "http://www.w3.org/2005/Atom",
        "xmlns:opds": "http://opds-spec.org/2010/catalog",
    })
    ET.SubElement(feed, "id").text = "urn:comics-ai:catalog"
    ET.SubElement(feed, "title").text = "Comics AI Studio Library"
    ET.SubElement(feed, "link", {
        "rel": "self",
        "href": "/opds",
        "type": "application/atom+xml;profile=opds-catalog;kind=acquisition",
    })

    for item in entries:
        arcid = item["arcid"]
        encoded_id = quote(arcid, safe="")
        entry = ET.SubElement(feed, "entry")
        ET.SubElement(entry, "id").text = f"urn:comics-ai:project:{arcid}"
        ET.SubElement(entry, "title").text = item["title"]
        ET.SubElement(entry, "summary", {"type": "text"}).text = item["summary"]
        ET.SubElement(entry, "link", {
            "rel": "http://opds-spec.org/image/thumbnail",
            "href": f"/api/archives/{encoded_id}/thumbnail",
            "type": "image/png",
        })
        ET.SubElement(entry, "link", {
            "rel": "http://opds-spec.org/acquisition",
            "href": f"/api/projects/{encoded_id}/export?format=cbz",
            "type": "application/vnd.comicbook+zip",
        })

    xml_bytes = ET.tostring(feed, encoding="utf-8", xml_declaration=True)
    return Response(content=xml_bytes, media_type="application/atom+xml;profile=opds-catalog;kind=acquisition")
