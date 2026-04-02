from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


BG = (242, 246, 252)
SURFACE = (255, 255, 255)
SURFACE_ALT = (247, 250, 255)
BORDER = (216, 225, 238)
TEXT = (27, 44, 71)
MUTED = (94, 113, 140)
PRIMARY = (38, 91, 214)
SUCCESS = (27, 152, 110)
WARNING = (204, 138, 26)
DANGER = (214, 72, 91)
SUCCESS_SOFT = (231, 248, 240)
WARNING_SOFT = (255, 245, 221)
DANGER_SOFT = (255, 234, 238)
PRIMARY_SOFT = (232, 240, 255)


def _fonts():
    try:
        return (
            ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 42),
            ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 30),
            ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 24),
            ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 20),
        )
    except Exception:
        fallback = ImageFont.load_default()
        return fallback, fallback, fallback, fallback


def _fit_contain(
    image: Image.Image,
    width: int,
    height: int,
    background: tuple[int, int, int],
) -> tuple[Image.Image, tuple[int, int, int, int]]:
    image = image.convert("RGB")
    src_w, src_h = image.size
    scale = min(width / src_w, height / src_h)
    resized = image.resize((int(src_w * scale), int(src_h * scale)), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (width, height), background)
    left = max(0, (width - resized.width) // 2)
    top = max(0, (height - resized.height) // 2)
    canvas.paste(resized, (left, top))
    return canvas, (left, top, left + resized.width, top + resized.height)


def _wrap_line(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    if not text:
        return [""]
    buffer = ""
    lines = []
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


def _draw_wrapped(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, font, fill, max_width: int, gap: int) -> int:
    current_y = y
    for line in _wrap_line(draw, text, font, max_width):
        draw.text((x, current_y), line, font=font, fill=fill)
        bbox = draw.textbbox((x, current_y), line, font=font)
        current_y += (bbox[3] - bbox[1]) + gap
    return current_y


def _measure_wrapped_height(draw: ImageDraw.ImageDraw, text: str, font, max_width: int, gap: int) -> int:
    height = 0
    for line in _wrap_line(draw, text, font, max_width):
        bbox = draw.textbbox((0, 0), line, font=font)
        height += (bbox[3] - bbox[1]) + gap
    return max(height - gap, 0)


def _draw_bbox(
    draw: ImageDraw.ImageDraw,
    bbox: list[int] | None,
    src_size: tuple[int, int],
    target_box: tuple[int, int, int, int],
    color: tuple[int, int, int],
) -> None:
    if not bbox:
        return
    src_w, src_h = src_size
    x1, y1, x2, y2 = bbox
    tx1, ty1, tx2, ty2 = target_box
    scale_x = (tx2 - tx1) / src_w
    scale_y = (ty2 - ty1) / src_h
    rect = (
        tx1 + x1 * scale_x,
        ty1 + y1 * scale_y,
        tx1 + x2 * scale_x,
        ty1 + y2 * scale_y,
    )
    draw.rounded_rectangle(rect, radius=18, outline=color, width=6)


def _tone_colors(status_tone: str) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    mapping = {
        "success": (SUCCESS, SUCCESS_SOFT),
        "warning": (WARNING, WARNING_SOFT),
        "danger": (DANGER, DANGER_SOFT),
    }
    return mapping.get(status_tone, (PRIMARY, PRIMARY_SOFT))


def _draw_status_pill(draw: ImageDraw.ImageDraw, x: int, y: int, label: str, font, tone: str) -> None:
    fg, bg = _tone_colors(tone)
    bbox = draw.textbbox((x, y), label, font=font)
    width = (bbox[2] - bbox[0]) + 36
    height = (bbox[3] - bbox[1]) + 18
    draw.rounded_rectangle((x, y, x + width, y + height), radius=height // 2, fill=bg)
    draw.text((x + 18, y + 9), label, font=font, fill=fg)


def _draw_metric_cards(draw: ImageDraw.ImageDraw, metrics: list[tuple[str, str]], origin: tuple[int, int], width: int, body_font, note_font) -> int:
    x, y = origin
    gap = 16
    columns = 2
    card_width = (width - gap) // columns
    rows = [metrics[index:index + columns] for index in range(0, len(metrics), columns)]
    current_y = y
    for row in rows:
        row_height = 112
        for label, value in row:
            label_height = _measure_wrapped_height(draw, label, note_font, card_width - 40, 4)
            value_height = _measure_wrapped_height(draw, value, body_font, card_width - 40, 6)
            row_height = max(row_height, 24 + label_height + 14 + value_height + 24)
        for index, (label, value) in enumerate(row):
            card_x = x + index * (card_width + gap)
            card_y = current_y
            draw.rounded_rectangle((card_x, card_y, card_x + card_width, card_y + row_height), radius=24, fill=SURFACE, outline=BORDER)
            next_y = _draw_wrapped(draw, card_x + 20, card_y + 18, label, note_font, MUTED, card_width - 40, 4)
            _draw_wrapped(draw, card_x + 20, next_y + 10, value, body_font, TEXT, card_width - 40, 6)
        current_y += row_height + gap
    return current_y - gap


def _measure_metric_cards_height(draw: ImageDraw.ImageDraw, metrics: list[tuple[str, str]], width: int, body_font, note_font) -> int:
    gap = 16
    columns = 2
    card_width = (width - gap) // columns
    rows = [metrics[index:index + columns] for index in range(0, len(metrics), columns)]
    total_height = 0
    for row in rows:
        row_height = 112
        for label, value in row:
            label_height = _measure_wrapped_height(draw, label, note_font, card_width - 40, 4)
            value_height = _measure_wrapped_height(draw, value, body_font, card_width - 40, 6)
            row_height = max(row_height, 24 + label_height + 14 + value_height + 24)
        total_height += row_height
    total_height += gap * max(len(rows) - 1, 0)
    return total_height


def _draw_labeled_image_panel(draw: ImageDraw.ImageDraw, canvas: Image.Image, image_path: str | Path, panel_box: tuple[int, int, int, int], label: str, bbox: list[int] | None, accent: tuple[int, int, int], title_font) -> None:
    x1, y1, x2, y2 = panel_box
    draw.rounded_rectangle(panel_box, radius=28, fill=SURFACE, outline=BORDER)
    draw.text((x1 + 24, y1 + 20), label, font=title_font, fill=TEXT)
    image = Image.open(image_path)
    inner_box = (x1 + 24, y1 + 74, x2 - 24, y2 - 24)
    fitted, content_box = _fit_contain(image, inner_box[2] - inner_box[0], inner_box[3] - inner_box[1], PRIMARY_SOFT)
    canvas.paste(fitted, (inner_box[0], inner_box[1]))
    fitted_box = (
        inner_box[0] + content_box[0],
        inner_box[1] + content_box[1],
        inner_box[0] + content_box[2],
        inner_box[1] + content_box[3],
    )
    draw.rounded_rectangle(fitted_box, radius=22, outline=accent, width=4)
    _draw_bbox(draw, bbox, image.size, fitted_box, accent)


def create_single_result_visual_v7(title: str, image_path: str | Path, bbox: list[int] | None, status_label: str, status_tone: str, metrics: list[tuple[str, str]], output_path: str | Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    title_font, body_font, _, mini_font = _fonts()
    source_image = Image.open(image_path)
    aspect_ratio = source_image.width / source_image.height if source_image.height else 1.0

    canvas = Image.new("RGB", (1600, 1020), BG)
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((24, 24, 1576, 996), radius=36, fill=SURFACE_ALT, outline=BORDER)
    draw.text((60, 56), title, font=title_font, fill=TEXT)
    _draw_status_pill(draw, 60, 118, status_label, mini_font, status_tone)

    image_panel_top = 176
    image_panel_bottom = 940
    image_inner_height = (image_panel_bottom - image_panel_top) - 98
    adaptive_width = int(image_inner_height * aspect_ratio) + 80
    image_panel_width = max(500, min(880, adaptive_width))
    image_panel = (60, image_panel_top, 60 + image_panel_width, image_panel_bottom)
    summary_box = (image_panel[2] + 32, image_panel_top, 1540, image_panel_bottom)

    _draw_labeled_image_panel(draw, canvas, image_path, image_panel, "\u539f\u59cb\u68c0\u6d4b\u56fe\u7247", bbox, PRIMARY, body_font)
    draw.rounded_rectangle(summary_box, radius=28, fill=SURFACE, outline=BORDER)
    draw.text((summary_box[0] + 32, image_panel_top + 30), "\u5173\u952e\u6307\u6807", font=body_font, fill=TEXT)
    _draw_metric_cards(draw, metrics, (summary_box[0] + 32, image_panel_top + 84), summary_box[2] - summary_box[0] - 64, body_font, mini_font)

    canvas.save(output_path, format="PNG", compress_level=0)
    return output_path


def create_dual_result_visual_v7(title: str, left_image_path: str | Path, right_image_path: str | Path, left_bbox: list[int] | None, right_bbox: list[int] | None, left_label: str, right_label: str, status_label: str, status_tone: str, metrics: list[tuple[str, str]], output_path: str | Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    title_font, body_font, _, mini_font = _fonts()
    width = 1760
    draft = Image.new("RGB", (width, 1440), BG)
    draft_draw = ImageDraw.Draw(draft)
    metrics_height = _measure_metric_cards_height(draft_draw, metrics, 1528, body_font, mini_font)
    summary_top = 716
    summary_metrics_top = 808
    summary_bottom = max(1050, summary_metrics_top + metrics_height + 40)
    canvas_height = summary_bottom + 80

    canvas = Image.new("RGB", (width, canvas_height), BG)
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((24, 24, width - 24, canvas_height - 24), radius=36, fill=SURFACE_ALT, outline=BORDER)
    draw.text((60, 56), title, font=title_font, fill=TEXT)
    _draw_status_pill(draw, 60, 118, status_label, mini_font, status_tone)

    _draw_labeled_image_panel(draw, canvas, left_image_path, (60, 176, 842, 684), left_label, left_bbox, PRIMARY, body_font)
    _draw_labeled_image_panel(draw, canvas, right_image_path, (878, 176, 1660, 684), right_label, right_bbox, SUCCESS, body_font)

    summary_box = (60, summary_top, 1660, summary_bottom)
    draw.rounded_rectangle(summary_box, radius=28, fill=SURFACE, outline=BORDER)
    draw.text((96, summary_top + 30), "\u5173\u952e\u6307\u6807", font=body_font, fill=TEXT)
    _draw_metric_cards(draw, metrics, (96, summary_metrics_top), 1528, body_font, mini_font)

    canvas.save(output_path, format="PNG", compress_level=0)
    return output_path
