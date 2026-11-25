from app.comfyui_client import _comic_story, prepare_workflow
from app.models import Panel, PlanRequest


def test_plan_request_allows_large_values():
    req = PlanRequest(brief="x" * 15000, pages=150, panels_per_page=24, style="s" * 600)
    assert req.pages == 150
    assert req.panels_per_page == 24
    panel = Panel(number=1, description="d", prompt="p", scene_views=["v1", "v2", "v3", "v4"])
    assert len(panel.scene_views) == 4


def test_workflow_placeholders_are_replaced_recursively():
    workflow = {"node": {"inputs": {"text": "__PROMPT__", "seed": "__SEED__", "nested": ["__NEGATIVE_PROMPT__"]}}}
    result = prepare_workflow(workflow, "hero", "bad", 42)
    assert result["node"]["inputs"] == {"text": "hero", "seed": 42, "nested": ["bad"]}


def test_custom_comic_node_receives_story_and_seed():
    workflow = {"1": {"class_type": "Generate Comic", "inputs": {"story": "", "add_to_positive": "", "add_to_negative": "", "seed": 0}}}
    result = prepare_workflow(workflow, "story", "negative", 7)
    assert result["1"]["inputs"] == {"story": "{vertical, story}", "add_to_positive": "story", "add_to_negative": "negative", "seed": 7}


def test_comic_story_uses_required_panel_syntax():
    assert _comic_story("hero in a castle").startswith("{vertical, hero in a castle}")
