import json
import re

import httpx

from .config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
from .models import BookPlan, ComicPage, Panel, PlanRequest, ReferenceAsset

MAX_LEAF_CHAPTERS = 6
BRANCH_FACTOR = 6


def _extract_json(text: str) -> dict:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.I)
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("LLM did not return a JSON object")
    raw = cleaned[start:end + 1]
    raw = re.sub(r",\s*([}\]])", r"\1", raw)
    return json.loads(raw)


def _language_name(request: PlanRequest) -> str:
    return "Hebrew" if request.language == "he" else "English"


def _matches_language(text: str, request: PlanRequest) -> bool:
    has_hebrew = bool(re.search(r"[\u0590-\u05ff]", text or ""))
    has_latin_word = bool(re.search(r"[A-Za-z]{2,}", text or ""))
    return (has_hebrew and not has_latin_word) if request.language == "he" else (not has_hebrew)


def _normalize_asset(asset: ReferenceAsset) -> ReferenceAsset:
    """Create a clean, reusable identity/location reference in English for SDXL."""
    visual_desc = asset.prompt.strip() or asset.description.strip()
    if asset.kind == "character":
        asset.prompt = (
            f"full-body standing character design of {visual_desc}, three-quarter view, "
            "neutral pose, plain white background, clear outfit details, consistent face and hair, "
            "no text, no border, no collage"
        )
    else:
        asset.prompt = (
            f"wide architectural establishing shot of {visual_desc}, empty location, no people, "
            "clear landmarks and lighting, consistent environment design, "
            "no text, no border, no collage"
        )
    return asset


async def _ask(messages: list[dict], timeout: float = 180, temperature: float = 0.65) -> dict:
    payload = {
        "model": LLM_MODEL,
        "temperature": temperature,
        "response_format": {"type": "json_object"},
        "messages": messages,
    }
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            f"{LLM_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {LLM_API_KEY}"},
            json=payload,
        )
        response.raise_for_status()
        return _extract_json(response.json()["choices"][0]["message"]["content"])


def _split_ranges(start: int, end: int, parts: int) -> list[tuple[int, int]]:
    """Split [start..end] inclusive into `parts` contiguous balanced sub-ranges."""
    total = end - start + 1
    parts = min(parts, total)
    base, extra = divmod(total, parts)
    ranges = []
    curr = start
    for i in range(parts):
        length = base + (1 if i < extra else 0)
        ranges.append((curr, curr + length - 1))
        curr += length
    return ranges


async def _expand_range_recursive(
    request: PlanRequest,
    start_ch: int,
    end_ch: int,
    arc_goal: str,
    prev_arc_ending: str,
) -> list[dict]:
    """
    Recursively splits a large chapter range into smaller sub-arcs until each leaf
    has <= MAX_LEAF_CHAPTERS chapters, preserving global pacing toward the ending.
    """
    total_in_range = end_ch - start_ch + 1
    lang = _language_name(request)

    if total_in_range > MAX_LEAF_CHAPTERS:
        sub_ranges = _split_ranges(start_ch, end_ch, BRANCH_FACTOR)
        ranges_desc = "\n".join(
            f"- Part {idx} (Chapters {s} to {e}, {e - s + 1} chapters)"
            for idx, (s, e) in enumerate(sub_ranges, start=1)
        )
        system = f"""You are a master story architect pacing a {request.pages}-chapter comic.
Your job is to subdivide Chapters {start_ch}..{end_ch} into {len(sub_ranges)} sequential story arcs so the plot stretches naturally without rushing to the ending too early.
Return JSON only:
{{"arcs": [{{"part": int, "start": int, "end": int, "goal": "detailed plot arc summary in {lang} describing what happens in these chapters and where they end"}}]}}
All text in `goal` MUST be in {lang}."""

        user_msg = (
            f"Full Story Premise & Ending: {request.brief}\n"
            f"Total Book Length: {request.pages} chapters.\n"
            f"Current Section (Chapters {start_ch} to {end_ch}) Objective: {arc_goal}\n"
            f"State Entering Chapter {start_ch}: {prev_arc_ending or 'Beginning of the story.'}\n"
            f"Subdivide into these exact {len(sub_ranges)} parts:\n{ranges_desc}"
        )

        data = await _ask([{"role": "system", "content": system}, {"role": "user", "content": user_msg}], timeout=150)
        raw_arcs = data.get("arcs", [])

        all_chapters: list[dict] = []
        running_prev = prev_arc_ending
        for idx, (s, e) in enumerate(sub_ranges):
            arc_obj = raw_arcs[idx] if idx < len(raw_arcs) else {}
            sub_goal = str(arc_obj.get("goal") or f"{arc_goal} ({idx + 1}/{len(sub_ranges)})")
            sub_chapters = await _expand_range_recursive(request, s, e, sub_goal, running_prev)
            all_chapters.extend(sub_chapters)
            if sub_chapters:
                running_prev = f"{sub_chapters[-1]['title']}: {sub_chapters[-1]['summary']}"
        return all_chapters

    system = f"""You are a comic chapter planner. Return JSON only:
{{"pages": [{{"number": int, "title": "chapter title in {lang}", "summary": "2-3 sentences in {lang} detailing specific events, obstacles, and progress in this chapter", "english_beat": "1-sentence ENGLISH visual summary of the main scene"}}]}}
Generate EXACTLY {total_in_range} chapters numbered {start_ch} through {end_ch}.
Do NOT conclude the whole book unless {end_ch} == {request.pages}. Pace the plot to fulfill this section's exact goal."""

    user_msg = (
        f"Full Story Premise & Ending: {request.brief}\n"
        f"Total Book Length: {request.pages} chapters.\n"
        f"Section Goal for Chapters {start_ch}..{end_ch}: {arc_goal}\n"
        f"What happened right before Chapter {start_ch}: {prev_arc_ending or 'Story opens here.'}\n"
        f"Write chapters {start_ch} to {end_ch}."
    )

    data = await _ask([{"role": "system", "content": system}, {"role": "user", "content": user_msg}], timeout=150)
    raw_pages = data.get("pages", [])

    result: list[dict] = []
    for offset in range(total_in_range):
        ch_no = start_ch + offset
        raw = raw_pages[offset] if offset < len(raw_pages) else {}
        default_title = f"פרק {ch_no}" if request.language == "he" else f"Chapter {ch_no}"
        result.append({
            "number": ch_no,
            "title": str(raw.get("title") or default_title),
            "summary": str(raw.get("summary") or arc_goal),
            "english_beat": str(raw.get("english_beat") or f"Chapter {ch_no} key story scene"),
        })
    return result


def _fallback_outline(request: PlanRequest) -> tuple[str, str, list[dict], list[ReferenceAsset]]:
    pages = []
    for no in range(1, request.pages + 1):
        pct = round((no / max(1, request.pages)) * 100)
        title = f"פרק {no} ({pct}%)" if request.language == "he" else f"Chapter {no} ({pct}%)"
        summary = (
            f"התקדמות עלילתית ({pct}% מהסיפור): {request.brief[:160]}"
            if request.language == "he"
            else f"Story progression ({pct}%): {request.brief[:160]}"
        )
        pages.append({"number": no, "title": title, "summary": summary, "english_beat": f"Story progression stage {no}"})

    character = ReferenceAsset(
        id="character-protagonist",
        kind="character",
        name="הגיבור" if request.language == "he" else "Protagonist",
        description="הדמות הראשית בסיפור" if request.language == "he" else "Main protagonist",
        prompt="main protagonist matching the story setting, expressive face, distinctive outfit",
    )
    location = ReferenceAsset(
        id="location-main",
        kind="location",
        name="הזירה המרכזית" if request.language == "he" else "Main World",
        description="הסביבה המרכזית של העלילה" if request.language == "he" else "Primary setting",
        prompt="atmospheric story environment matching the brief",
    )
    title = "קומיקס בהמשכים" if request.language == "he" else "Serialized Comic"
    return title, request.style, pages, [_normalize_asset(character), _normalize_asset(location)]


async def _create_outline(request: PlanRequest) -> tuple[str, str, list[dict], list[ReferenceAsset]]:
    lang = _language_name(request)
    bible_system = f"""You are a comic showrunner. Return JSON only:
{{"title": "book title in {lang}", "global_arc": "high-level summary in {lang} spanning from the opening premise all the way to the user's requested ending", "assets": [{{"id": "char-1", "kind": "character|location", "name": "name in {lang}", "description": "role in {lang}", "prompt": "detailed ENGLISH visual description (appearance, outfit, colors, architecture)"}}]}}
Extract all key characters and locations from the brief."""

    try:
        bible = await _ask([
            {"role": "system", "content": bible_system},
            {"role": "user", "content": f"Story Brief & Ending: {request.brief}\nTotal Chapters: {request.pages}\nStyle: {request.style}\nLanguage: {lang}"},
        ], timeout=120)

        title = str(bible.get("title") or ("קומיקס חדש" if request.language == "he" else "New Comic"))
        global_arc = str(bible.get("global_arc") or request.brief)

        assets = []
        for idx, raw_asset in enumerate(bible.get("assets", []), start=1):
            kind = "location" if str(raw_asset.get("kind")).lower() == "location" else "character"
            assets.append(_normalize_asset(ReferenceAsset(
                id=str(raw_asset.get("id") or f"{kind}-{idx}"),
                kind=kind,
                name=str(raw_asset.get("name") or f"Asset {idx}"),
                description=str(raw_asset.get("description") or ""),
                prompt=str(raw_asset.get("prompt") or raw_asset.get("description") or ""),
            )))
        if not assets:
            _, _, _, assets = _fallback_outline(request)

        pages = await _expand_range_recursive(
            request=request,
            start_ch=1,
            end_ch=request.pages,
            arc_goal=global_arc,
            prev_arc_ending="",
        )
        return title, request.style, pages, assets
    except Exception:
        return _fallback_outline(request)


async def _create_single_page(
    request: PlanRequest,
    outline: dict,
    assets: list[ReferenceAsset],
    prev_summary: str,
    next_summary: str,
) -> ComicPage:
    """Generate panels for ONE chapter while anchored between the previous chapter, next chapter, and global ending."""
    lang = _language_name(request)
    asset_visuals = "; ".join(f"{a.name} ({a.kind}): {a.prompt}" for a in assets)

    system = f"""You are a comic storyboard artist. Return JSON only:
{{"panels": [{{"number": int, "description": "visual action in {lang}", "prompt": "vivid ENGLISH visual prompt for image generation (subject, exact action, setting, prop, camera angle)", "dialogue": ["single short spoken line in {lang}"], "narration": "short story caption in {lang}", "shot_type": "wide|medium|action|closeup"}}]}}

Rules:
1. Return EXACTLY {request.panels_per_page} panels numbered 1 to {request.panels_per_page}.
2. Panel 1 must connect smoothly from what happened in the previous chapter; the final panel must lead naturally toward the next chapter.
3. Every panel MUST show a DIFFERENT concrete action (no static portraits).
4. `prompt` MUST be in ENGLISH ONLY (no Hebrew), putting the main subject and action in the first 25 words.
5. `description`, `dialogue`, and `narration` MUST be in {lang} only."""

    user_msg = (
        f"Overall Story & Ultimate Ending: {request.brief}\n"
        f"Characters & Locations Visual Guide (English): {asset_visuals}\n"
        f"Previous Chapter ({outline['number'] - 1}): {prev_summary or 'None (Story Start)'}\n"
        f"CURRENT Chapter ({outline['number']}/{request.pages}): {outline['title']} — {outline['summary']}\n"
        f"Next Chapter ({outline['number'] + 1}): {next_summary or 'None (Final Chapter)'}\n"
        f"English Visual Beat: {outline.get('english_beat', '')}"
    )

    shot_angles = [
        "wide establishing shot",
        "dynamic three-quarter action shot",
        "medium over-the-shoulder shot",
        "dramatic low-angle full-body shot",
        "close-up reaction and prop detail",
        "wide environmental reveal",
    ]

    try:
        data = await _ask(
            [{"role": "system", "content": system}, {"role": "user", "content": user_msg}],
            timeout=150,
            temperature=0.72,
        )
        raw_panels = data.get("panels", [])
        if not raw_panels:
            raise ValueError("empty panels")

        panels: list[Panel] = []
        for panel_no in range(1, request.panels_per_page + 1):
            raw = raw_panels[panel_no - 1] if panel_no - 1 < len(raw_panels) else raw_panels[-1]
            angle = shot_angles[(outline["number"] + panel_no - 2) % len(shot_angles)]

            en_prompt = str(raw.get("prompt") or "").strip()
            en_prompt = re.sub(r"[\u0590-\u05ff]+", "", en_prompt).strip(" ,;-")
            if len(en_prompt.split()) < 5:
                en_prompt = f"{angle}, {outline.get('english_beat', 'dramatic story scene')}, panel {panel_no} action"
            else:
                en_prompt = f"{angle}, {en_prompt}"

            desc = str(raw.get("description") or "").strip()
            if not desc or not _matches_language(desc, request):
                desc = f"{outline['title']} - סצנה {panel_no}" if request.language == "he" else f"{outline['title']} - Scene {panel_no}"

            dialogue_raw = raw.get("dialogue", [])
            if isinstance(dialogue_raw, str):
                dialogue_raw = [dialogue_raw]
            dialogue = [str(d).strip() for d in dialogue_raw if str(d).strip() and _matches_language(str(d), request)][:1]

            narration = str(raw.get("narration") or "").strip()
            if not _matches_language(narration, request):
                narration = ""

            panels.append(Panel(
                id=f"p{outline['number']}-f{panel_no}",
                number=panel_no,
                description=desc,
                prompt=en_prompt,
                dialogue=dialogue,
                narration=narration,
                shot_type=str(raw.get("shot_type") or "action"),
            ))
        return ComicPage(number=outline["number"], title=outline["title"], summary=outline["summary"], panels=panels)
    except Exception:
        panels = []
        for panel_no in range(1, request.panels_per_page + 1):
            angle = shot_angles[(outline["number"] + panel_no - 2) % len(shot_angles)]
            beat_en = outline.get("english_beat") or "hero advancing the story"
            panels.append(Panel(
                id=f"p{outline['number']}-f{panel_no}",
                number=panel_no,
                description=f"{outline['summary']} (חלק {panel_no})" if request.language == "he" else f"{outline['summary']} (Part {panel_no})",
                prompt=f"{angle}, {beat_en}, step {panel_no} of {request.panels_per_page}",
                dialogue=[],
                narration=outline["title"] if panel_no == 1 else "",
                shot_type="action",
            ))
        return ComicPage(number=outline["number"], title=outline["title"], summary=outline["summary"], panels=panels)


async def create_plan(request: PlanRequest) -> BookPlan:
    title, style, outlines, assets = await _create_outline(request)
    pages: list[ComicPage] = []
    for idx, outline in enumerate(outlines):
        prev_summary = f"{pages[-1].title}: {pages[-1].summary}" if pages else ""
        next_summary = f"{outlines[idx + 1]['title']}: {outlines[idx + 1]['summary']}" if idx + 1 < len(outlines) else ""
        page = await _create_single_page(request, outline, assets, prev_summary, next_summary)
        pages.append(page)
    return BookPlan(
        title=title,
        style=style,
        language=request.language,
        characters=[a.name for a in assets if a.kind == "character"],
        locations=[a.name for a in assets if a.kind == "location"],
        assets=assets,
        pages=pages,
    )