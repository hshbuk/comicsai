from typing import Any

from pydantic import BaseModel, Field


class PlanRequest(BaseModel):
    brief: str = Field(min_length=1, max_length=12000)
    pages: int = Field(default=1, ge=1, le=100)
    panels_per_page: int = Field(default=4, ge=1, le=16)
    style: str = Field(default="comic book illustration", max_length=500)
    color_mode: str = Field(default="color", pattern="^(color|bw)$")
    language: str = Field(default="he", pattern="^(he|en)$")


class Panel(BaseModel):
    id: str = ""
    number: int
    description: str
    prompt: str
    negative_prompt: str = "text, watermark, blurry, deformed hands"
    dialogue: list[str] = Field(default_factory=list)
    narration: str = ""
    speaker: str = ""
    shot_type: str = "full_body_action"
    critical: bool = False
    scene_views: list[str] = Field(default_factory=list, max_length=3)
    seed: int | None = None


class ReferenceAsset(BaseModel):
    id: str
    kind: str
    name: str
    description: str
    prompt: str
    image: str | None = None
    project_id: str | None = None
    created_at: str | None = None


class ComicPlan(BaseModel):
    title: str
    style: str
    characters: list[str] = Field(default_factory=list)
    panels: list[Panel]


class ComicPage(BaseModel):
    number: int
    title: str = ""
    summary: str = ""
    panels: list[Panel]


class BookPlan(BaseModel):
    title: str
    style: str
    language: str = "he"
    characters: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    assets: list[ReferenceAsset] = Field(default_factory=list)
    pages: list[ComicPage]


class GenerateRequest(PlanRequest):
    workflow: str = "single_panel_sdxl_api.json"
    seed: int | None = None
    plan: BookPlan | None = None


class RegeneratePanelRequest(BaseModel):
    project_id: str
    page_number: int
    panel_number: int
    view_index: int = 1
    prompt: str | None = None
    seed: int | None = None
    workflow: str = "single_panel_sdxl_api.json"


class ImportAssetRequest(BaseModel):
    project_id: str
    asset_id: str


class GenerateResponse(BaseModel):
    project_id: str
    plan: BookPlan
    images: list[str]
