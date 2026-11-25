from pathlib import Path
import os

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def _url(name: str, default: str) -> str:
    return os.getenv(name, default).rstrip("/")


LLM_BASE_URL = _url("LLM_BASE_URL", "http://127.0.0.1:11434/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "local-model")
LLM_API_KEY = os.getenv("LLM_API_KEY", "local")
COMFYUI_BASE_URL = _url("COMFYUI_BASE_URL", "http://127.0.0.1:8188")
COMFYUI_TIMEOUT_SECONDS = float(os.getenv("COMFYUI_TIMEOUT_SECONDS", "300"))
OUTPUT_DIR = ROOT / os.getenv("OUTPUT_DIR", "outputs")
WORKFLOW_DIR = ROOT / os.getenv("WORKFLOW_DIR", "workflows")
GLOBAL_ASSETS_DIR = OUTPUT_DIR / "global_assets"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
WORKFLOW_DIR.mkdir(parents=True, exist_ok=True)
GLOBAL_ASSETS_DIR.mkdir(parents=True, exist_ok=True)
