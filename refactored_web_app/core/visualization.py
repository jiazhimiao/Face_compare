from __future__ import annotations

from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont


CANVAS_BG = (238, 245, 255)
CARD_BG = (255, 255, 255)
CARD_BORDER = (205, 221, 248)
TITLE_COLOR = (18, 45, 88)
BODY_COLOR = (92, 113, 146)
ACCENT = (47, 109, 246)
NIGHT = (24, 59, 124)
SUCCESS = (22, 155, 115)
SUMMARY_BG = (247, 251, 255)
SUMMARY_BORDER = (214, 226, 248)


def _fonts() -> tuple[ImageFont.FreeTypeFont | ImageFont.ImageFont, ImageFont.FreeTypeFont | ImageFont.ImageFont, ImageFont.FreeTypeFont | ImageFont.ImageFont]:
    try:
        return (
            ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 40),
            ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 30),
            ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 26),
        )
    except Exception:
        fallback = ImageFont.load_default()
        return fallback, fallback, fallback


def _fit_cover(image: Image.Image, width: int, height: int) -> Image.Image:
    image = image.convert("RGB")
    src_w, src_h = image.size
    scale = max(width / src_w, height / src_h)
    resized = image.resize((int(src_w * scale), int(src_h * scale)), Image.Resampling.LANCZOS)
    left = max(0, (resized.width - width) // 2)
    top = max(0, (resized.height - height) // 2)
    return resized.crop((left, top, left + width, top + height))


def _draw_bbox(draw: ImageDraw.ImageDraw, bbox: list[int] | None, src_size: tuple[int, int], target_box: tuple[int, int, int, int], color: tuple[int, int, int]) -> None:
    if not bbox:
        return
    src_w, src_h = src_size
    x1, y1, x2, y2 = bbox
    tx1, ty1, tx2, ty2 = target_box
    target_w = tx2 - tx1
    target_h = ty2 - ty1
    sx = target_w / src_w
    sy = target_h / src_h
    rect = (
        tx1 + x1 * sx,
        ty1 + y1 * sy,
        tx1 + x2 * sx,
        ty1 + y2 * sy,
    )
    draw.rounded_rectangle(rect, radius=14, outline=color, width=5)


def _wrap_line(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont | ImageFont.ImageFont, max_width: int) -> list[str]:
    if not text:
        return [""]
    buffer = ""
    lines: list[str] = []
    for char in text:
        candidate = buffer + char
        if draw.textlength(candidate, font=font) <= max_width or not buffer:
            buffer = candidate
            continue
        lines.append(buffer)
        buffer = char
    if buffer:
        lines.append(buffer)
    return lines or [text]


def _draw_wrapped_lines(
    draw: ImageDraw.ImageDraw,
    origin: tuple[int, int],
    lines: Iterable[str],
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    max_width: int,
    fill: tuple[int, int, int],
    line_gap: int,
) -> int:
    x, y = origin
    current_y = y
    for line in lines:
        wrapped = _wrap_line(draw, line, font, max_width)
        for item in wrapped:
            draw.text((x, current_y), item, fill=fill, font=font)
            bbox = draw.textbbox((x, current_y), item, font=font)
            current_y += (bbox[3] - bbox[1]) + line_gap
    return current_y


def _count_wrapped_lines(
    draw: ImageDraw.ImageDraw,
    lines: Iterable[str],
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    max_width: int,
) -> int:
    total = 0
    for line in lines:
        total += max(1, len(_wrap_line(draw, line, font, max_width)))
    return total


def create_text_summary(title: str, lines: list[str], output_path: str | Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    title_font, body_font, _ = _fonts()
    width = 920
    image = Image.new("RGB", (width, 420), color=CANVAS_BG)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((24, 24, width - 24, 396), radius=24, fill=CARD_BG, outline=CARD_BORDER)
    draw.text((48, 48), title, fill=TITLE_COLOR, font=title_font)
    _draw_wrapped_lines(draw, (48, 116), lines, body_font, width - 96, BODY_COLOR, 10)

    image.save(output_path, format="PNG", compress_level=0)
    return output_path


def create_single_result_visual(title: str, image_path: str | Path, bbox: list[int] | None, lines: list[str], output_path: str | Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    title_font, body_font, note_font = _fonts()

    canvas = Image.new("RGB", (1380, 860), color=CANVAS_BG)
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((24, 24, 1356, 836), radius=28, fill=CARD_BG, outline=CARD_BORDER)
    draw.text((56, 48), title, fill=TITLE_COLOR, font=title_font)
    draw.text((58, 94), "\u56fe\u7247\u7ed3\u679c\u4f1a\u4fdd\u6301\u5728\u5b89\u5168\u8fb9\u8ddd\u5185\uff0c\u907f\u514d\u957f\u6587\u672c\u6ea2\u51fa\u3002", fill=BODY_COLOR, font=note_font)

    src = Image.open(image_path)
    fitted = _fit_cover(src, 680, 590)
    canvas.paste(fitted, (56, 146))
    draw.rounded_rectangle((56, 146, 736, 736), radius=26, outline=ACCENT, width=3)
    _draw_bbox(draw, bbox, src.size, (56, 146, 736, 736), ACCENT)

    draw.rounded_rectangle((776, 146, 1308, 736), radius=24, fill=SUMMARY_BG, outline=SUMMARY_BORDER)
    draw.text((808, 176), "\u7ed3\u679c\u6458\u8981", fill=TITLE_COLOR, font=body_font)
    _draw_wrapped_lines(draw, (808, 236), lines, body_font, 436, BODY_COLOR, 16)

    canvas.save(output_path, format="PNG", compress_level=0)
    return output_path


def create_dual_result_visual(
    title: str,
    left_image_path: str | Path,
    right_image_path: str | Path,
    left_bbox: list[int] | None,
    right_bbox: list[int] | None,
    lines: list[str],
    output_path: str | Path,
) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    title_font, body_font, note_font = _fonts()

    probe = Image.new("RGB", (10, 10), color=CANVAS_BG)
    probe_draw = ImageDraw.Draw(probe)
    wrapped_line_count = _count_wrapped_lines(probe_draw, lines, body_font, 1336)
    detail_block_height = max(326, 120 + wrapped_line_count * 54)
    canvas_height = 772 + detail_block_height

    canvas = Image.new("RGB", (1520, canvas_height), color=CANVAS_BG)
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((24, 24, 1496, canvas_height - 24), radius=28, fill=CARD_BG, outline=CARD_BORDER)
    draw.text((56, 48), title, fill=TITLE_COLOR, font=title_font)
    draw.text((58, 94), "\u65b0\u7248\u7ed3\u679c\u56fe\u5df2\u5207\u6362\u4e3a\u84dd\u767d\u914d\u8272\uff0c\u5e76\u4fdd\u7559\u81ea\u52a8\u6362\u884c\u4e0e\u8fb9\u754c\u63a7\u5236\u3002", fill=BODY_COLOR, font=note_font)

    left_src = Image.open(left_image_path)
    right_src = Image.open(right_image_path)
    left_fitted = _fit_cover(left_src, 620, 470)
    right_fitted = _fit_cover(right_src, 620, 470)
    canvas.paste(left_fitted, (56, 150))
    canvas.paste(right_fitted, (844, 150))
    draw.rounded_rectangle((56, 150, 676, 620), radius=24, outline=ACCENT, width=3)
    draw.rounded_rectangle((844, 150, 1464, 620), radius=24, outline=NIGHT, width=3)
    _draw_bbox(draw, left_bbox, left_src.size, (56, 150, 676, 620), ACCENT)
    _draw_bbox(draw, right_bbox, right_src.size, (844, 150, 1464, 620), NIGHT)

    draw.text((56, 648), "\u5de6\u4fa7\u56fe\u7247", fill=TITLE_COLOR, font=note_font)
    draw.text((844, 648), "\u53f3\u4fa7\u56fe\u7247", fill=TITLE_COLOR, font=note_font)

    detail_bottom = 702 + detail_block_height
    draw.rounded_rectangle((56, 702, 1464, detail_bottom), radius=24, fill=SUMMARY_BG, outline=SUMMARY_BORDER)
    draw.text((84, 740), "\u7ed3\u679c\u8bf4\u660e", fill=TITLE_COLOR, font=body_font)
    _draw_wrapped_lines(draw, (84, 804), lines, body_font, 1336, BODY_COLOR, 18)

    canvas.save(output_path, format="PNG", compress_level=0)
    return output_path
