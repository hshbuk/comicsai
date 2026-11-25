from io import BytesIO
from pathlib import Path
import re

from PIL import Image, ImageDraw, ImageFont

try:
    from bidi.algorithm import get_display
except ImportError:  # pragma: no cover
    get_display = lambda value: value


def _font(size: int, bold: bool = False):
    candidates = [
        Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def _is_rtl(text: str) -> bool:
    return bool(re.search(r"[\u0590-\u05ff]", text))


def _visual(text: str) -> str:
    return get_display(text) if _is_rtl(text) else text


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and draw.textlength(_visual(candidate), font=font) > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines or [""]


def compose_panel(image_bytes: bytes, dialogue: list[str], narration: str = "") -> bytes:
    """Put text in bands outside the artwork, with correct Hebrew bidirectional rendering."""
    artwork = Image.open(BytesIO(image_bytes)).convert("RGBA")
    width, height = artwork.size
    pad = max(18, width // 32)
    font = _font(max(22, width // 32))
    bold = _font(max(22, width // 32), bold=True)
    measure = ImageDraw.Draw(Image.new("RGBA", (1, 1)))

    def text_lines(value: str, use_font) -> list[str]:
        return _wrap(measure, value.strip(), use_font, width - pad * 2)

    narration_lines = text_lines(narration, bold) if narration.strip() else []
    dialogue_blocks = [text_lines(value, font) for value in (dialogue or []) if value and value.strip()]
    line_height = font.getbbox("Ag")[3] - font.getbbox("Ag")[1] + 8
    bold_height = bold.getbbox("Ag")[3] - bold.getbbox("Ag")[1] + 8
    band_pad = max(12, pad // 2)
    top_height = len(narration_lines) * bold_height + band_pad * 2 if narration_lines else 0
    bottom_height = sum(len(lines) * line_height + band_pad * 2 for lines in dialogue_blocks)

    canvas = Image.new("RGBA", (width, top_height + height + bottom_height), (245, 245, 245, 255))
    canvas.paste(artwork, (0, top_height))
    draw = ImageDraw.Draw(canvas, "RGBA")

    def draw_lines(lines: list[str], y: int, use_font, color):
        step = use_font.getbbox("Ag")[3] - use_font.getbbox("Ag")[1] + 8
        for index, logical in enumerate(lines):
            rendered = _visual(logical)
            if _is_rtl(logical):
                draw.text((width - pad, y + index * step), rendered, font=use_font, fill=color, anchor="ra")
            else:
                draw.text((width // 2, y + index * step), rendered, font=use_font, fill=color, anchor="ma")

    if narration_lines:
        draw.rectangle((0, 0, width, top_height), fill=(32, 32, 32, 255))
        draw_lines(narration_lines, band_pad, bold, (255, 255, 255, 255))

    y = top_height + height
    for lines in dialogue_blocks:
        block_height = len(lines) * line_height + band_pad * 2
        draw.rectangle((0, y, width, y + block_height), fill=(255, 255, 255, 255), outline=(30, 30, 30, 255), width=2)
        draw_lines(lines, y + band_pad, font, (15, 15, 15, 255))
        y += block_height

    output = BytesIO()
    canvas.convert("RGB").save(output, format="PNG", optimize=True)
    return output.getvalue()
