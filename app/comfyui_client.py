import asyncio
import copy
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import httpx

from .config import COMFYUI_BASE_URL, COMFYUI_TIMEOUT_SECONDS


def _replace(value: Any, prompt: str, negative: str, seed: int, reference_image: str | None = None) -> Any:
    if isinstance(value, dict):
        return {k: _replace(v, prompt, negative, seed, reference_image) for k, v in value.items()}
    if isinstance(value, list):
        return [_replace(v, prompt, negative, seed, reference_image) for v in value]
    if isinstance(value, str):
        if value == "__SEED__":
            return seed
        return value.replace("__PROMPT__", prompt).replace("__NEGATIVE_PROMPT__", negative).replace("__SEED__", str(seed)).replace("__REFERENCE_IMAGE__", reference_image or value)
    return value


def _comic_story(prompt: str, caption: str = "") -> str:
    """ComfyUI_sloppy-comic parses panel prompts only from {aspect, prompt} blocks."""
    clean = " ".join(prompt.replace("{", "").replace("}", "").split())
    text = caption.strip().replace("{", "").replace("}", "")
    return f"{text}\n{{vertical, {clean}}}" if text else f"{{vertical, {clean}}}"


def prepare_workflow(workflow: dict, prompt: str, negative: str, seed: int, caption: str = "", reference_image: str | None = None) -> dict:
    result = _replace(copy.deepcopy(workflow), prompt, negative, seed, reference_image)
    # Support both explicit placeholders and the custom Generate Comic node found in the supplied workflow.
    for node in result.values():
        if not isinstance(node, dict) or not isinstance(node.get("inputs"), dict):
            continue
        inputs = node["inputs"]
        if "story" in inputs and (not inputs["story"] or inputs["story"] == prompt):
            inputs["story"] = _comic_story(prompt, caption)
        if "add_to_positive" in inputs and not inputs["add_to_positive"]:
            inputs["add_to_positive"] = prompt
        if "add_to_negative" in inputs and not inputs["add_to_negative"]:
            inputs["add_to_negative"] = negative
        if "seed" in inputs and (inputs["seed"] in (0, "0", "__SEED__")):
            inputs["seed"] = seed
    return result


def validate_workflow(workflow: dict) -> list[str]:
    errors: list[str] = []
    if not isinstance(workflow, dict) or not workflow:
        return ["Workflow root must be a non-empty API-format object"]
    for node_id, node in workflow.items():
        if not isinstance(node, dict) or not node.get("class_type"):
            errors.append(f"Node {node_id} is missing class_type")
        elif not isinstance(node.get("inputs", {}), dict):
            errors.append(f"Node {node_id} inputs must be an object")
    return errors


async def generate_image(workflow: dict, prompt: str, negative: str, seed: int, caption: str = "", reference_bytes: bytes | None = None) -> bytes:
    async with httpx.AsyncClient(timeout=30) as client:
        reference_name = None
        if reference_bytes is not None and "__REFERENCE_IMAGE__" in json.dumps(workflow):
            upload = await client.post(f"{COMFYUI_BASE_URL}/upload/image", files={"image": ("comic_reference.png", reference_bytes, "image/png")}, data={"overwrite": "true"})
            upload.raise_for_status()
            reference_name = upload.json().get("name")
            if not reference_name:
                raise RuntimeError("ComfyUI did not return uploaded reference filename")
        prepared = prepare_workflow(workflow, prompt, negative, seed, caption, reference_name)
        response = await client.post(f"{COMFYUI_BASE_URL}/prompt", json={"prompt": prepared})
        response.raise_for_status()
        prompt_id = response.json().get("prompt_id")
        if not prompt_id:
            raise RuntimeError("ComfyUI did not return prompt_id")
        deadline = asyncio.get_running_loop().time() + COMFYUI_TIMEOUT_SECONDS
        while asyncio.get_running_loop().time() < deadline:
            history = await client.get(f"{COMFYUI_BASE_URL}/history/{prompt_id}")
            history.raise_for_status()
            item = history.json().get(prompt_id, {})
            if item.get("status", {}).get("status_str") == "error":
                details = json.dumps(item.get("status"), ensure_ascii=False)
                if "Fault failed" in details or "out of memory" in details.lower():
                    raise RuntimeError("ComfyUI ran out of GPU memory while loading SDXL + IPAdapter. The compact workflow or a ComfyUI restart is required.")
                raise RuntimeError(details)
            outputs = item.get("outputs", {})
            for node in outputs.values():
                for image in node.get("images", []):
                    query = urlencode({"filename": image["filename"], "subfolder": image.get("subfolder", ""), "type": image.get("type", "output")})
                    result = await client.get(f"{COMFYUI_BASE_URL}/view?{query}")
                    result.raise_for_status()
                    return result.content
            await asyncio.sleep(1)
    raise TimeoutError("ComfyUI generation timed out")


async def release_comfy_memory() -> None:
    """Ask ComfyUI to unload cached models before switching to the heavier IPAdapter graph."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(f"{COMFYUI_BASE_URL}/free", json={"unload_models": True, "free_memory": True})
            response.raise_for_status()
    except httpx.HTTPError:
        return


async def diagnose_workflow(workflow: dict) -> dict:
    errors = validate_workflow(workflow)
    result = {"valid": not errors, "errors": errors, "comfyui_reachable": False, "missing_nodes": []}
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            response = await client.get(f"{COMFYUI_BASE_URL}/object_info")
            response.raise_for_status()
            info = response.json()
        result["comfyui_reachable"] = True
        missing = [node.get("class_type") for node in workflow.values() if node.get("class_type") not in info]
        result["missing_nodes"] = sorted(set(missing))
        if missing:
            result["errors"].append("Missing ComfyUI nodes: " + ", ".join(sorted(set(missing))))
        result["valid"] = not result["errors"]
    except (httpx.HTTPError, ValueError):
        result["errors"].append("ComfyUI is not reachable at the configured address")
    return result
