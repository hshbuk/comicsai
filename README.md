**Language:** English | [עברית](README.he.md)

# Comics AI Studio

A local web application for generating AI comics: an **LLM** plans chapters, panels, and continuity assets; **ComfyUI** renders the illustrations; **Pillow + python-bidi** composite narration and dialogue bands outside the artwork (with full Hebrew RTL support); and a built-in **LANraragi-compatible API & OPDS 1.2 server** lets comic readers like **Tachiyomi / Mihon / Aniyomi** browse and read projects directly over your home network.

## Key Features

- **Hierarchical Story Planning**: Recursive chapter and plot-arc planning with unlimited chapters (`pages >= 1`) and panels per chapter (`panels_per_page >= 1`), supporting multiple `scene_views` per panel in English or Hebrew.
- **Project & Global Asset Bank**: Generates character and location reference images saved both per-project and in a shared global registry (`outputs/global_assets/`) for cross-comic reuse.
- **Single-Panel Regeneration**: Edit the story plan before or after generation and regenerate individual panels or views on demand.
- **Clean Text Compositing**: Adds a top narration strip and bottom dialogue bands outside the illustration with automatic RTL handling via `python-bidi`.
- **Multi-Format Export**: `CBZ` (with `ComicInfo.xml` and sequential `0001.png` numbering), `ZIP`, `JSON`, and `Markdown`.
- **Home-Network Reader Server**: Built-in **LANraragi API** and **OPDS 1.2** catalog for Tachiyomi / Mihon / Aniyomi.

## Quick Start

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000` in your browser, or launch [`ComicsAI.bat`](ComicsAI.bat) for the interactive control panel (manage the local server, configure local/remote LLM & ComfyUI endpoints, and view your LAN IP for Tachiyomi).

## Full Documentation (GitHub Wiki)

- [Wiki Home](https://github.com/hshbuk/comicsai/wiki)
- [Architecture & Pipeline](https://github.com/hshbuk/comicsai/wiki/Architecture)
- [Installation & Configuration](https://github.com/hshbuk/comicsai/wiki/Installation-and-Configuration)
- [ComfyUI Workflows](https://github.com/hshbuk/comicsai/wiki/ComfyUI-Workflows)
- [Reader Server (Tachiyomi & OPDS)](https://github.com/hshbuk/comicsai/wiki/Reader-Server-Tachiyomi-OPDS)
- [API Reference](https://github.com/hshbuk/comicsai/wiki/API-Reference)

## Tests

```powershell
python -m pytest -v
```
